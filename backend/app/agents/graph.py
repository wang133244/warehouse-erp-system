"""督导分流 + 五个业务节点；一轮一跳结束。库连接放 ContextVar，不进图状态。"""

from __future__ import annotations  # 允许前置注解

from contextvars import ContextVar  # 按调用栈隔离 DB/用户，协程安全且不进 LangGraph 状态
from typing import Any, TypedDict  # 图状态与工具调用的宽松类型

from sqlalchemy.orm import Session  # 请求级数据库会话

from backend.app.agents.tools import WHITELIST_TOOLS, assert_whitelist  # 出口再滤一遍工具名
from backend.app.core.logging import get_logger  # 助手运行日志

GRAPH_ENGINE = "langgraph"  # 对外声明当前图引擎，便于系统信息接口展示
# ContextVar：只在 run_agents 调用期间有效，节点通过 _xxx_var.get() 取，绝不写入 AgentState。
_db_var: ContextVar[Session] = ContextVar("agent_db")  # 当前请求的 SQLAlchemy 会话；无 default，未 set 则 LookupError
_user_id_var: ContextVar[int | None] = ContextVar("agent_user_id", default=None)  # 当前登录用户，仅用于日志 _scope()
_session_id_var: ContextVar[int | None] = ContextVar("agent_session_id", default=None)  # 当前助手会话 ID，仅用于日志
_graph = None  # 编译后的 StateGraph 单例，首次 get_graph() 时构建
agent_logger = get_logger("agent")  # 意图、工具、耗时相关日志


class AgentState(TypedDict, total=False):  # 图状态：只含可序列化的对话与结果
    # 节点间只传对话与结果；DB/用户放 ContextVar，避免进图状态。
    content: str  # 本轮用户原话，各节点只读
    intent: str  # 督导写出：inventory/analysis/exception/draft/review
    answer: str  # 业务节点写出：最终回复
    tool_calls: list[dict[str, Any]]  # 业务节点写出：已打白名单标签的工具调用
    draft: dict[str, Any] | None  # 仅草稿结构，不直接改库存
    history: list[dict[str, str]]  # 本会话上文；无 checkpointer，由调用方每次传入
    plan: dict[str, Any] | None  # DeepSeek 槽位；失败则关键词，业务节点据此选工具


INTENT_AGENT = {  # 意图 -> 图节点名，条件边与收尾边共用
    "inventory": "inventory_agent",  # 查库存窗口
    "analysis": "analysis_agent",  # 报表/看板窗口
    "exception": "exception_agent",  # 预警窗口
    "draft": "draft_agent",  # 草稿窗口
    "review": "review_agent",  # 审批窗口
}  # INTENT_AGENT 结束


def _scope() -> str:  # 日志前缀：从 ContextVar 读用户与会话，不从 state 读
    return f"user_id={_user_id_var.get()} session_id={_session_id_var.get()}"  # 未 set 时 user/session 为 None


def classify_intent(  # 决定走哪个业务节点：问候 > 规划 JSON > 关键词
    content: str,  # 本轮原话
    history: list[dict[str, str]] | None = None,  # 上文，规划器用
    plan: dict[str, Any] | None = None,  # 督导已算好的规划，避免重复打 LLM
    *,  # 后面只能关键字
    allow_plan_llm: bool = True,  # False 时不再调用 plan_turn（督导已调用过）
) -> str:  # 返回 INTENT_AGENT 的键
    from backend.app.agents.llm import plan_turn  # 延迟导入，避免与 llm 循环
    from backend.app.services.assistant_service import GREETING_RE  # 问候正则与助手服务共用

    text = content or ""  # 空内容当空串
    stripped = text.strip()  # 去空白后匹配问候
    if GREETING_RE.match(stripped):  # 你好/在吗 等短问候
        agent_logger.info("%s intent=inventory source=greeting", _scope())  # 问候也进库存窗口做能力说明
        return "inventory"  # 固定分流到 inventory_agent
    resolved = plan  # 优先用调用方传入的规划
    if resolved is None and allow_plan_llm:  # 督导以外的入口才现场规划
        resolved = plan_turn(content, history)  # DeepSeek 槽位，无 Key 则 None
    if resolved:  # 规划成功
        intent = resolved.get("intent")  # 可能是 help
        if intent == "help":  # 能力说明不单独建节点
            intent = "inventory"  # 映射到库存窗口
        if intent in INTENT_AGENT:  # 合法业务意图
            agent_logger.info("%s intent=%s source=plan", _scope(), intent)  # 来源记为 plan
            return intent  # 按规划分流
    upper = text.upper()  # ABC 等英文关键词不区分大小写
    if ("入库" in text or "出库" in text or "盘点" in text) and "草稿" in text:  # 明确要草稿
        intent = "draft"  # 草稿节点
    elif "审批" in text:  # 审批/待审
        intent = "review"  # 审批节点
    elif "预警" in text or "异常" in text:  # 库存预警
        intent = "exception"  # 预警节点
    elif "ABC" in upper or "周转" in text or "看板" in text or "汇总" in text or "报表" in text or "日报" in text or "周报" in text or "拣货效率" in text:  # 分析类
        intent = "analysis"  # 分析节点
    else:  # 默认查库存
        intent = "inventory"  # 库存节点
    agent_logger.info("%s intent=%s source=keyword", _scope(), intent)  # 来源记为 keyword
    return intent  # 关键词分流结果


def _run_tools(state: AgentState, agent: str) -> AgentState:  # 五个业务节点的共同实现：跑工具、打标签、可选改写
    from backend.app.agents.llm import polish_answer  # 延迟导入改写
    from backend.app.services.assistant_service import classify_and_run  # 真正选工具并执行

    db = _db_var.get()  # 从 ContextVar 取会话，state 里没有 DB
    answer, tool_calls, draft = classify_and_run(  # 按 plan/关键词调用白名单工具
        db,  # 当前请求会话
        state["content"],  # 本轮用户原话
        history=state.get("history") or [],  # 上文，供 SKU 指代
        plan=state.get("plan"),  # 督导写入的槽位
    )  # classify_and_run 结束
    tagged = []  # 带 agent 名的工具调用列表
    for call in tool_calls:  # 逐条再断言白名单
        name = assert_whitelist(call["name"])  # 禁止名单或未知名会抛错
        tagged.append({**call, "name": name, "agent": agent})  # 记下是哪个窗口调的
    if not tagged:  # 没调工具（问候/纯说明）
        polished = answer  # 不改写，避免模型空转
    else:  # 有工具结果才改写
        polished = polish_answer(  # DeepSeek 润色，失败为 None
            state["content"],  # 原问
            answer,  # 工具事实
            [call["name"] for call in tagged],  # 工具名列表
            history=state.get("history") or [],  # 上文
        )  # polish_answer 结束
    agent_logger.info(  # 记录本窗口做了什么
        "%s agent=%s intent=%s tools=%s draft=%s history_len=%s",  # 作用域、窗口、意图、工具、是否草稿、上文长度
        _scope(),  # ContextVar 中的用户与会话
        agent,  # 节点名
        state.get("intent", "inventory"),  # 督导写下的意图
        [call["name"] for call in tagged],  # 实际工具
        bool(draft),  # 是否带草稿
        len(state.get("history") or []),  # 上文条数
    )  # info 结束
    return {  # 只回写结果字段，LangGraph 会 merge 进 state
        "answer": polished or answer,  # 改写失败用工具原文
        "tool_calls": tagged,  # 已打标签的调用
        "draft": draft,  # 可能为 None
        "intent": state.get("intent", "inventory"),  # 带回意图，出口日志一致
    }  # 节点输出结束


def supervisor_node(state: AgentState) -> AgentState:  # 入口节点：规划 + 分类，不调业务工具
    from backend.app.agents.llm import plan_turn  # 本节点负责打一次规划 LLM
    from backend.app.services.assistant_service import GREETING_RE  # 问候则跳过规划，省一次调用

    content = state.get("content", "")  # 本轮原话
    history = state.get("history") or []  # 上文
    plan = None  # 默认无规划
    if not GREETING_RE.match((content or "").strip()):  # 非问候才规划
        plan = plan_turn(content, history)  # 可能 None（无 Key 或解析失败）
    return {"intent": classify_intent(content, history, plan=plan, allow_plan_llm=False), "plan": plan}  # 写入 intent/plan，供条件边与业务节点


def inventory_node(state: AgentState) -> AgentState:  # 库存窗口节点
    return _run_tools(state, "inventory_agent")  # 查余额/流水等


def analysis_node(state: AgentState) -> AgentState:  # 分析窗口节点
    return _run_tools(state, "analysis_agent")  # 报表、看板、周转


def exception_node(state: AgentState) -> AgentState:  # 预警窗口节点
    return _run_tools(state, "exception_agent")  # 异常库存


def draft_node(state: AgentState) -> AgentState:  # 草稿窗口节点
    return _run_tools(state, "draft_agent")  # 只生成草稿，不改库存


def review_node(state: AgentState) -> AgentState:  # 审批窗口节点
    return _run_tools(state, "review_agent")  # 查审批或提交审批


def route_intent(state: AgentState) -> str:  # 条件边路由函数：返回 INTENT_AGENT 的键
    return state.get("intent") or "inventory"  # 缺省走库存，避免未知 intent 卡在督导


def _build_graph():  # 组装节点与边：START -> 督导 -> 五窗口之一 -> END，图内不循环
    from langgraph.graph import END, START, StateGraph  # 延迟导入，测试未装 langgraph 时仍可 import 本模块

    builder = StateGraph(AgentState)  # 状态类型为 AgentState
    builder.add_node("supervisor", supervisor_node)  # 节点：督导，写 intent/plan
    builder.add_node("inventory_agent", inventory_node)  # 节点：库存窗口
    builder.add_node("analysis_agent", analysis_node)  # 节点：分析窗口
    builder.add_node("exception_agent", exception_node)  # 节点：预警窗口
    builder.add_node("draft_agent", draft_node)  # 节点：草稿窗口
    builder.add_node("review_agent", review_node)  # 节点：审批窗口
    builder.add_edge(START, "supervisor")  # 边：图入口固定进入督导
    # 督导按 intent 进五个窗口之一，窗口办完即 END，图内不循环调工具。
    builder.add_conditional_edges(  # 条件边：督导 --route_intent--> 某一业务节点
        "supervisor",  # 源节点
        route_intent,  # 根据 state["intent"] 选边
        {  # 意图键 -> 目标节点名
            "inventory": "inventory_agent",  # 查库存
            "analysis": "analysis_agent",  # 分析报表
            "exception": "exception_agent",  # 预警
            "draft": "draft_agent",  # 草稿
            "review": "review_agent",  # 审批
        },  # 路由表结束
    )  # 条件边结束
    for node in INTENT_AGENT.values():  # 五个业务节点
        builder.add_edge(node, END)  # 边：窗口完成后直接结束，不回到督导
    return builder.compile()  # 编译成可 invoke 的图


def get_graph():  # 懒编译单例，避免每个请求重建图
    global _graph  # 模块级缓存
    if _graph is None:  # 第一次调用
        _graph = _build_graph()  # 编译并保存
    return _graph  # 已编译图


def run_agents(  # 对外入口：set ContextVar -> invoke 图 -> reset ContextVar
    db: Session,  # 请求会话，放入 _db_var
    content: str,  # 本轮用户原话
    history: list[dict[str, str]] | None = None,  # 本会话上文
    *,  # 后面只能关键字
    user_id: int | None = None,  # 写入 _user_id_var，仅日志
    session_id: int | None = None,  # 写入 _session_id_var，仅日志
) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:  # 回复、工具调用、可选草稿
    db_token = _db_var.set(db)  # 绑定会话到当前上下文，返回 token 供 finally reset
    user_token = _user_id_var.set(user_id)  # 绑定用户
    session_token = _session_id_var.set(session_id)  # 绑定会话 ID
    history_len = len(history or [])  # 日志用
    agent_logger.info("%s run history_len=%s", _scope(), history_len)  # 开始跑图
    try:  # invoke 期间节点通过 ContextVar 取 db
        result = get_graph().invoke({"content": content, "history": history or []})  # 初始 state 只有 content/history
    finally:  # 无论成功失败都拆掉上下文，避免串请求
        _session_id_var.reset(session_token)  # 恢复进入前的 session_id
        _user_id_var.reset(user_token)  # 恢复 user_id
        _db_var.reset(db_token)  # 恢复 db（通常是未 set）
    tool_calls = [call for call in result.get("tool_calls") or [] if call.get("name") in WHITELIST_TOOLS]  # 出口再滤白名单
    return result.get("answer") or "", tool_calls, result.get("draft")  # 空回答用空串，草稿可能为 None
