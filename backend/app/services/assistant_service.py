"""助手会话隔离、规划槽位、白名单工具、草稿（不改库存）。"""

from __future__ import annotations  # 启用延后求值类型注解

import re  # 从用户话里抽取 SKU、数量、库位，不写库存

from sqlalchemy import delete, or_, select  # 会话消息增删与只读库存查询
from sqlalchemy.orm import Session  # 会话/消息写入与库存只读共用会话

from backend.app.core.errors import AppError  # 会话不属于当前用户时伪装 404
from backend.app.core.logging import get_logger  # 助手日志，记录拒绝越权会话
from backend.app.models import (  # 助手只用会话、只读库存与待办，不调用写库存函数
    AgentMessage,  # 会话消息（可带草稿 JSON）
    AgentSession,  # 按 user_id 隔离的会话
    AlertAck,  # 预警确认，查询时剔除已处理
    ApprovalTask,  # 待审批只读计数
    Product,  # 解析 SKU
    StockBalance,  # 只读余额，计算可用量
    WarehouseLocation,  # 只读库位码展示
)  # 结束模型导入：助手只读库存与待办，不写余额
from backend.app.services.dashboard_service import LOW_STOCK_THRESHOLD, dashboard_summary  # 低库存阈值与看板只读汇总
from backend.app.services.inventory_service import (  # 复用幂等与可用量公式；绝不调用 apply_inbound/reserve/deduct
    available_units,  # 只读计算可用 = 实际 − 预留 − 冻结
    existing_idempotent_response,  # 会话写操作幂等回放
    record_idempotent_response,  # 记录会话/消息成功响应
    require_idempotency_key,  # 创建/清空/删会话、发消息必须带键
    write_audit,  # 审计助手动作，不写库存流水
)  # 结束库存服务导入：只用幂等与可用量，不调用过账函数
from backend.app.services.report_service import abc_report, daily_report, picking_efficiency, turnover_report, weekly_report  # 只读报表，助手展示用

assistant_logger = get_logger("agent")  # 助手专用日志


SKU_RE = re.compile(r"(?:SKU[-_]?[A-Za-z0-9]+|MS-[A-Za-z0-9._\-]+)", re.IGNORECASE)  # 从话术提取系统 SKU 或来源码
QTY_RE = re.compile(r"数量\s*(\d+)")  # 提取“数量 N”，仅填草稿槽位，不加库存
LOCATION_RE = re.compile(r"库位\s*([A-Za-z0-9\-]+)")  # 提取库位码，仅填草稿
TABLE_HINTS = ("制表", "表格", "做成表", "用表")  # 用户要求表格时才附加 markdown 表
# 问候走说明文案，避免无 SKU 时倒出前 20 条库存。
GREETING_RE = re.compile(  # 纯问候匹配，命中则返回帮助而不 dump 库存
    r"^(你好|您好|嗨|哈喽|在吗|早上好|下午好|晚上好|谢谢|感谢|hello|hi|hey)([!！。.?？~～\s]*)$",  # 仅这些短问候
    re.IGNORECASE,  # 英文问候不区分大小写
)  # 结束问候正则
HELP_TEXT = (  # 能力说明：强调草稿须人工确认、助手不改库存
    "你好，我是仓储助手。我可以查库存、预警、审批和报表，也可以生成入出库或盘点草稿"  # 只读查询 + 草稿
    "（草稿必须到业务页人工确认，我不会直接改库存）。\n"  # 明确不走写库存服务
    "例如：查询 SKU-1 的可用库存；查看预警；请给出 SKU 的 ABC 分类。"  # 示例话术
)  # 结束帮助文案
ASK_SKU_TEXT = "请提供系统 SKU 或商品编码，例如：查询 SKU-1 的可用库存。"  # 缺 SKU 时追问，避免盲查全仓
SUGGEST_LOW_STOCK = (  # 低库存建议：去预警页或生成入库草稿，仍不改库存
    "建议：可用量已低于安全库存，可去预警页确认，或让我生成入库草稿"  # 只建议
    "（需到入库页人工保存，我不会直接改库存）。"  # 再次强调
)  # 结束低库存建议
INVENTORY_HINTS = ("库存", "可用", "库位", "sku", "商品", "还有多少", "在哪", "这个", "那个")  # 库存意图关键词


def format_markdown_table(columns: list[str], rows: list[dict] | None) -> str:  # 把只读查询结果格式化成 markdown 表
    if not columns:  # 无列则不制表
        return ""  # 空字符串，调用方不加表
    header = "| " + " | ".join(str(column) for column in columns) + " |"  # 表头行
    divider = "| " + " | ".join("---" for _ in columns) + " |"  # 对齐分隔行
    body: list[str] = []  # 数据行
    for row in rows or []:  # 无行当空列表
        cells = []  # 本行列单元格
        for column in columns:  # 按列顺序取值
            value = row.get(column, "")  # 缺列当空
            cells.append("" if value is None else str(value))  # None 显示为空串
        body.append("| " + " | ".join(cells) + " |")  # 拼一行
    return "\n".join([header, divider, *body])  # 拼完整表，纯展示


def wants_table(content: str, row_count: int = 0) -> bool:  # 判断是否应附加表格
    if any(hint in (content or "") for hint in TABLE_HINTS):  # 用户明确要表
        return True  # 制表
    return row_count >= 2  # 两行及以上默认制表便于阅读


def _with_table(  # 在助手回复后附加表格，并记一条 format_table 工具调用（仍不改库存）
    text: str,  # 原本文案
    tool_calls: list[dict],  # 已有白名单工具调用
    columns: list[str],  # 表头
    rows: list[dict],  # 只读行
    content: str,  # 用户原话，判断是否要表
) -> tuple[str, list[dict]]:  # 返回新文案与扩展后的 tool_calls
    if not rows or not columns or not wants_table(content, len(rows)):  # 没数据或不需要表
        return text, tool_calls  # 原样返回
    table = format_markdown_table(columns, rows)  # 生成 markdown
    return f"{text}\n\n{table}", [  # 文案后追加表
        *tool_calls,  # 保留原查询工具调用
        {"name": "format_table", "arguments": {"columns": columns, "row_count": len(rows)}},  # 记录制表，无写库存参数
    ]  # 结束 tool_calls


def serialize_session(session: AgentSession) -> dict:  # 会话对外 JSON，不含库存字段
    return {  # 会话摘要
        "session_id": session.session_id,  # 会话 ID
        "title": session.title,  # 标题（首条消息截断）
        "created_at": session.created_at.isoformat() if session.created_at else None,  # 创建时间
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,  # 更新时间
    }  # 结束序列化


def serialize_message(message: AgentMessage) -> dict:  # 消息对外 JSON，draft 仅草稿不表示已过账
    return {  # 消息体
        "message_id": message.message_id,  # 消息 ID
        "session_id": message.session_id,  # 所属会话
        "role": message.role,  # user/assistant
        "content": message.content,  # 文本
        "tool_calls": message.tool_calls or [],  # 白名单工具调用记录
        "draft": message.draft,  # 入出库/盘点草稿 JSON，须到业务页确认
        "created_at": message.created_at.isoformat() if message.created_at else None,  # 时间
    }  # 结束序列化


def create_session(db: Session, user_id: int, key: str) -> dict:  # 为当前用户新建隔离会话，不改库存
    key = require_idempotency_key(key)  # 建会话也要幂等，防连点多开会话
    prior = existing_idempotent_response(db, user_id, key)  # 已创建则回放
    if prior:  # 幂等命中
        return prior  # 返回上次会话，不重复插入
    session = AgentSession(user_id=user_id, title="新会话")  # 绑定当前用户，默认标题
    db.add(session)  # 插入会话行
    db.flush()  # 拿到 session_id
    body = serialize_session(session)  # 组装响应
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/agents/sessions", body=body, status=201)  # 记下 201
    db.commit()  # 只提交会话，不动库存表
    assistant_logger.info("session created user_id=%s session_id=%s", user_id, session.session_id)  # 记录创建
    return body  # 返回新会话


def list_sessions(db: Session, user_id: int) -> dict:  # 只列出当前用户的会话
    rows = list(  # 本用户会话
        db.scalars(  # 标量为会话对象
            select(AgentSession)  # 查会话表
            .where(AgentSession.user_id == user_id)  # 会话隔离：不能看到别人的
            .order_by(AgentSession.session_id.desc())  # 新会话在前
        )  # 结束查询
    )  # 物化
    return {"items": [serialize_session(row) for row in rows]}  # 只读列表


def list_messages(db: Session, session_id: int, user_id: int) -> dict:  # 读消息前校验会话归属
    session = db.get(AgentSession, session_id)  # 加载会话
    if session is None or session.user_id != user_id:  # 不存在或不属于当前用户
        assistant_logger.warning(  # 记录越权或错误 ID，对外统一 404
            "session denied user_id=%s session_id=%s exists=%s owner=%s",  # 模板
            user_id,  # 请求人
            session_id,  # 目标会话
            session is not None,  # 是否存在
            None if session is None else session.user_id,  # 真实主人
        )  # 结束日志
        raise AppError("NOT_FOUND", "会话不存在", 404)  # 不泄露他人会话是否存在
    rows = list(  # 该会话消息
        db.scalars(  # 标量消息
            select(AgentMessage)  # 消息表
            .where(AgentMessage.session_id == session_id)  # 仅本会话
            .order_by(AgentMessage.message_id)  # 时间顺序
        )  # 结束查询
    )  # 物化
    return {"items": [serialize_message(row) for row in rows]}  # 只读，含草稿字段但不改库存


def clear_session(db: Session, session_id: int, user_id: int, key: str) -> dict:  # 清空消息并重置标题，不改库存
    key = require_idempotency_key(key)  # 清空写操作要幂等
    prior = existing_idempotent_response(db, user_id, key)  # 已清空则回放
    if prior:  # 幂等命中
        return prior  # 避免重复删消息
    session = db.get(AgentSession, session_id)  # 加载会话
    if session is None or session.user_id != user_id:  # 归属校验
        raise AppError("NOT_FOUND", "会话不存在", 404)  # 统一 404
    db.execute(delete(AgentMessage).where(AgentMessage.session_id == session_id))  # 只删该会话消息
    session.title = "新会话"  # 标题复位
    db.flush()  # 落盘前刷新
    body = serialize_session(session)  # 返回清空后会话
    record_idempotent_response(  # 记下清空结果
        db,  # 同一事务
        user_id=user_id,  # 用户
        key=key,  # 幂等键
        path=f"/api/v1/agents/sessions/{session_id}/clear",  # 清空路径
        body=body,  # 响应体
    )  # 结束幂等
    write_audit(  # 审计清空会话（与库存无关）
        db,  # 同一事务
        user_id=user_id,  # 操作人
        action="agent_session_clear",  # 动作
        entity_type="agent_session",  # 实体会话
        entity_id=session_id,  # 会话 ID
        after={"cleared": True},  # 快照
    )  # 结束审计
    db.commit()  # 提交消息删除，不碰库存余额
    return body  # 返回会话


def delete_session(db: Session, session_id: int, user_id: int, key: str) -> dict:  # 删除会话及消息；他人会话当 404
    key = require_idempotency_key(key)  # 删除要幂等
    prior = existing_idempotent_response(db, user_id, key)  # 已删则回放成功体
    if prior:  # 幂等命中
        return prior  # 幂等删除视为成功
    session = db.get(AgentSession, session_id)  # 加载会话
    if session is not None and session.user_id != user_id:  # 存在但不是自己的
        raise AppError("NOT_FOUND", "会话不存在", 404)  # 不暴露他人会话
    if session is not None:  # 自己的会话才删
        db.execute(delete(AgentMessage).where(AgentMessage.session_id == session_id))  # 先删消息
        db.delete(session)  # 再删会话头
        db.flush()  # 刷新删除
        write_audit(  # 审计删除
            db,  # 同一事务
            user_id=user_id,  # 操作人
            action="agent_session_delete",  # 删除动作
            entity_type="agent_session",  # 会话
            entity_id=session_id,  # ID
            after={"deleted": True},  # 快照
        )  # 结束审计
    body = {"session_id": session_id, "deleted": True}  # 幂等语义：不存在也返回已删除
    record_idempotent_response(  # 记下删除结果
        db,  # 同一事务
        user_id=user_id,  # 用户
        key=key,  # 幂等键
        path=f"/api/v1/agents/sessions/{session_id}",  # DELETE 路径
        body=body,  # 成功体
    )  # 结束幂等
    db.commit()  # 提交删除，不改库存
    return body  # 返回已删除


def _normalize_sku_token(token: str) -> str:  # 把 SKU1 规范成 SKU-1，便于匹配主数据
    sku_code = token.strip()  # 去掉空白
    upper = sku_code.upper()  # 比较前缀用大写
    if upper.startswith("SKU") and not upper.startswith("SKU-"):  # 缺连字符的 SKU 前缀
        return "SKU-" + sku_code[3:].lstrip("-_")  # 补上连字符
    return sku_code  # 已是标准形态或其它编码


def _resolve_sku(db: Session, content: str) -> str | None:  # 从文本解析并匹配商品，只读 Product
    match = SKU_RE.search(content or "")  # 正则抽出疑似 SKU
    token = match.group(0) if match else None  # 原始命中或空
    candidates: list[str] = []  # 候选编码
    if token:  # 有正则命中才生成候选
        candidates.append(token)  # 原文
        candidates.append(_normalize_sku_token(token))  # 规范化后再试
    for candidate in dict.fromkeys(candidates):  # 去重保序
        like = f"%{candidate}%"  # 模糊模式
        product = db.scalar(  # 只读查商品，不锁库存行
            select(Product).where(  # 精确或模糊匹配 SKU/来源码
                or_(  # 多字段
                    Product.sku_code == candidate,  # 系统 SKU 精确
                    Product.source_product_code == candidate,  # 来源码精确
                    Product.sku_code.like(like),  # SKU 模糊
                    Product.source_product_code.like(like),  # 来源码模糊
                )  # 结束 or_
            )  # 结束 where
        )  # 取第一条商品
        if product:  # 匹配到主数据
            return product.sku_code  # 返回规范系统 SKU
    if token:  # 库中没有仍返回规范化 token，供草稿占位
        return _normalize_sku_token(token)  # 不写库存，只填槽位
    return None  # 话术里没有 SKU


def _inventory_query(db: Session, sku_code: str | None) -> tuple[str, dict]:  # 只读查可用库存，不加锁不过账
    statement = select(Product, StockBalance, WarehouseLocation).join(  # 商品+余额+库位
        StockBalance, StockBalance.product_id == Product.product_id  # 关联余额
    ).join(WarehouseLocation, WarehouseLocation.location_id == StockBalance.location_id)  # 关联库位展示码
    if sku_code:  # 有 SKU 才收窄，避免问候时 dump 全仓
        like = f"%{sku_code}%"  # 模糊
        statement = statement.where(  # SKU/来源码/品名
            or_(  # 多字段
                Product.sku_code == sku_code,  # 精确 SKU
                Product.source_product_code == sku_code,  # 精确来源码
                Product.sku_code.like(like),  # 模糊 SKU
                Product.source_product_code.like(like),  # 模糊来源码
                Product.product_name.like(like),  # 品名
            )  # 结束 or_
        )  # 结束 where
    rows = list(db.execute(statement.limit(20)))  # 最多 20 行，防止刷屏；只读
    if not rows:  # 无余额记录
        text = f"没有找到 {sku_code or '指定商品'} 的库存记录。"  # 文案
        return text, {"sku_code": sku_code, "items": []}  # 空列表，不改库存
    lines = [  # 自然语言行：实际/锁定/冻结/可用
        (  # 一行描述
            f"{product.sku_code} @ {location.location_code}："  # SKU 与库位
            f"实际 {balance.quantity}，锁定 {balance.reserved_quantity}，"  # 实际与预留（只读）
            f"冻结 {balance.frozen_quantity}，可用 {available_units(balance)}"  # 冻结与可用公式
        )  # 结束一行
        for product, balance, location in rows  # 解包查询
    ]  # 结束 lines
    header = f"查询到 {sku_code or '库存'} 的可用库存："  # 前缀
    return header + " " + "；".join(lines), {  # 拼接文案与结构化 items
        "sku_code": sku_code,  # 查询键
        "items": [  # 结构化行供制表
            {  # 一行
                "sku_code": product.sku_code,  # SKU
                "location_code": location.location_code,  # 库位码
                "quantity": balance.quantity,  # 实际（只读）
                "available_quantity": available_units(balance),  # 可用（只读计算）
            }  # 结束一行
            for product, balance, location in rows  # 解包
        ],  # 结束 items
    }  # 结束第二返回值


def _alerts_query(db: Session) -> tuple[str, dict]:  # 只读低库存预警条数（未确认）
    rows = list(  # 可用量 <= 阈值的余额
        db.scalars(  # 标量余额
            select(StockBalance).where(  # 可用公式与看板一致
                StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity  # 可用
                <= LOW_STOCK_THRESHOLD  # 阈值
            )  # 结束 where
        )  # 结束查询
    )  # 物化
    acked = set(db.scalars(select(AlertAck.balance_id)))  # 已确认预警
    pending = [row for row in rows if row.balance_id not in acked]  # 剔除已处理
    return f"当前有 {len(pending)} 条待处理低库存预警。", {"count": len(pending)}  # 只报条数，不改库存


def _approvals_query(db: Session) -> tuple[str, dict]:  # 只读待审批任务数
    count = len(list(db.scalars(select(ApprovalTask).where(ApprovalTask.status == "pending"))))  # pending 计数
    return f"当前有 {count} 条待审批任务。", {"count": count}  # 不审批、不改库存


def _inbound_draft(sku_code: str | None, location_code: str | None, quantity: int | None) -> tuple[str, dict]:  # 生成入库草稿 JSON，不调用 apply_inbound
    draft = {  # 草稿结构与入库页对齐
        "type": "inbound",  # 入库草稿
        "items": [  # 一行槽位
            {  # 槽位字段
                "sku_code": sku_code,  # 商品
                "location_code": location_code,  # 库位（可空）
                "quantity": quantity,  # 数量（可空）
            }  # 结束一行
        ],  # 结束 items
    }  # 结束草稿
    return "已生成入库单草稿，请在入库单页面人工确认后保存，助手不会直接改库存。", draft  # 明确须人工确认


def _sku_from_history(db: Session, history: list[dict[str, str]] | None) -> str | None:  # 从最近对话找回 SKU，优先用户话
    user_contents: list[str] = []  # 用户句
    other_contents: list[str] = []  # 助手句
    for item in reversed(history or []):  # 从近到远扫
        content = item.get("content") or ""  # 文本
        if not content or content.startswith("你好，我是仓储助手"):  # 跳过空句和帮助套话
            continue  # 下一句
        if item.get("role") == "user":  # 用户消息优先
            user_contents.append(content)  # 收集
        else:  # 助手消息作后备
            other_contents.append(content)  # 收集
    for content in user_contents + other_contents:  # 先用户后助手
        sku_code = _resolve_sku(db, content)  # 只读解析
        if sku_code:  # 找到即用
            return sku_code  # 填槽位
    return None  # 历史里也没有


def _resolve_slots(  # 合并本句、规划器与历史，得到 SKU/库位/数量槽位
    db: Session,  # 用于解析 SKU
    content: str,  # 当前用户话
    history: list[dict[str, str]] | None,  # 最近对话
    plan: dict | None,  # 规划器槽位（仍不写库存）
) -> tuple[str | None, str | None, int | None]:  # sku, location, qty
    sku_code = _resolve_sku(db, content)  # 本句 SKU
    location_match = LOCATION_RE.search(content or "")  # 本句库位
    quantity_match = QTY_RE.search(content or "")  # 本句数量
    location_code = location_match.group(1) if location_match else None  # 库位码或空
    quantity = int(quantity_match.group(1)) if quantity_match else None  # 数量或空
    use_history = True  # 默认允许用历史 SKU
    if plan:  # 规划器给出的槽位可补全
        plan_sku = plan.get("sku_code")  # 规划器 SKU
        if plan_sku:  # 有则优先补本句缺失
            sku_code = sku_code or _resolve_sku(db, str(plan_sku)) or str(plan_sku)  # 本句 > 库匹配 > 原文
        if not location_code:  # 本句没库位用规划器
            location_code = plan.get("location_code")  # 补库位
        if quantity is None:  # 本句没数量用规划器
            quantity = plan.get("quantity")  # 补数量
        use_history = bool(plan.get("use_history_sku", True))  # 规划器可禁止沿用历史 SKU
    if not sku_code and use_history:  # 仍缺 SKU 且允许历史
        sku_code = _sku_from_history(db, history)  # 从对话找回
    return sku_code, location_code, quantity  # 仅槽位，不改库存


def _with_suggestion(text: str, kind: str, data: dict | None) -> str:  # 按查询类型追加操作建议，仍不执行写库存
    payload = data or {}  # 空数据当空 dict
    if kind == "inventory":  # 库存查询后看是否低于阈值
        items = payload.get("items") or []  # 只读行
        if items:  # 有行才比较
            lowest = min(int(item.get("available_quantity") or 0) for item in items)  # 最低可用
            if lowest <= LOW_STOCK_THRESHOLD:  # 触发低库存建议
                return f"{text}\n{SUGGEST_LOW_STOCK}"  # 建议草稿/预警页，不自动入库
        return text  # 库存充足不加建议
    if kind == "alerts" and payload.get("count"):  # 有待处理预警
        return f"{text}\n建议：到预警页确认处理，需要补货时可让我生成入库草稿，保存仍须在入库页完成。"  # 强调人工保存
    if kind == "approvals" and payload.get("count"):  # 有待审批
        return f"{text}\n建议：到审批页处理这些待办。"  # 助手不代批
    if kind == "dashboard":  # 看板待办组合建议
        bits = []  # 待办名称
        if payload.get("pending_approvals"):  # 有待审批
            bits.append("审批")  # 加入
        if payload.get("pending_receiving"):  # 有待收货
            bits.append("收货")  # 加入
        if payload.get("pending_review"):  # 有待复核
            bits.append("出库复核")  # 加入
        if bits:  # 有待办才建议
            return f"{text}\n建议：优先处理{'、'.join(bits)}。"  # 只提示，不改单
    return text  # 无建议


def classify_and_run(  # 意图路由：查询/报表/草稿；草稿不调用写库存服务
    db: Session,  # 只读查询与解析 SKU
    content: str,  # 用户当前句
    history: list[dict[str, str]] | None = None,  # 槽位上下文
    plan: dict | None = None,  # 规划器意图
) -> tuple[str, list[dict], dict | None]:  # 文案、工具调用、可选草稿
    sku_code, location_code, quantity = _resolve_slots(db, content, history, plan)  # 填槽位
    text = content or ""  # 原话
    stripped = text.strip()  # 去空白后判断问候
    plan_intent = (plan or {}).get("intent")  # 规划意图
    plan_report = (plan or {}).get("report")  # 报表类型
    plan_draft = (plan or {}).get("draft_type")  # 草稿类型
    if GREETING_RE.match(stripped) or plan_intent == "help" or (  # 问候/帮助或短句且不像库存问询
        len(stripped) <= 6  # 过短
        and not sku_code  # 无 SKU
        and not any(hint in stripped.lower() for hint in INVENTORY_HINTS)  # 无库存关键词
        and "查询" not in stripped  # 非查询
        and "预警" not in stripped  # 非预警
        and "审批" not in stripped  # 非审批
        and "报表" not in stripped  # 非报表
        and "草稿" not in stripped  # 非草稿
        and plan_intent not in {"inventory", "analysis", "exception", "draft", "review"}  # 规划器也非业务意图
    ):  # 结束帮助分支条件
        assistant_logger.info("help reply, skip inventory dump")  # 避免无 SKU dump 前 20 条库存
        return HELP_TEXT, [], None  # 说明文案，无工具、无草稿
    if ("入库" in content and "草稿" in content) or plan_draft == "inbound":  # 入库草稿意图
        if not sku_code:  # 草稿必须有 SKU
            return ASK_SKU_TEXT, [], None  # 追问，不生成空草稿
        text, draft = _inbound_draft(sku_code, location_code, quantity)  # 只生成 JSON 草稿
        return text, [{"name": "create_inbound_draft", "arguments": draft["items"][0]}], draft  # 白名单工具，不 apply_inbound
    if ("出库" in content and "草稿" in content) or plan_draft == "outbound":  # 出库草稿意图
        if not sku_code:  # 缺 SKU
            return ASK_SKU_TEXT, [], None  # 追问
        draft = {"type": "outbound", "items": [{"sku_code": sku_code, "quantity": quantity}]}  # 出库草稿，不 reserve
        return (  # 三元组
            "已生成出库单草稿，请在出库单页面人工确认后保存。",  # 须业务页保存
            [{"name": "create_outbound_draft", "arguments": draft["items"][0]}],  # 白名单
            draft,  # 草稿 JSON
        )  # 结束出库草稿返回
    if ("盘点" in content and "草稿" in content) or plan_draft == "counting":  # 盘点草稿
        if not sku_code:  # 缺 SKU
            return ASK_SKU_TEXT, [], None  # 追问
        draft = {"type": "counting", "items": [{"sku_code": sku_code}]}  # 盘点草稿，不过账
        return "已生成盘点草稿，请在盘点页面人工确认后保存。", [{"name": "create_counting_draft", "arguments": draft["items"][0]}], draft  # 不调用 apply_count_adjustment
    if "预警" in content or plan_intent == "exception":  # 预警查询
        text, data = _alerts_query(db)  # 只读条数
        text = _with_suggestion(text, "alerts", data)  # 追加建议
        return text, [{"name": "query_alerts", "arguments": data}], None  # 无草稿
    if "审批" in content or plan_intent == "review":  # 审批查询
        text, data = _approvals_query(db)  # 只读计数
        text = _with_suggestion(text, "approvals", data)  # 建议去审批页
        return text, [{"name": "query_approvals", "arguments": data}], None  # 不代批
    if "ABC" in content.upper() or ("分类" in content and "报表" in content) or plan_report == "abc":  # ABC 报表
        data = abc_report(db)  # 只读分类
        classes = "、".join(f"{item['sku_code']}={item['class']}" for item in data["items"][:8]) or "暂无商品"  # 摘要前 8
        text = f"ABC 分类基于{data['basis']}：{classes}。"  # 说明依据
        calls = [{"name": "query_abc_report", "arguments": {"count": len(data["items"])}}]  # 白名单
        rows = [  # 制表行
            {  # 一行
                "SKU": item["sku_code"],  # SKU
                "分类": item["class"],  # A/B/C
                "份额": f"{round(float(item['share']) * 100, 1)}%",  # 百分比
            }  # 结束一行
            for item in data["items"][:20]  # 最多 20 行
        ]  # 结束 rows
        text, calls = _with_table(text, calls, ["SKU", "分类", "份额"], rows, content)  # 按需制表
        return text, calls, None  # 无草稿
    if "周转" in content or plan_report == "turnover":  # 周转报表
        data = turnover_report(db)  # 只读
        top = data["items"][0] if data["items"] else None  # 最高周转
        text = (  # 摘要
            f"{top['sku_code']} 周转率 {top['turnover_rate']}，出库量 {top['outbound_quantity']}。"  # 有数据
            if top  # 有第一名
            else "暂无周转数据。"  # 空
        )  # 结束文案
        calls = [{"name": "query_turnover_report", "arguments": {"count": len(data["items"])}}]  # 白名单
        rows = [  # 表行
            {  # 一行
                "SKU": item["sku_code"],  # SKU
                "出库量": item["outbound_quantity"],  # 出库
                "现存量": item["on_hand_quantity"],  # 现存量只读
                "周转率": item["turnover_rate"],  # 比率
            }  # 结束一行
            for item in data["items"][:20]  # 最多 20
        ]  # 结束 rows
        text, calls = _with_table(text, calls, ["SKU", "出库量", "现存量", "周转率"], rows, content)  # 制表
        return text, calls, None  # 无草稿
    if "日报" in content or plan_report == "daily":  # 入出库日报
        data = daily_report(db)  # 只读近 7 日
        today = data["items"][-1] if data["items"] else {"inbound_quantity": 0, "outbound_quantity": 0}  # 最后一天即今日
        text = f"今日入库 {today['inbound_quantity']}，出库 {today['outbound_quantity']}。"  # 摘要
        calls = [{"name": "query_daily_report", "arguments": {"days": data["days"]}}]  # 白名单
        rows = [  # 表行
            {"日期": item["date"], "入库量": item["inbound_quantity"], "出库量": item["outbound_quantity"]}  # 一日
            for item in data["items"]  # 全部天数
        ]  # 结束 rows
        text, calls = _with_table(text, calls, ["日期", "入库量", "出库量"], rows, content)  # 制表
        return text, calls, None  # 无草稿
    if "周报" in content or plan_report == "weekly":  # 周报
        data = weekly_report(db)  # 只读
        current = data["items"][-1] if data["items"] else {"inbound_quantity": 0, "outbound_quantity": 0}  # 本周
        text = f"本周入库 {current['inbound_quantity']}，出库 {current['outbound_quantity']}。"  # 摘要
        calls = [{"name": "query_weekly_report", "arguments": {"weeks": data["weeks"]}}]  # 白名单
        rows = [  # 表行
            {"周": item["week"], "入库量": item["inbound_quantity"], "出库量": item["outbound_quantity"]}  # 一周
            for item in data["items"]  # 各周
        ]  # 结束 rows
        text, calls = _with_table(text, calls, ["周", "入库量", "出库量"], rows, content)  # 制表
        return text, calls, None  # 无草稿
    if "拣货效率" in content or ("拣货" in content and "效率" in content) or plan_report == "picking":  # 拣货效率
        data = picking_efficiency(db)  # 只读任务完成率
        text = f"拣货任务 {data['total_tasks']} 条，完成率 {data['completion_rate']}。"  # 摘要
        return text, [{"name": "query_picking_efficiency", "arguments": data}], None  # 无草稿
    if "看板" in content or "汇总" in content or plan_report == "dashboard":  # 看板汇总
        data = dashboard_summary(db)  # 只读缓存/聚合
        text = (  # 卡片数字
            f"库存总量 {data['stock_quantity']}，待收货 {data['pending_receiving']} 单，"  # 总量与待收货
            f"待复核 {data['pending_review']} 单，待审批 {data['pending_approvals']} 条。"  # 待复核与待审批
        )  # 结束文案
        text = _with_suggestion(text, "dashboard", data)  # 待办建议
        return text, [{"name": "query_dashboard", "arguments": {}}], None  # 无草稿
    if not sku_code and not any(hint in text.lower() for hint in INVENTORY_HINTS) and "查询" not in text and plan_intent != "inventory":  # 无法识别且不像查库存
        assistant_logger.info("unrecognized question, skip inventory dump")  # 不 dump 库存
        return HELP_TEXT, [], None  # 回帮助
    if not sku_code:  # 像查库存但没 SKU
        return ASK_SKU_TEXT, [], None  # 追问 SKU
    text, data = _inventory_query(db, sku_code)  # 默认走只读库存查询
    calls = [{"name": "query_inventory", "arguments": {"sku_code": sku_code, "items": data["items"]}}]  # 白名单查询
    rows = [  # 表行
        {  # 一行
            "SKU": item["sku_code"],  # SKU
            "库位": item["location_code"],  # 库位
            "实际": item["quantity"],  # 实际只读
            "可用": item["available_quantity"],  # 可用只读
        }  # 结束一行
        for item in data["items"]  # 查询结果
    ]  # 结束 rows
    text, calls = _with_table(text, calls, ["SKU", "库位", "实际", "可用"], rows, content)  # 制表
    text = _with_suggestion(text, "inventory", data)  # 低库存则建议草稿
    return text, calls, None  # 查询路径无草稿（除非前面草稿分支）


def post_message(db: Session, session_id: int, user_id: int, content: str, key: str) -> dict:  # 发消息：落库对话并跑助手，不改库存
    key = require_idempotency_key(key)  # 发消息幂等，防连点重复插入
    prior = existing_idempotent_response(db, user_id, key)  # 已处理则回放
    if prior:  # 幂等命中
        return prior  # 不再跑助手、不再插消息
    session = db.get(AgentSession, session_id)  # 加载会话
    if session is None or session.user_id != user_id:  # 隔离校验
        assistant_logger.warning(  # 越权日志
            "session denied user_id=%s session_id=%s exists=%s owner=%s",  # 模板
            user_id,  # 请求人
            session_id,  # 会话
            session is not None,  # 是否存在
            None if session is None else session.user_id,  # 主人
        )  # 结束日志
        raise AppError("NOT_FOUND", "会话不存在", 404)  # 统一 404
    history = [  # 取最近 8 条用户/助手文本作槽位上下文
        {"role": message.role, "content": message.content}  # 只要角色和内容
        for message in db.scalars(  # 本会话消息
            select(AgentMessage)  # 消息表
            .where(AgentMessage.session_id == session_id)  # 本会话
            .order_by(AgentMessage.message_id)  # 顺序
        )  # 结束查询
        if message.role in {"user", "assistant"} and message.content  # 跳过无内容
    ][-8:]  # 只留最近 8 条
    assistant_logger.info(  # 记录请求规模
        "message user_id=%s session_id=%s history_len=%s",  # 模板
        user_id,  # 用户
        session_id,  # 会话
        len(history),  # 历史长度
    )  # 结束日志
    db.add(AgentMessage(session_id=session_id, role="user", content=content))  # 先落用户消息
    from backend.app.agents.graph import run_agents  # 延迟导入规划图，避免循环依赖

    answer, tool_calls, draft = run_agents(  # 规划+白名单工具；内部走 classify_and_run，不改库存
        db, content, history, user_id=user_id, session_id=session_id  # 传入会话上下文
    )  # 得到回复、工具调用、可选草稿
    message = AgentMessage(  # 助手回复消息
        session_id=session_id,  # 同一会话
        role="assistant",  # 助手
        content=answer,  # 文案
        tool_calls=tool_calls,  # 白名单调用记录
        draft=draft,  # 草稿 JSON（若有），仍须业务页确认
    )  # 结束消息字段
    db.add(message)  # 插入助手消息
    if session.title == "新会话":  # 首条用户话当作标题
        session.title = content[:24]  # 截断 24 字
    db.flush()  # 拿到 message_id
    body = serialize_message(message)  # 响应体
    record_idempotent_response(  # 记下本条回复，同键不重复跑图
        db,  # 同一事务
        user_id=user_id,  # 用户
        key=key,  # 幂等键
        path=f"/api/v1/agents/sessions/{session_id}/messages",  # 发消息路径
        body=body,  # 助手消息 JSON
    )  # 结束幂等
    write_audit(  # 审计助手消息（记录用了哪些工具、是否带草稿）
        db,  # 同一事务
        user_id=user_id,  # 用户
        action="agent_message",  # 动作
        entity_type="agent_session",  # 会话
        entity_id=session_id,  # 会话 ID
        after={"tool_calls": [call["name"] for call in tool_calls], "has_draft": draft is not None},  # 不写库存数量
    )  # 结束审计
    db.commit()  # 只提交会话消息，库存余额不变
    return body  # 返回助手消息
