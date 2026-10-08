"""DeepSeek：plan_turn 规划意图/槽位，polish_answer 改写工具结果；无 Key 则返回 None。"""

from __future__ import annotations  # 允许前置注解

import json  # 请求体与模型 JSON 解析
import re  # 从模型输出中抽出 JSON 对象
import urllib.error  # 捕获 HTTP/网络错误
import urllib.request  # 标准库发 POST，避免强依赖 httpx
from typing import Any  # 解析后的宽松类型

from backend.app.core.config import get_settings  # 读取 DeepSeek 密钥与模型名


ALLOWED_INTENTS = {"inventory", "analysis", "exception", "draft", "review"}  # 分类器允许的业务意图
PLAN_INTENTS = ALLOWED_INTENTS | {"help"}  # 规划器额外允许 help（问候），图里会映射到 inventory
PLAN_REPORTS = {"abc", "turnover", "daily", "weekly", "picking", "dashboard"}  # analysis 可用的报表槽
PLAN_DRAFTS = {"inbound", "outbound", "counting"}  # draft 可用的草稿类型
JSON_RE = re.compile(r"\{.*\}", re.DOTALL)  # 贪婪匹配第一段花括号，兼容模型夹杂说明文字


def llm_enabled() -> bool:  # 是否配置了可用的 DeepSeek Key
    return bool(get_settings().deepseek_api_key.strip())  # 空白视为未启用


def llm_provider() -> str:  # 对外暴露当前提供商名
    return "deepseek" if llm_enabled() else "none"  # 无 Key 则 none


def complete_chat(messages: list[dict[str, str]], *, timeout: float = 12) -> str | None:  # 调 chat/completions，失败返回 None
    settings = get_settings()  # 读密钥、模型、基址
    api_key = settings.deepseek_api_key.strip()  # 去掉误粘贴的空白
    if not api_key:  # 未配置则不发网
        return None  # 调用方走关键词/原文
    payload = json.dumps(  # 组装 OpenAI 兼容请求体
        {  # DeepSeek chat 参数
            "model": settings.deepseek_model,  # 模型名
            "messages": messages,  # 系统+用户消息
            "temperature": 0.2,  # 低温度，意图/改写更稳
        }  # 请求 JSON 结束
    ).encode("utf-8")  # HTTP body 用 UTF-8
    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"  # 拼完整 URL
    request = urllib.request.Request(  # 构造 POST
        url,  # 接口地址
        data=payload,  # JSON 字节
        method="POST",  # 以 POST 提交补全请求
        headers={  # 鉴权与内容类型
            "Authorization": f"Bearer {api_key}",  # Bearer 密钥
            "Content-Type": "application/json",  # JSON 体
            "Accept": "application/json",  # 期望 JSON 响应
        },  # headers 结束
    )  # Request 结束
    try:  # 网络与 JSON 都可能失败
        with urllib.request.urlopen(request, timeout=timeout) as response:  # 同步等待，超时切断
            body = json.loads(response.read().decode("utf-8"))  # 解码响应
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:  # 网络、超时、坏 JSON
        from backend.app.core.logging import get_logger  # 延迟导入日志

        get_logger("agent").warning("llm request failed: %s", exc)  # 记失败原因，不抛给用户
        return None  # 降级
    try:  # 按 OpenAI 形状取 content
        content = body["choices"][0]["message"]["content"]  # 第一条回复正文
    except (KeyError, IndexError, TypeError):  # 结构不对
        return None  # 当作无结果
    if not isinstance(content, str) or not content.strip():  # 空串或非字符串
        return None  # 无效回复
    return content.strip()  # 去掉首尾空白后返回


def classify_intent_llm(content: str) -> str | None:  # 仅分类意图，不含槽位；失败返回 None
    raw = complete_chat(  # 让模型只吐 JSON
        [  # 系统约束 + 用户原话
            {  # 系统提示
                "role": "system",  # 系统角色
                "content": (  # 强制 JSON 与意图枚举
                    "你是仓储助手的意图分类器。只返回 JSON："  # 角色与输出格式
                    '{"intent":"inventory|analysis|exception|draft|review"}。'  # 允许的意图枚举
                    "inventory=查库存；analysis=ABC/周转/报表/看板；exception=预警；"  # 各意图含义
                    "draft=生成入出库或盘点草稿；review=审批。不要输出其它文字。"  # 草稿与审批，禁止废话
                ),  # 系统内容结束
            },  # 系统消息结束
            {"role": "user", "content": (content or "")[:2000]},  # 截断过长用户输入
        ]  # messages 结束
    )  # complete_chat 结束
    if not raw:  # 无模型输出
        return None  # 交给关键词
    match = JSON_RE.search(raw)  # 抽出 JSON
    if match is None:  # 没有花括号
        return None  # 解析失败
    try:  # JSON 可能仍非法
        parsed: Any = json.loads(match.group(0))  # 解析对象
    except json.JSONDecodeError:  # 坏 JSON
        return None  # 失败
    intent = str(parsed.get("intent") or "").strip()  # 取出 intent 字段
    return intent if intent in ALLOWED_INTENTS else None  # 不在枚举则丢弃


def _as_optional_str(value: Any) -> str | None:  # 把模型槽位收成非空字符串或 None
    if value is None:  # 模型给出空值则视为未填槽位
        return None  # 无值
    text = str(value).strip()  # 转字符串并去空白
    return text or None  # 空串也当无值


def _as_optional_int(value: Any) -> int | None:  # 把数量槽位收成 int 或 None
    if value is None or value is False:  # null/false 不当作 0
        return None  # 无数量
    try:  # 可能是字符串数字
        return int(value)  # 转整数
    except (TypeError, ValueError):  # 无法转换
        return None  # 丢弃


def plan_turn(content: str, history: list[dict[str, str]] | None = None) -> dict[str, Any] | None:  # 规划本轮意图与槽位
    history_blob = []  # 拼进 prompt 的最近对话摘要
    for item in (history or [])[-6:]:  # 只取最近 6 条，控制 token
        role = item.get("role")  # 只保留用户与助手两轮
        text = item.get("content")  # 正文
        if role in {"user", "assistant"} and text:  # 忽略工具等其它角色
            history_blob.append(f"{role}: {text[:400]}")  # 单条再截断
    raw = complete_chat(  # 调用规划器
        [  # 系统 JSON 契约 + 用户本轮
            {  # 系统提示
                "role": "system",  # 系统角色
                "content": (  # 槽位与枚举说明
                    "你是仓储助手的回合规划器。只返回 JSON："  # 规划器角色
                    '{"intent":"inventory|analysis|exception|draft|review|help",'  # 意图含 help
                    '"sku_code":null,"location_code":null,"quantity":null,'  # 库存槽位
                    '"report":null,"draft_type":null,"use_history_sku":true}。'  # 报表、草稿、是否沿用上文 SKU
                    "intent：inventory=查库存；analysis=ABC/周转/报表/看板；exception=预警；"  # 意图说明
                    "draft=入出库或盘点草稿；review=审批；help=问候或能力说明。"  # 草稿、审批、帮助
                    "report 仅 analysis 时用 abc|turnover|daily|weekly|picking|dashboard。"  # 报表枚举
                    "draft_type 仅 draft 时用 inbound|outbound|counting。"  # 草稿类型枚举
                    "当前句没提 SKU 但上一句有，则 use_history_sku=true。"  # 指代规则
                    "禁止编造不存在的 SKU。不要输出其它文字。"  # 禁止幻觉
                ),  # 系统内容结束
            },  # 系统消息结束
            {  # 用户消息：上文 + 本轮
                "role": "user",  # 用户角色
                "content": (  # 把历史与本轮拼在一起
                    f"最近对话：\n{chr(10).join(history_blob) or '（无）'}\n"  # 上文摘要，无则标注
                    f"本轮用户：{(content or '')[:1500]}"  # 本轮原话截断
                ),  # 用户内容结束
            },  # 用户消息结束
        ]  # messages 结束
    )  # complete_chat 结束
    if not raw:  # 无输出
        return None  # 图会改走关键词
    match = JSON_RE.search(raw)  # 抽 JSON
    if match is None:  # 抽不出
        return None  # 失败
    try:  # 解析
        parsed: Any = json.loads(match.group(0))  # 得到对象
    except json.JSONDecodeError:  # 坏 JSON
        return None  # 失败
    if not isinstance(parsed, dict):  # 必须是对象
        return None  # 数组等形状丢弃
    intent = str(parsed.get("intent") or "").strip()  # 意图
    if intent not in PLAN_INTENTS:  # 未知意图
        return None  # 整份规划作废
    report = _as_optional_str(parsed.get("report"))  # 报表槽
    draft_type = _as_optional_str(parsed.get("draft_type"))  # 草稿类型槽
    return {  # 规范化后的规划结果
        "intent": intent,  # 意图，含 help
        "sku_code": _as_optional_str(parsed.get("sku_code")),  # 商品编码槽位
        "location_code": _as_optional_str(parsed.get("location_code")),  # 库位码
        "quantity": _as_optional_int(parsed.get("quantity")),  # 数量
        "report": report if report in PLAN_REPORTS else None,  # 非法报表名丢掉
        "draft_type": draft_type if draft_type in PLAN_DRAFTS else None,  # 非法草稿类型丢掉
        "use_history_sku": bool(parsed.get("use_history_sku", True)),  # 默认允许沿用上文 SKU
    }  # 规划字典结束


def polish_answer(  # 用模型改写工具结果，禁止编造数量或声称已改库存
    question: str,  # 用户原问
    tool_answer: str,  # 工具拼好的事实文本
    tool_names: list[str],  # 本轮用过的工具名
    history: list[dict[str, str]] | None = None,  # 上文，帮助指代
) -> str | None:  # 改写失败则调用方用原文
    messages: list[dict[str, str]] = [  # 先放系统约束
        {  # 系统提示
            "role": "system",  # 系统角色
            "content": (  # 只能改写、保留表格与「建议：」
                "你是仓储助手。只能改写已给出的工具结果，用简体中文、简洁说明。"  # 只改写不编造
                "禁止编造数量，禁止声称已经改库存、已经入库或已经出库。"  # 禁止假动作
                "草稿必须提醒用户到业务页人工确认。不要输出 JSON。"  # 草稿需人确认
                "如果工具结果里有 Markdown 表格，必须原样保留表格，不要改成逗号分隔或纯文字列表。"  # 保留表格
                "工具结果中的「建议：」及其后整句必须原样保留。"  # 保留建议句
            ),  # 系统内容结束
        }  # 系统消息结束
    ]  # 初始 messages
    for item in (history or [])[-6:]:  # 再附最近 6 条对话
        role = item.get("role")  # 角色
        content = item.get("content")  # 正文
        if role in {"user", "assistant"} and content:  # 只保留人话
            messages.append({"role": role, "content": content[:800]})  # 单条截断
    messages.append(  # 最后附本轮事实
        {  # 用户消息
            "role": "user",  # 用户角色
            "content": (  # 问题、工具名、工具结果
                f"用户问题：{question[:1500]}\n"  # 原问截断
                f"已调用工具：{', '.join(tool_names) or '无'}\n"  # 工具名列表
                f"工具结果：{tool_answer[:3000]}"  # 事实文本截断
            ),  # 内容结束
        }  # 消息结束
    )  # append 结束
    return complete_chat(messages)  # 改写后的中文，或 None
