"""盘点单、实盘录入、提交差异。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Header, Query, Request, Response  # 路由、依赖、幂等头、查询、请求与响应
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import UserAccount  # 当前操作用户实体
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user_roles, require_roles  # 查询角色与角色校验
from backend.app.schemas.stock_counts import StockCountUpsert  # 盘点新建/更新 DTO
from backend.app.services.stock_count_service import (  # 从盘点服务导入业务函数
    create_stock_count,  # 创建盘点单
    get_stock_count,  # 查询盘点详情
    list_stock_counts,  # 分页列出盘点
    submit_stock_count,  # 提交盘点差异
    update_stock_count,  # 更新实盘
)  # 盘点服务导入结束


router = APIRouter(prefix="/stock-counts", tags=["盘点"])  # 盘点路由，前缀 /stock-counts


def _request_id(request: Request) -> str:  # 从请求状态取出链路 ID
    return getattr(request.state, "request_id", "api")  # 缺省为 "api"


@router.get("")  # GET /stock-counts，分页列出盘点单
def list_orders(  # 按状态、单号筛选盘点
    current_user: Annotated[  # 管理员、仓管员或仓管经理
        UserAccount,  # 用户实体
        Depends(require_roles("admin", "warehouse_operator", "warehouse_manager")),  # 角色白名单
    ],  # 当前用户注解结束
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    page: Annotated[int, Query(ge=1)] = 1,  # 页码从 1 起
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,  # 每页 1–100
    status: str | None = Query(default=None, max_length=32),  # 按状态筛选
    order_no: str | None = Query(default=None, max_length=64),  # 按单号筛选
) -> dict:  # 返回分页字典
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    return list_stock_counts(  # 委托盘点服务
        db,  # 会话
        user_id=current_user.user_id,  # 当前用户
        roles=roles,  # 角色
        page=page,  # 页码
        page_size=page_size,  # 每页条数
        status=status,  # 状态过滤
        order_no=order_no,  # 单号过滤
    )  # 返回列表


@router.post("")  # POST /stock-counts，创建盘点单
def create(  # 新建盘点草稿
    payload: StockCountUpsert,  # 备注与明细
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可建
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = create_stock_count(  # 调用创建逻辑
        db,  # 会话
        payload=payload,  # 入参
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体


@router.get("/{count_id}")  # GET /stock-counts/{id}，盘点详情
def get_order(  # 查询单张盘点单
    count_id: int,  # 盘点主键
    current_user: Annotated[  # 可查看角色
        UserAccount,  # 用户实体
        Depends(require_roles("admin", "warehouse_operator", "warehouse_manager")),  # 角色白名单
    ],  # 当前用户注解结束
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回详情
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    return get_stock_count(  # 委托服务
        db,  # 会话
        count_id,  # 盘点 ID
        user_id=current_user.user_id,  # 当前用户
        roles=roles,  # 角色
    )  # 返回详情


@router.put("/{count_id}")  # PUT /stock-counts/{id}，更新实盘
def update(  # 覆盖更新盘点明细
    count_id: int,  # 盘点主键
    payload: StockCountUpsert,  # 新备注与明细
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可改
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = update_stock_count(  # 调用更新逻辑
        db,  # 会话
        count_id=count_id,  # 盘点 ID
        payload=payload,  # 入参
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体


@router.post("/{count_id}/submit")  # POST .../submit，提交差异
def submit(  # 提交盘点，生成盘盈盘亏
    count_id: int,  # 盘点主键
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可提交
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = submit_stock_count(  # 调用提交逻辑
        db,  # 会话
        count_id=count_id,  # 盘点 ID
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体
