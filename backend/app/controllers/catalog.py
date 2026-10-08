"""商品/仓库/库位 CRUD、库位地图、商品 CSV 导入。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status  # 路由、依赖、幂等头、HTTP 异常、查询与状态码
from sqlalchemy import func, or_, select  # 聚合计数、OR 条件与 SELECT
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import DataImportBatch, Product, UserAccount, Warehouse, WarehouseLocation  # 导入批次、商品、用户、仓库与库位
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user, require_roles  # 登录校验与角色校验
from backend.app.schemas.catalog import ImportBatchResponse, LocationResponse, ProductResponse, WarehouseResponse  # 基础资料出参 DTO
from backend.app.schemas.followup import LocationCreate, LocationUpdate, ProductCreate, ProductCsvImport, ProductUpdate, WarehouseCreate  # 基础资料入参 DTO
from backend.app.services.catalog_service import (  # 从基础资料服务导入写操作
    create_location,  # 新建库位
    create_product,  # 新建商品
    create_warehouse,  # 新建仓库
    import_product_csv,  # CSV 导入商品
    list_location_map,  # 库位地图数据
    update_location,  # 更新库位
    update_product,  # 更新商品
)  # 基础资料服务导入结束

router = APIRouter(tags=["基础资料"])  # 无统一前缀，各接口自带 /products 等路径


def _page(stmt, count_stmt, db: Session, offset: int, limit: int):  # 通用分页：算总数并切片
    return {"total": db.scalar(count_stmt) or 0, "items": list(db.scalars(stmt.offset(offset).limit(limit)))}  # total 为 0 时用 0 兜底


@router.get("/products")  # GET /products，分页列商品
def list_products(  # 按 SKU/名称/品牌/来源编码关键字筛选
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    keyword: str | None = None,  # 可选关键字
    offset: int = Query(0, ge=0),  # 分页偏移
    limit: int = Query(50, ge=1, le=200),  # 每页 1–200
):  # 返回 {total, items}
    where = []  # 动态 WHERE 条件列表
    if keyword:  # 有关键字时模糊匹配多个字段
        like = f"%{keyword}%"  # 构造 LIKE 模式
        where.append(or_(Product.sku_code.like(like), Product.product_name.like(like), Product.brand.like(like), Product.source_product_code.like(like)))  # SKU/名称/品牌/来源编码
    return _page(  # 分页查询商品
        select(Product).where(*where).order_by(Product.product_id),  # 数据查询按 ID 排序
        select(func.count()).select_from(Product).where(*where),  # 计数查询
        db,  # 会话
        offset,  # 偏移
        limit,  # 条数
    )  # 返回分页结果


@router.post("/products", status_code=status.HTTP_201_CREATED)  # POST /products，新建商品
def add_product(  # 创建商品，支持幂等
    payload: ProductCreate,  # 商品字段
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 管理员或仓管经理
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回创建结果
    return create_product(db, payload, current_user.user_id, idempotency_key)  # 委托目录服务


@router.patch("/products/{product_id}")  # PATCH /products/{id}，部分更新商品
def patch_product(  # 更新商品字段
    product_id: int,  # 商品主键
    payload: ProductUpdate,  # 待更新字段
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 管理员或仓管经理
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回更新结果
    return update_product(db, product_id, payload, current_user.user_id, idempotency_key)  # 委托目录服务


@router.get("/products/{product_id}", response_model=ProductResponse)  # GET /products/{id}，商品详情
def get_product(product_id: int, _: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):  # 按主键取商品
    product = db.get(Product, product_id)  # 查询商品
    if product is None:  # 不存在
        raise HTTPException(status_code=404, detail="商品不存在")  # 返回 404
    return product  # ORM 经 from_attributes 转 DTO


@router.get("/warehouses")  # GET /warehouses，列出全部仓库
def list_warehouses(_: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):  # 不分页返回全部仓库
    return {  # 组装列表
        "total": db.scalar(select(func.count()).select_from(Warehouse)) or 0,  # 仓库总数
        "items": list(db.scalars(select(Warehouse).order_by(Warehouse.warehouse_id))),  # 按 ID 排序的仓库列表
    }  # 响应结束


@router.post("/warehouses", status_code=status.HTTP_201_CREATED)  # POST /warehouses，新建仓库
def add_warehouse(  # 创建仓库
    payload: WarehouseCreate,  # 仓库编码与名称
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 管理员或仓管经理
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回创建结果
    return create_warehouse(db, payload, current_user.user_id, idempotency_key)  # 委托目录服务


@router.get("/locations")  # GET /locations，分页列库位
def list_locations(  # 可按仓库、库区、关键字筛选
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    warehouse_id: int | None = None,  # 按仓库过滤
    zone_code: str | None = None,  # 按库区过滤
    keyword: str | None = None,  # 模糊匹配库位/仓库编码名称
    offset: int = Query(0, ge=0),  # 分页偏移
    limit: int = Query(50, ge=1, le=200),  # 每页 1–200
):  # 返回 {total, items}
    where = []  # 动态 WHERE 条件
    if warehouse_id is not None:  # 指定仓库
        where.append(WarehouseLocation.warehouse_id == warehouse_id)  # 按仓库 ID
    if zone_code:  # 指定库区
        where.append(WarehouseLocation.zone_code == zone_code)  # 按库区编码精确匹配
    statement = select(WarehouseLocation)  # 库位数据查询
    count_statement = select(func.count()).select_from(WarehouseLocation)  # 库位计数查询
    if keyword:  # 有关键字时联仓库表做模糊匹配
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        statement = statement.join(Warehouse, Warehouse.warehouse_id == WarehouseLocation.warehouse_id)  # 数据查询联仓库
        count_statement = count_statement.join(Warehouse, Warehouse.warehouse_id == WarehouseLocation.warehouse_id)  # 计数查询同样联仓库
        where.append(  # 库位各段编码或仓库编码/名称任一匹配
            or_(  # OR 条件组
                WarehouseLocation.location_code.like(like),  # 库位编码
                WarehouseLocation.zone_code.like(like),  # 库区
                WarehouseLocation.aisle_code.like(like),  # 巷道
                WarehouseLocation.rack_code.like(like),  # 货架
                WarehouseLocation.position_code.like(like),  # 货位
                Warehouse.warehouse_code.like(like),  # 仓库编码
                Warehouse.warehouse_name.like(like),  # 仓库名称
            )  # OR 结束
        )  # 关键字条件结束
    return _page(  # 分页返回库位
        statement.where(*where).order_by(WarehouseLocation.location_id),  # 按库位 ID 排序
        count_statement.where(*where),  # 同步计数
        db,  # 会话
        offset,  # 偏移
        limit,  # 条数
    )  # 返回分页结果


@router.get("/locations/map")  # GET /locations/map，库位地图
def get_location_map(_: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):  # 返回地图用库位聚合数据
    return list_location_map(db)  # 委托目录服务


@router.post("/locations", status_code=status.HTTP_201_CREATED)  # POST /locations，新建库位
def add_location(  # 创建库位
    payload: LocationCreate,  # 库位字段
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 管理员或仓管经理
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回创建结果
    return create_location(db, payload, current_user.user_id, idempotency_key)  # 委托目录服务


@router.patch("/locations/{location_id}")  # PATCH /locations/{id}，部分更新库位
def patch_location(  # 更新库位字段
    location_id: int,  # 库位主键
    payload: LocationUpdate,  # 待更新字段
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_manager"))],  # 管理员或仓管经理
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回更新结果
    return update_location(db, location_id, payload, current_user.user_id, idempotency_key)  # 委托目录服务


@router.get("/imports")  # GET /imports，列出导入批次
def list_imports(  # 按批次号/数据集/状态关键字筛选
    _: Annotated[object, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    keyword: str | None = None,  # 可选关键字
):  # 返回 {total, items}
    where = []  # 动态 WHERE
    if keyword:  # 有关键字时模糊匹配批次字段
        like = f"%{keyword.strip()}%"  # 构造 LIKE 模式
        where.append(  # 批次号、数据集名或状态
            or_(  # OR 条件组
                DataImportBatch.batch_no.like(like),  # 批次号
                DataImportBatch.dataset_name.like(like),  # 数据集名称
                DataImportBatch.status.like(like),  # 状态
            )  # OR 结束
        )  # 关键字条件结束
    return {  # 组装列表（不分页 offset）
        "total": db.scalar(select(func.count()).select_from(DataImportBatch).where(*where)) or 0,  # 批次总数
        "items": list(db.scalars(select(DataImportBatch).where(*where).order_by(DataImportBatch.batch_id.desc()))),  # 按批次 ID 倒序
    }  # 响应结束


@router.post("/imports", status_code=status.HTTP_201_CREATED)  # POST /imports，上传商品 CSV
def upload_imports(  # 解析 CSV 并写入商品
    payload: ProductCsvImport,  # CSV 文本与文件名
    current_user: Annotated[UserAccount, Depends(require_roles("admin"))],  # 仅管理员
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,  # 可选幂等键
):  # 返回导入批次
    return import_product_csv(db, payload.content.encode("utf-8"), payload.filename, current_user.user_id, idempotency_key)  # 内容按 UTF-8 编码后交给服务


@router.get("/imports/{batch_id}", response_model=ImportBatchResponse)  # GET /imports/{id}，导入批次详情
def get_import(batch_id: int, _: Annotated[object, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):  # 按主键取导入批次
    batch = db.get(DataImportBatch, batch_id)  # 查询批次
    if batch is None:  # 不存在
        raise HTTPException(status_code=404, detail="导入批次不存在")  # 返回 404
    return batch  # ORM 转 DTO
