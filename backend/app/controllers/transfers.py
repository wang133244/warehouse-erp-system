"""库位调拨申请、提交审批、执行。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Header, Query, Request, Response  # 路由、依赖、幂等头、查询、请求与响应
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import UserAccount  # 当前操作用户实体
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user_roles, require_roles  # 查询角色与角色校验
from backend.app.schemas.transfers import TransferUpsert  # 调拨新建/更新 DTO
from backend.app.services.transfer_service import (  # 从调拨服务导入业务函数
    create_transfer,  # 创建调拨单
    execute_transfer,  # 执行调拨扣加库存
    get_transfer,  # 查询调拨详情
    list_transfers,  # 分页列出调拨
    submit_transfer,  # 提交审批
    update_transfer,  # 更新调拨草稿
)  # 调拨服务导入结束


router = APIRouter(prefix="/transfers", tags=["调拨"])  # 调拨路由，前缀 /transfers


def _request_id(request: Request) -> str:  # 从请求状态取出链路 ID
    return getattr(request.state, "request_id", "api")  # 缺省为 "api"


@router.get("")  # GET /transfers，分页列出调拨单
def list_orders(  # 按状态、单号筛选调拨
    current_user: Annotated[  # 管理员、仓管员或仓管经理
        UserAccount,  # 用户实体
        Depends(require_roles("admin", "warehouse_operator", "warehouse_manager")),  # 角色白名单
    ],  # 当前用户注解结束
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    page: Annotated[int, Query(ge=1)] = 1,  # 页码从 1 起
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,  # 每页 1–100
    status: str | None = Query(default=None, max_length=80),  # 按状态筛选
    order_no: str | None = Query(default=None, max_length=64),  # 按单号筛选
) -> dict:  # 返回分页字典
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    return list_transfers(  # 委托调拨服务
        db,  # 会话
        user_id=current_user.user_id,  # 当前用户
        roles=roles,  # 角色
        page=page,  # 页码
        page_size=page_size,  # 每页条数
        status=status,  # 状态过滤
        order_no=order_no,  # 单号过滤
    )  # 返回列表


@router.post("")  # POST /transfers，创建调拨单
def create(  # 新建调拨草稿
    payload: TransferUpsert,  # 备注与明细
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可建
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = create_transfer(  # 调用创建逻辑
        db,  # 会话
        payload=payload,  # 入参
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体


@router.get("/{transfer_id}")  # GET /transfers/{id}，调拨详情
def get_order(  # 查询单张调拨单
    transfer_id: int,  # 调拨主键
    current_user: Annotated[  # 可查看角色
        UserAccount,  # 用户实体
        Depends(require_roles("admin", "warehouse_operator", "warehouse_manager")),  # 角色白名单
    ],  # 当前用户注解结束
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回详情
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    return get_transfer(  # 委托服务
        db,  # 会话
        transfer_id,  # 调拨 ID
        user_id=current_user.user_id,  # 当前用户
        roles=roles,  # 角色
    )  # 返回详情


@router.put("/{transfer_id}")  # PUT /transfers/{id}，更新草稿
def update(  # 覆盖更新调拨明细
    transfer_id: int,  # 调拨主键
    payload: TransferUpsert,  # 新备注与明细
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可改
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = update_transfer(  # 调用更新逻辑
        db,  # 会话
        transfer_id=transfer_id,  # 调拨 ID
        payload=payload,  # 入参
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体


@router.post("/{transfer_id}/submit")  # POST .../submit，提交审批
def submit(  # 将调拨单提交审批
    transfer_id: int,  # 调拨主键
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可提交
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = submit_transfer(  # 调用提交逻辑
        db,  # 会话
        transfer_id=transfer_id,  # 调拨 ID
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体


@router.post("/{transfer_id}/execute")  # POST .../execute，执行调拨
def execute(  # 审批通过后执行库存转移
    transfer_id: int,  # 调拨主键
    request: Request,  # 取 request_id
    response: Response,  # 回写 HTTP 状态
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],  # 管理员或仓管员可执行
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = execute_transfer(  # 调用执行逻辑
        db,  # 会话
        transfer_id=transfer_id,  # 调拨 ID
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务结果
    response.status_code = result.status_code  # 回写状态码
    return result.body  # 返回响应体
