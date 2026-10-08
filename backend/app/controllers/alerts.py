"""低库存预警列表、确认、生成补货草稿。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Header, Query  # 路由、依赖、幂等头与查询参数
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import UserAccount  # 当前操作用户实体
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user, require_roles  # 登录校验与角色校验
from backend.app.schemas.followup import AlertAckCreate  # 预警确认备注 DTO
from backend.app.services.alert_service import ack_alert, list_alerts  # 确认预警与列出预警

router = APIRouter(prefix="/alerts", tags=["预警"])  # 预警路由，前缀 /alerts


@router.get("")  # GET /alerts，分页列出低库存预警
def alerts(  # 查询低库存预警列表
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    threshold: int = Query(10, ge=0),  # 可用量低于该阈值视为预警，默认 10
    offset: int = Query(0, ge=0),  # 分页偏移
    limit: int = Query(50, ge=1, le=200),  # 每页条数，1–200
    keyword: str | None = None,  # 可选关键字过滤
):  # 返回服务层列表结构
    return list_alerts(db, threshold, offset, limit, keyword)  # 委托预警服务查询


@router.post("/{balance_id}/ack")  # POST /alerts/{balance_id}/ack，确认一条预警
def ack(  # 确认预警并可带备注
    balance_id: int,  # 库存余额主键，标识预警行
    payload: AlertAckCreate,  # 确认备注
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager", "warehouse_operator", "operator"))],  # 仓管相关角色可确认
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回确认结果
    return ack_alert(db, balance_id, current_user.user_id, idempotency_key, payload.note)  # 委托服务写入确认记录
