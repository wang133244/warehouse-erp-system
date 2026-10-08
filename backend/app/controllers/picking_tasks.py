"""拣货任务列表与确认拣货。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型
from fastapi import APIRouter, Depends, Header, Query  # 路由、依赖、幂等头与查询参数
from sqlalchemy import or_, select  # OR 条件与 SELECT 构造
from sqlalchemy.orm import Session  # ORM 会话类型
from backend.app.models import PickingTask, Product, WarehouseLocation  # 拣货任务、商品与库位，用于关键字联查
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user  # 登录校验
from backend.app.services.outbound_service import confirm_task  # 确认拣货并回写出库明细
router=APIRouter(prefix="/picking-tasks",tags=["拣货"])  # 拣货路由，前缀 /picking-tasks
@router.get("")  # GET /picking-tasks，列出拣货任务
def list_tasks(  # 可按单号/状态/SKU/库位关键字筛选
    _:Annotated[object,Depends(get_current_user)],  # 要求已登录
    db:Annotated[Session,Depends(get_db)],  # 数据库会话
    keyword:str|None=None,  # 可选关键字
):  # 返回 {items: [...]}
    statement = select(PickingTask)  # 基础查询拣货任务
    if keyword:  # 有关键字时联表模糊匹配
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        statement = (  # 联商品与库位后过滤
            statement.join(Product, Product.product_id == PickingTask.product_id)  # 联商品取 SKU
            .join(WarehouseLocation, WarehouseLocation.location_id == PickingTask.location_id)  # 联库位取编码
            .where(  # 任务号、状态、SKU 或库位编码任一匹配
                or_(  # OR 条件组
                    PickingTask.task_no.like(like),  # 任务号
                    PickingTask.status.like(like),  # 状态
                    Product.sku_code.like(like),  # 按商品 SKU 模糊匹配
                    WarehouseLocation.location_code.like(like),  # 库位编码
                )  # OR 结束
            )  # where 结束
        )  # 联表查询结束
    rows=list(db.scalars(statement.order_by(PickingTask.picking_task_id.desc())))  # 按任务 ID 倒序取出
    return {"items":[{"picking_task_id":x.picking_task_id,"task_no":x.task_no,"outbound_order_id":x.outbound_order_id,"product_id":x.product_id,"location_id":x.location_id,"quantity":x.quantity,"status":x.status}for x in rows]}  # 组装任务列表
@router.post("/{task_id}/confirm")  # POST /picking-tasks/{id}/confirm，确认拣货
def confirm(task_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return confirm_task(db,task_id,current_user.user_id,idempotency_key)  # 委托出库服务确认该任务
