"""操作审计查询与导出。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型
from fastapi import APIRouter, Depends, Query  # 路由、依赖与查询参数
from sqlalchemy import or_, select  # OR 条件与 SELECT 构造
from sqlalchemy.orm import Session  # ORM 会话类型
from backend.app.models import AuditLog, UserAccount  # 审计日志与用户表，用于联查用户名
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user  # 登录校验
from backend.app.services.user_service import account_names  # 批量把 user_id 映射为用户名

router = APIRouter(prefix="/audit-logs", tags=["审计"])  # 审计路由，前缀 /audit-logs


@router.get("")  # GET /audit-logs，列出最近审计记录
def list_logs(  # 按关键字筛选并返回审计列表
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    keyword: str | None = None,  # 可选关键字，匹配动作/实体/用户名
    limit: int = Query(100, ge=1, le=500),  # 最多返回条数，默认 100
):  # 返回 {items: [...]}
    statement = select(AuditLog)  # 基础查询审计表
    if keyword:  # 有关键字时做模糊匹配
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        statement = statement.outerjoin(UserAccount, UserAccount.user_id == AuditLog.user_id)  # 左连用户表以便搜用户名
        statement = statement.where(  # 动作、实体类型或用户名任一匹配
            or_(  # 三个字段 OR
                AuditLog.action.like(like),  # 动作描述
                AuditLog.entity_type.like(like),  # 实体类型
                UserAccount.username.like(like),  # 操作者用户名
            )  # OR 条件结束
        )  # where 结束
    rows = list(db.scalars(statement.order_by(AuditLog.audit_log_id.desc()).limit(limit)))  # 按 ID 倒序并截断
    names = account_names(db, {row.user_id for row in rows if row.user_id})  # 批量查有 user_id 的显示名
    return {  # 组装列表响应
        "items": [  # 审计条目数组
            {  # 单条审计
                "audit_log_id": row.audit_log_id,  # 审计主键
                "action": row.action,  # 动作
                "entity_type": row.entity_type,  # 实体类型
                "entity_id": row.entity_id,  # 实体 ID
                "user_id": row.user_id,  # 操作者 ID
                "username": names.get(row.user_id) if row.user_id else None,  # 有用户则填用户名
                "created_at": row.created_at,  # 发生时间
            }  # 单条结束
            for row in rows  # 遍历查询结果
        ]  # items 结束
    }  # 响应结束
