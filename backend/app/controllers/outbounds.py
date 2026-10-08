"""出库单创建、分配、复核、完成。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型
from fastapi import APIRouter, Depends, Header, Query, Response, status  # 路由、依赖、幂等头、查询、响应与状态码
from sqlalchemy import or_, select  # OR 条件与 SELECT 构造
from sqlalchemy.orm import Session  # ORM 会话类型
from backend.app.models import OutboundItem, OutboundOrder, Product, UserAccount  # 出库单头、明细、商品与用户
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user  # 登录校验
from backend.app.schemas.outbounds import OutboundCreate, OutboundReview  # 建单与复核 DTO
from backend.app.services.outbound_service import allocate_order, complete_order, create_order, review_order  # 分配、完成、创建与复核
router=APIRouter(prefix="/outbounds",tags=["出库"])  # 出库路由，前缀 /outbounds
@router.get("")  # GET /outbounds，列出出库单
def list_orders(  # 按状态与关键字筛选出库单
    _:Annotated[object,Depends(get_current_user)],  # 要求已登录
    db:Annotated[Session,Depends(get_db)],  # 数据库会话
    keyword:str|None=None,  # 可选关键字（单号/状态/SKU/客户 ID）
    status_filter:str|None=Query(default=None, alias="status"),  # 查询参数名 status
):  # 返回 {total, items}
    statement = select(OutboundOrder)  # 基础查询出库单头
    if status_filter:  # 指定状态时精确过滤
        statement = statement.where(OutboundOrder.status == status_filter)  # 按状态筛选
    if keyword:  # 有关键字时模糊匹配单号、状态、SKU 或客户 ID
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        matching_ids = (  # 子查询：明细商品 SKU 匹配的出库单 ID
            select(OutboundItem.outbound_order_id)  # 选出库单 ID
            .join(Product, Product.product_id == OutboundItem.product_id)  # 联商品
            .where(or_(Product.sku_code.like(like), Product.source_product_code.like(like)))  # SKU 或来源编码匹配
        )  # 子查询结束
        conditions = [  # 主查询 OR 条件
            OutboundOrder.order_no.like(like),  # 单号
            OutboundOrder.status.like(like),  # 状态文本
            OutboundOrder.outbound_order_id.in_(matching_ids),  # 明细 SKU 命中
        ]  # 条件列表
        if keyword.strip().isdigit():  # 关键字全是数字时额外按客户 ID 精确匹配
            conditions.append(OutboundOrder.customer_id == int(keyword.strip()))  # 客户 ID
        statement = statement.where(or_(*conditions))  # 合并 OR 条件
    rows=list(db.scalars(statement.order_by(OutboundOrder.outbound_order_id.desc())))  # 按单号 ID 倒序取出
    return {"total": len(rows), "items":[{"outbound_order_id":x.outbound_order_id,"order_no":x.order_no,"status":x.status,"customer_id":x.customer_id,"note":x.note,"created_at":x.created_at}for x in rows]}  # 组装列表（total 为当前结果条数）
@router.post("",status_code=status.HTTP_201_CREATED)  # POST /outbounds，创建出库单，默认 201
def create(payload:OutboundCreate,response:Response,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):  # 建单；幂等命中时可能改写为 200
 body=create_order(db,payload,current_user.user_id,idempotency_key);response.status_code=201 if body.get("status")=="draft"else 200;return body  # 草稿 201，其它状态 200
@router.get("/{order_id}")  # GET /outbounds/{id}，出库单详情
def get_order(order_id:int,_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):  # 查询单头并附明细
 order=db.get(OutboundOrder,order_id)  # 按主键取出库单
 if order is None:from backend.app.core.errors import AppError;raise AppError("NOT_FOUND","出库单不存在",404)  # 不存在则 404
 items=list(db.scalars(select(OutboundItem).where(OutboundItem.outbound_order_id==order_id)))  # 查出该单全部明细
 return {"outbound_order_id":order.outbound_order_id,"order_no":order.order_no,"status":order.status,"items":[{"outbound_item_id":i.outbound_item_id,"product_id":i.product_id,"quantity":i.quantity,"allocated_quantity":i.allocated_quantity,"picked_quantity":i.picked_quantity}for i in items]}  # 组装详情（含已分配/已拣数量）
@router.post("/{order_id}/allocate")  # POST .../allocate，库存分配
def allocate(order_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return allocate_order(db,order_id,current_user.user_id,idempotency_key)  # 委托出库服务预留库存并生成拣货任务
@router.post("/{order_id}/review")  # POST .../review，出库复核
def review(  # 复核出库单
    order_id: int,  # 出库单主键
    payload: OutboundReview,  # 复核意见
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 当前用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回复核结果
    return review_order(db, order_id, current_user.user_id, idempotency_key, payload)  # 委托出库服务复核
@router.post("/{order_id}/complete")  # POST .../complete，完成出库
def complete(order_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return complete_order(db,order_id,current_user.user_id,idempotency_key)  # 委托出库服务扣减库存并完结
