"""库存查询、流水、可用量、看板与导出；不在此写库存。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Query  # 路由、依赖与查询参数
from sqlalchemy import false, func, or_, select  # 永假条件、聚合、OR 与 SELECT
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.core.cache import STOCK_PREFIX, cache_get_json, cache_set_json  # 库存缓存前缀与 JSON 读写
from backend.app.models import Product, StockBalance, StockLedger, UserAccount, WarehouseLocation  # 商品、余额、流水、用户与库位
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user, get_current_user_roles, granted_warehouse_ids  # 登录、角色与仓库授权范围
from backend.app.services.inventory_service import available_units  # 计算单行可用量（在库-预留-冻结）

router = APIRouter(prefix="/inventory", tags=["库存"])  # 库存查询路由，前缀 /inventory


def _scope_filter(db: Session, user: UserAccount):  # 按用户角色算出可访问的仓库 ID 集合
    roles = get_current_user_roles(db, user.user_id)  # 读取角色
    return granted_warehouse_ids(db, user.user_id, roles)  # None 表示不限制；空集合表示无仓库权限


def _balance_statement(granted: set[int] | None):  # 构造余额查询与计数，并套仓库范围
    statement = select(StockBalance).join(  # 余额联库位以便按仓库过滤
        WarehouseLocation, WarehouseLocation.location_id == StockBalance.location_id  # 库位外键
    )  # 数据查询联表结束
    count_statement = (  # 同步的计数查询
        select(func.count())  # 对余额行计数
        .select_from(StockBalance)  # 从余额表起算
        .join(WarehouseLocation, WarehouseLocation.location_id == StockBalance.location_id)  # 同样联库位
    )  # 计数查询结束
    if granted is not None:  # 非超管范围时需要过滤仓库
        if granted:  # 有授权仓库
            statement = statement.where(WarehouseLocation.warehouse_id.in_(granted))  # 数据限制在授权仓
            count_statement = count_statement.where(WarehouseLocation.warehouse_id.in_(granted))  # 计数同样限制
        else:  # 授权集合为空：看不到任何库存
            statement = statement.where(false())  # 永假，返回空
            count_statement = count_statement.where(false())  # 计数为 0
    return statement, count_statement  # 返回成对查询


@router.get("/balances")  # GET /inventory/balances，分页列库存余额
def balances(  # 可按商品、关键字、仅可用筛选
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 当前用户（用于仓库范围）
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    product_id: int | None = None,  # 按商品过滤
    keyword: str | None = None,  # 模糊匹配 SKU/名称/库位
    available_only: bool = Query(False),  # 为真时只返回可用量 > 0 的行
    offset: int = Query(0, ge=0),  # 分页偏移
    limit: int = Query(50, ge=1, le=200),  # 每页 1–200
):  # 返回 {total, items}
    granted = _scope_filter(db, current_user)  # 仓库授权范围
    statement, count_statement = _balance_statement(granted)  # 带范围的查询对
    if product_id is not None:  # 指定商品
        statement = statement.where(StockBalance.product_id == product_id)  # 数据按商品过滤
        count_statement = count_statement.where(StockBalance.product_id == product_id)  # 计数同步过滤
    if available_only:  # 只要有可用量的行
        available_expr = (  # 可用 = 在库 - 预留 - 冻结
            StockBalance.quantity  # 在库数量
            - StockBalance.reserved_quantity  # 减去已预留
            - func.coalesce(StockBalance.frozen_quantity, 0)  # 减去冻结，空当 0
        )  # 可用量表达式
        statement = statement.where(available_expr > 0)  # 数据过滤
        count_statement = count_statement.where(available_expr > 0)  # 计数过滤
    if keyword:  # 有关键字时联商品表
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        statement = statement.join(Product, Product.product_id == StockBalance.product_id)  # 数据查询联商品
        count_statement = count_statement.join(Product, Product.product_id == StockBalance.product_id)  # 计数联商品
        match = or_(  # SKU、来源编码、名称或库位编码/库区
            Product.sku_code.like(like),  # 内部 SKU
            Product.source_product_code.like(like),  # 来源编码
            Product.product_name.like(like),  # 商品名称
            WarehouseLocation.location_code.like(like),  # 库位编码
            WarehouseLocation.zone_code.like(like),  # 库区
        )  # OR 结束
        statement = statement.where(match)  # 数据应用关键字
        count_statement = count_statement.where(match)  # 计数应用关键字
    rows = list(db.scalars(statement.order_by(StockBalance.balance_id).offset(offset).limit(limit)))  # 分页取出余额行
    products = {  # 本页涉及商品，便于填 SKU
        item.product_id: item  # 以商品主键为键映射商品实体
        for item in db.scalars(select(Product).where(Product.product_id.in_({row.product_id for row in rows} or {-1})))  # 空集用 -1 避免 IN ()
    }  # 商品字典结束
    locations = {  # 本页涉及库位，便于填库位编码
        item.location_id: item  # 以库位主键为键映射库位实体
        for item in db.scalars(  # 批量查库位
            select(WarehouseLocation).where(WarehouseLocation.location_id.in_({row.location_id for row in rows} or {-1}))  # 空集用 -1
        )  # scalars 结束
    }  # 库位字典结束
    return {  # 组装分页响应
        "total": db.scalar(count_statement) or 0,  # 符合条件的总行数
        "items": [  # 当前页
            {  # 单行余额
                "balance_id": row.balance_id,  # 余额主键
                "product_id": row.product_id,  # 商品 ID
                "location_id": row.location_id,  # 库位 ID
                "quantity": row.quantity,  # 在库数量
                "reserved_quantity": row.reserved_quantity,  # 预留数量
                "frozen_quantity": row.frozen_quantity,  # 冻结数量
                "available_quantity": available_units(row),  # 计算可用量
                "sku_code": products.get(row.product_id).sku_code if products.get(row.product_id) else None,  # 有商品则填 SKU
                "source_product_code": products.get(row.product_id).source_product_code if products.get(row.product_id) else None,  # 来源编码
                "location_code": locations.get(row.location_id).location_code if locations.get(row.location_id) else None,  # 库位编码
                "updated_at": row.updated_at,  # 最后更新时间
            }  # 单行结束
            for row in rows  # 遍历本页
        ],  # items 结束
    }  # 响应结束


@router.get("/{product_id}/availability")  # GET /inventory/{id}/availability，商品可用量汇总
def availability(  # 在授权仓库范围内汇总在库/预留/冻结
    product_id: int,  # 商品主键
    current_user: Annotated[UserAccount, Depends(get_current_user)],  # 当前用户
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
):  # 返回汇总字典
    granted = _scope_filter(db, current_user)  # 仓库范围
    cache_key = f"{STOCK_PREFIX}availability:{product_id}:{current_user.user_id}"  # 按商品+用户缓存（范围因人而异）
    cached = cache_get_json(cache_key)  # 尝试读缓存
    if cached is not None:  # 命中则直接返回
        return cached  # 跳过数据库
    statement = (  # 汇总该商品在范围内的三类数量
        select(  # 三列 SUM，空当 0
            func.coalesce(func.sum(StockBalance.quantity), 0),  # 在库合计
            func.coalesce(func.sum(StockBalance.reserved_quantity), 0),  # 预留合计
            func.coalesce(func.sum(StockBalance.frozen_quantity), 0),  # 冻结合计
        )  # select 列结束
        .select_from(StockBalance)  # 从余额表
        .join(WarehouseLocation, WarehouseLocation.location_id == StockBalance.location_id)  # 联库位以便按仓过滤
        .where(StockBalance.product_id == product_id)  # 限定商品
    )  # 汇总语句骨架
    if granted is not None:  # 需要按仓限制
        if granted:  # 有授权仓库
            statement = statement.where(WarehouseLocation.warehouse_id.in_(granted))  # 限制仓库
        else:  # 无授权仓库
            statement = statement.where(false())  # 永假，合计为 0
    quantity, reserved, frozen = db.execute(statement).one()  # 取出三列合计
    body = {  # 组装可用量响应
        "product_id": product_id,  # 商品 ID
        "quantity": int(quantity),  # 在库
        "reserved_quantity": int(reserved),  # 预留
        "frozen_quantity": int(frozen),  # 冻结
        "available_quantity": int(quantity) - int(reserved) - int(frozen),  # 可用
    }  # 响应体结束
    cache_set_json(cache_key, body, 30)  # 缓存 30 秒
    return body  # 返回汇总


@router.get("/ledgers")  # GET /inventory/ledgers，库存流水
def ledgers(  # 按关键字筛选最近流水（本接口不按仓库授权裁剪）
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    keyword: str | None = None,  # 类型中文别名、SKU 或库位
    limit: int = Query(100, ge=1, le=500),  # 最多返回条数
):  # 返回 {items: [...]}
    statement = (  # 流水联商品与库位，便于关键字搜索
        select(StockLedger)  # 选流水行
        .join(Product, Product.product_id == StockLedger.product_id)  # 联商品
        .join(WarehouseLocation, WarehouseLocation.location_id == StockLedger.location_id)  # 联库位
    )  # 基础查询结束
    if keyword:  # 有关键字时匹配类型/SKU/库位
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        type_aliases = {  # 中文类型名映射到流水 transaction_type
            "入库": "inbound",  # 入库
            "出库": "outbound",  # 出库
            "盘盈": "count_gain",  # 盘盈
            "盘亏": "count_loss",  # 盘亏
            "调拨入": "transfer_in",  # 调拨入
            "调拨出": "transfer_out",  # 调拨出
        }  # 别名表结束
        type_value = type_aliases.get(keyword.strip())  # 若整词命中中文别名则精确匹配类型
        type_match = StockLedger.transaction_type == type_value if type_value else StockLedger.transaction_type.like(like)  # 否则对类型字段模糊匹配
        statement = statement.where(  # 类型、SKU、来源编码或库位任一匹配
            or_(  # OR 条件组
                type_match,  # 交易类型
                Product.sku_code.like(like),  # 按商品 SKU 模糊匹配
                Product.source_product_code.like(like),  # 来源编码
                WarehouseLocation.location_code.like(like),  # 库位编码
            )  # OR 结束
        )  # where 结束
    rows = list(db.scalars(statement.order_by(StockLedger.ledger_id.desc()).limit(limit)))  # 按流水 ID 倒序截断
    return {  # 组装列表
        "items": [  # 流水数组
            {  # 单条流水
                "ledger_id": row.ledger_id,  # 流水主键
                "product_id": row.product_id,  # 商品
                "location_id": row.location_id,  # 库位
                "transaction_type": row.transaction_type,  # 交易类型
                "quantity_delta": row.quantity_delta,  # 数量变化
                "before_quantity": row.before_quantity,  # 变动前
                "after_quantity": row.after_quantity,  # 变动后
                "source_type": row.source_type,  # 来源单据类型
                "source_id": row.source_id,  # 来源单据 ID
                "created_at": row.created_at,  # 发生时间
            }  # 单条结束
            for row in rows  # 遍历结果
        ]  # items 结束
    }  # 响应结束
