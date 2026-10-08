"""助手会话、用户管理、系统 runtime。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Header, Query, Response  # 路由、依赖、幂等头、查询与原始响应
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import UserAccount  # 当前操作用户实体
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user, require_roles  # 登录校验与角色校验
from backend.app.schemas.followup import AgentMessageCreate, UserCreate, UserUpdate  # 助手消息与用户增改 DTO
from backend.app.schemas.inbounds import ReceiveConfirm  # 收货确认入参
from backend.app.services import alert_service, assistant_service, dashboard_service, user_service  # 导出 CSV、助手、看板与用户服务
from backend.app.services.inbound_service import confirm_order, list_receivings  # 收货队列与确认
from backend.app.services.outbound_service import list_reviews  # 出库复核队列

users_router = APIRouter(prefix="/users", tags=["用户"])  # 用户管理路由
roles_router = APIRouter(prefix="/roles", tags=["用户"])  # 角色列表路由
receivings_router = APIRouter(prefix="/receivings", tags=["收货确认"])  # 收货确认队列
reviews_router = APIRouter(prefix="/outbound-reviews", tags=["出库复核"])  # 出库复核队列
agents_router = APIRouter(prefix="/agents", tags=["智能助手"])  # 智能助手会话
exports_router = APIRouter(prefix="/exports", tags=["导出"])  # CSV 导出
dashboard_router = APIRouter(prefix="/dashboard", tags=["看板"])  # 工作台看板
system_router = APIRouter(prefix="/system", tags=["系统"])  # 运行时信息


@users_router.get("")  # GET /users，列出用户
def list_users(  # 管理员按关键字查用户
    _: Annotated[UserAccount, Depends(require_roles("admin"))],  # 仅管理员
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    keyword: str | None = None,  # 可选关键字
) -> dict:  # 返回用户列表
    return user_service.list_users(db, keyword)  # 委托用户服务


@users_router.post("", status_code=201)  # POST /users，创建用户
def create_user(  # 新建账号并赋角色
    payload: UserCreate,  # 用户名、密码、角色等
    current_user: Annotated[UserAccount, Depends(require_roles("admin"))],  # 仅管理员
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回创建结果
    return user_service.create_user(db, payload, current_user.user_id, idempotency_key)  # 委托用户服务


@users_router.patch("/{user_id}")  # PATCH /users/{id}，更新用户
def update_user(  # 改显示名、密码、角色、仓库或启用状态
    user_id: int,  # 目标用户主键
    payload: UserUpdate,  # 待更新字段
    current_user: Annotated[UserAccount, Depends(require_roles("admin"))],  # 仅管理员
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回更新结果
    return user_service.update_user(db, user_id, payload, current_user.user_id, idempotency_key)  # 委托用户服务


@users_router.delete("/{user_id}")  # DELETE /users/{id}，删除/停用用户
def delete_user(  # 删除指定用户
    user_id: int,  # 目标用户主键
    current_user: Annotated[UserAccount, Depends(require_roles("admin"))],  # 仅管理员
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回删除结果
    return user_service.delete_user(db, user_id, current_user.user_id, idempotency_key)  # 委托用户服务


@roles_router.get("")  # GET /roles，列出系统角色
def list_roles(  # 管理员查看角色字典
    _: Annotated[UserAccount, Depends(require_roles("admin"))],  # 仅管理员
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回角色列表
    return user_service.list_roles(db)  # 委托用户服务


@receivings_router.get("")  # GET /receivings，待收货队列
def list_receiving_queue(  # 列出待确认收货的入库单
    _: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager", "warehouse_operator", "operator"))],  # 仓管相关角色
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回队列
    return list_receivings(db)  # 委托入库服务


@receivings_router.post("/{order_id}/confirm")  # POST /receivings/{id}/confirm，确认收货
def confirm_receiving(  # 按实收明细确认入库
    order_id: int,  # 入库单主键
    payload: ReceiveConfirm,  # 实收数量与备注
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager", "warehouse_operator", "operator"))],  # 仓管相关角色
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回确认结果
    return confirm_order(db, order_id, current_user.user_id, idempotency_key, payload)  # 委托入库服务写库存


@reviews_router.get("")  # GET /outbound-reviews，待复核出库
def list_outbound_reviews(  # 列出待复核出库单
    _: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager", "warehouse_operator", "operator"))],  # 仓管相关角色
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    keyword: str | None = None,  # 可选关键字
) -> dict:  # 返回队列
    return list_reviews(db, keyword)  # 委托出库服务


@agents_router.post("/sessions", status_code=201)  # POST /agents/sessions，新建助手会话
def create_agent_session(  # 为当前用户创建会话
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 已登录用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回会话
    return assistant_service.create_session(db, current_user.user_id, idempotency_key)  # 委托助手服务


@agents_router.get("/sessions")  # GET /agents/sessions，列出会话
def list_agent_sessions(  # 当前用户的助手会话列表
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 已登录用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回会话列表
    return assistant_service.list_sessions(db, current_user.user_id)  # 委托助手服务


@agents_router.post("/sessions/{session_id}/messages")  # POST .../messages，发送消息
def post_agent_message(  # 向会话追加用户消息并触发回复
    session_id: int,  # 会话主键
    payload: AgentMessageCreate,  # 消息正文
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 已登录用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回助手回复
    return assistant_service.post_message(db, session_id, current_user.user_id, payload.content, idempotency_key)  # 委托助手服务


@agents_router.get("/sessions/{session_id}/messages")  # GET .../messages，历史消息
def list_agent_messages(  # 读取某会话消息
    session_id: int,  # 会话主键
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 已登录用户（校验归属）
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回消息列表
    return assistant_service.list_messages(db, session_id, current_user.user_id)  # 委托助手服务


@agents_router.post("/sessions/{session_id}/clear")  # POST .../clear，清空会话消息
def clear_agent_session(  # 保留会话但清空历史
    session_id: int,  # 会话主键
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 已登录用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回清空结果
    return assistant_service.clear_session(db, session_id, current_user.user_id, idempotency_key)  # 委托助手服务


@agents_router.delete("/sessions/{session_id}")  # DELETE /agents/sessions/{id}，删除会话
def delete_agent_session(  # 删除指定助手会话
    session_id: int,  # 会话主键
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 已登录用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回删除结果
    return assistant_service.delete_session(db, session_id, current_user.user_id, idempotency_key)  # 委托助手服务


@exports_router.get("/inventory")  # GET /exports/inventory，导出库存 CSV
def export_inventory(  # 下载库存余额 CSV
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> Response:  # 返回 CSV 文件响应
    return Response(content=alert_service.inventory_csv(db), media_type="text/csv; charset=utf-8")  # 以 UTF-8 返回库存 CSV


@exports_router.get("/ledgers")  # GET /exports/ledgers，导出流水 CSV
def export_ledgers(  # 下载最近库存流水
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    limit: int = Query(500, ge=1, le=2000),  # 导出条数上限
) -> Response:  # 返回 CSV
    return Response(content=alert_service.ledger_csv(db, limit), media_type="text/csv; charset=utf-8")  # 以 UTF-8 返回流水 CSV


@exports_router.get("/audit")  # GET /exports/audit，导出审计 CSV
def export_audit(  # 下载最近审计日志
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    limit: int = Query(500, ge=1, le=2000),  # 导出条数上限
) -> Response:  # 返回 CSV
    return Response(content=alert_service.audit_csv(db, limit), media_type="text/csv; charset=utf-8")  # 以 UTF-8 返回审计 CSV


@dashboard_router.get("/summary")  # GET /dashboard/summary，看板摘要
def summary(  # 工作台数字摘要
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回摘要
    return dashboard_service.dashboard_summary(db)  # 委托看板服务


@dashboard_router.get("/charts")  # GET /dashboard/charts，看板图表
def charts(  # 工作台图表数据
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回图表
    return dashboard_service.dashboard_charts(db)  # 委托看板服务


@system_router.get("/runtime")  # GET /system/runtime，运行时配置快照
def runtime(_: Annotated[UserAccount, Depends(get_current_user)]) -> dict:  # 需登录，不查库
    from backend.app.agents.graph import GRAPH_ENGINE  # 延迟导入图引擎标识，避免循环依赖
    from backend.app.agents.llm import llm_provider  # 延迟导入当前 LLM 提供方
    from backend.app.core.cache import get_cache_backend  # 延迟导入缓存后端名称

    return {  # 组装运行时快照
        "cache_backend": get_cache_backend(),  # 当前缓存后端
        "graph_engine": GRAPH_ENGINE,  # 智能体图引擎
        "llm_provider": llm_provider(),  # 当前 LLM 提供方
        "inventory_source": "mysql",  # 库存数据来源固定为 MySQL
    }  # 返回运行时字典
