"""入库单列表、创建、确认收货。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型
from fastapi import APIRouter, Depends, Header, Query, Response, status  # 路由、依赖、幂等头、查询、响应与状态码
from sqlalchemy import select  # 构造明细查询
from sqlalchemy.orm import Session  # ORM 会话类型
from backend.app.models import InboundItem, InboundOrder  # 入库单头与明细
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user  # 登录校验
from backend.app.schemas.inbounds import InboundCreate  # 创建入库单 DTO
from backend.app.services.inbound_service import confirm_order, create_order, list_orders  # 确认、创建与列表
router=APIRouter(prefix="/inbounds",tags=["入库"])  # 入库路由，前缀 /inbounds
@router.get("")  # GET /inbounds，列出入库单
def list_inbound_orders(  # 按关键字与状态筛选入库单
    _:Annotated[object,Depends(get_current_user)],  # 要求已登录
    db:Annotated[Session,Depends(get_db)],  # 数据库会话
    keyword:str|None=None,  # 可选关键字
    status_filter:str|None=Query(default=None, alias="status"),  # 查询参数名 status，避免与 FastAPI status 模块冲突
):  # 返回服务层列表
    return list_orders(db, keyword=keyword, status=status_filter)  # 委托入库服务查询
@router.post("",status_code=status.HTTP_201_CREATED)  # POST /inbounds，创建入库单，默认 201
def create(payload:InboundCreate,response:Response,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):  # 建单；幂等命中时可能改写为 200
 body=create_order(db,payload,current_user.user_id,idempotency_key);response.status_code=201 if body.get("status")=="draft" else 200;return body  # 草稿返回 201，其它状态（含幂等重放）返回 200
@router.get("/{order_id}")  # GET /inbounds/{id}，入库单详情
def get_order(order_id:int,_:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):  # 查询单头并附明细
 order=db.get(InboundOrder,order_id)  # 按主键取入库单
 if order is None: from backend.app.core.errors import AppError;raise AppError("NOT_FOUND","入库单不存在",404)  # 不存在则 404
 items=list(db.scalars(select(InboundItem).where(InboundItem.inbound_order_id==order_id)))  # 查出该单全部明细
 return {"inbound_order_id":order.inbound_order_id,"order_no":order.order_no,"status":order.status,"note":order.note,"items":[{"inbound_item_id":i.inbound_item_id,"product_id":i.product_id,"location_id":i.location_id,"quantity":i.quantity}for i in items]}  # 组装详情
@router.post("/{order_id}/confirm")  # POST /inbounds/{id}/confirm，确认收货
def confirm(order_id:int,current_user:Annotated[object,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)],idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None):return confirm_order(db,order_id,current_user.user_id,idempotency_key)  # 委托入库服务确认并写库存
