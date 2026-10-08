"""审批待办、同意、驳回（驳回须填意见）。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Header, Query, Request, Response  # 路由、依赖、幂等头、查询、请求与响应
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import UserAccount  # 当前操作用户实体
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user_roles, require_roles  # 查询角色与角色校验
from backend.app.schemas.approvals import ApprovalDecision  # 审批意见 DTO
from backend.app.services.approval_service import (  # 从审批服务导入业务函数
    approve_task,  # 同意审批
    get_approval,  # 查询单条审批
    list_approvals,  # 分页列出审批
    reject_task,  # 驳回审批
)  # 审批服务导入结束


router = APIRouter(prefix="/approvals", tags=["审批"])  # 审批路由，前缀 /approvals


def _request_id(request: Request) -> str:  # 从请求状态取出链路 ID，缺省为 "api"
    return getattr(request.state, "request_id", "api")  # 供服务层写审计/幂等


@router.get("")  # GET /approvals，分页列出待办/历史审批
def list_tasks(  # 按状态、业务类型、单号筛选审批
    current_user: Annotated[  # 当前用户须为管理员或仓管经理
        UserAccount,  # 用户实体
        Depends(require_roles("admin", "warehouse_manager")),  # 角色白名单
    ],  # 当前用户注解结束
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    page: Annotated[int, Query(ge=1)] = 1,  # 页码从 1 起
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,  # 每页 1–100
    status: str | None = Query(default=None, max_length=32),  # 按审批状态筛选
    business_type: str | None = Query(default=None, max_length=32),  # 按业务类型筛选
    order_no: str | None = Query(default=None, max_length=64),  # 按关联单号筛选
) -> dict:  # 返回分页字典
    roles = get_current_user_roles(db, current_user.user_id)  # 读取当前用户角色
    return list_approvals(  # 委托审批服务分页查询
        db,  # 会话
        user_id=current_user.user_id,  # 用于权限范围
        roles=roles,  # 角色列表
        page=page,  # 页码
        page_size=page_size,  # 每页条数
        status=status,  # 状态过滤
        business_type=business_type,  # 业务类型过滤
        order_no=order_no,  # 单号过滤
    )  # 返回列表结果


@router.get("/{approval_id}")  # GET /approvals/{id}，审批详情
def get_task(  # 查询单条审批（含权限校验）
    approval_id: int,  # 审批主键
    current_user: Annotated[  # 管理员或仓管经理
        UserAccount,  # 用户实体
        Depends(require_roles("admin", "warehouse_manager")),  # 角色白名单
    ],  # 当前用户注解结束
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回详情字典
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    return get_approval(  # 委托服务取详情
        db,  # 会话
        approval_id,  # 审批 ID
        user_id=current_user.user_id,  # 当前用户
        roles=roles,  # 角色
    )  # 返回详情


@router.post("/{approval_id}/approve")  # POST .../approve，同意
def approve(  # 同意审批任务
    approval_id: int,  # 审批主键
    request: Request,  # 用于取 request_id
    response: Response,  # 回写服务层给出的 HTTP 状态
    payload: ApprovalDecision,  # 审批意见
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 仅经理级可批
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = approve_task(  # 调用同意逻辑
        db,  # 会话
        approval_id=approval_id,  # 审批 ID
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        payload=payload,  # 意见
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务返回带 status_code 的结果
    response.status_code = result.status_code  # 把服务状态码写回 HTTP
    return result.body  # 返回响应体


@router.post("/{approval_id}/reject")  # POST .../reject，驳回
def reject(  # 驳回审批任务（意见由 schema 约束）
    approval_id: int,  # 审批主键
    request: Request,  # 用于取 request_id
    response: Response,  # 回写 HTTP 状态
    payload: ApprovalDecision,  # 驳回意见
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 仅经理级可驳
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
) -> dict:  # 返回业务体
    roles = get_current_user_roles(db, current_user.user_id)  # 读取角色
    result = reject_task(  # 调用驳回逻辑
        db,  # 会话
        approval_id=approval_id,  # 审批 ID
        user_id=current_user.user_id,  # 操作者
        roles=roles,  # 角色
        payload=payload,  # 意见
        key=idempotency_key,  # 幂等键
        request_id=_request_id(request),  # 链路 ID
    )  # 服务返回带 status_code 的结果
    response.status_code = result.status_code  # 把服务状态码写回 HTTP
    return result.body  # 返回响应体
