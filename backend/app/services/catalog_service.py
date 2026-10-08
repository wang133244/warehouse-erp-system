"""商品/仓/位查询创建与 CSV 导入。"""

from __future__ import annotations  # 启用延后求值注解，支持前向引用类型

import csv  # 导入 CSV 读取器
import io  # 导入内存 IO，把字节流转成文本流
from datetime import UTC, datetime  # 导入 UTC 时间，用于生成导入批次号

from sqlalchemy import func, select  # 导入聚合与查询构造
from sqlalchemy.orm import Session  # 导入 ORM 会话类型

from backend.app.core.errors import AppError  # 导入业务异常
from backend.app.models import DataImportBatch, Product, Warehouse, WarehouseLocation  # 导入主数据与导入批次模型
from backend.app.schemas.followup import LocationCreate, LocationUpdate, ProductCreate, ProductUpdate, WarehouseCreate  # 导入仓/位/商品入参
from backend.app.services.inventory_service import (  # 从库存服务导入幂等与审计辅助
    existing_idempotent_response,  # 查询已缓存的幂等响应
    record_idempotent_response,  # 写入幂等响应缓存
    require_idempotency_key,  # 校验幂等键必填
    write_audit,  # 写审计日志
)  # 结束 inventory_service 导入


def serialize_product(product: Product) -> dict:  # 把商品实体序列化为接口字典
    return {  # 组装商品详情
        "product_id": product.product_id,  # 商品主键
        "sku_code": product.sku_code,  # 系统 SKU
        "source_product_code": product.source_product_code,  # 来源商品编码
        "brand": product.brand,  # 品牌
        "product_name": product.product_name,  # 品名
        "category": product.category,  # 品类
        "size": product.size,  # 规格尺寸
        "function_feature": product.function_feature,  # 功能特征
        "color": product.color,  # 颜色
        "pallet_spec": product.pallet_spec,  # 托盘规格单位
        "pallet_capacity": product.pallet_capacity,  # 托盘容量
        "is_active": bool(product.is_active),  # 是否启用，统一转布尔
    }  # 结束商品序列化


def list_location_map(db: Session) -> dict:  # 按仓库+库区汇总库位地图
    grouped = db.execute(  # 按仓、区聚合库位数量
        select(  # 选出分组键与计数
            WarehouseLocation.warehouse_id,  # 仓库 ID
            Warehouse.warehouse_code,  # 仓库编码
            WarehouseLocation.zone_code,  # 库区编码
            func.count(WarehouseLocation.location_id),  # 该区库位数
        )  # 结束 select 列
        .join(Warehouse, Warehouse.warehouse_id == WarehouseLocation.warehouse_id)  # 连接仓库拿编码
        .group_by(WarehouseLocation.warehouse_id, Warehouse.warehouse_code, WarehouseLocation.zone_code)  # 按仓+区分组
        .order_by(Warehouse.warehouse_code, WarehouseLocation.zone_code)  # 按仓码、区码排序
    ).all()  # 取出全部分组行
    items = []  # 地图条目
    total = 0  # 库位总数
    for warehouse_id, warehouse_code, zone_code, location_count in grouped:  # 逐区补充库位编码列表
        codes = list(  # 该区全部库位编码
            db.scalars(  # 取编码标量
                select(WarehouseLocation.location_code)  # 只要编码
                .where(  # 限定同一仓同一区
                    WarehouseLocation.warehouse_id == warehouse_id,  # 同仓库
                    WarehouseLocation.zone_code == zone_code,  # 同库区
                )  # 结束 where
                .order_by(WarehouseLocation.location_code)  # 编码升序，便于地图展示
            )  # 结束 scalars
        )  # 结束编码列表
        total += int(location_count)  # 累计库位数
        items.append(  # 追加一个仓+区条目
            {  # 区级地图节点
                "warehouse_id": warehouse_id,  # 仓库 ID
                "warehouse_code": warehouse_code,  # 仓库编码
                "zone_code": zone_code,  # 库区编码
                "location_count": int(location_count),  # 该区库位数
                "location_codes": codes,  # 该区库位编码列表
            }  # 结束区级节点
        )  # 结束 append
    return {"total": total, "items": items}  # 返回总数与分区地图


def serialize_location(location: WarehouseLocation) -> dict:  # 把库位实体序列化为接口字典
    return {  # 组装库位详情
        "location_id": location.location_id,  # 库位主键
        "warehouse_id": location.warehouse_id,  # 所属仓库
        "location_code": location.location_code,  # 库位编码
        "zone_code": location.zone_code,  # 库区
        "aisle_code": location.aisle_code,  # 巷道
        "rack_code": location.rack_code,  # 货架
        "position_code": location.position_code,  # 货位
        "is_active": bool(location.is_active),  # 是否启用
    }  # 结束库位序列化


def serialize_warehouse(warehouse: Warehouse) -> dict:  # 把仓库实体序列化为接口字典
    return {  # 组装仓库详情
        "warehouse_id": warehouse.warehouse_id,  # 仓库主键
        "warehouse_code": warehouse.warehouse_code,  # 仓库编码
        "warehouse_name": warehouse.warehouse_name,  # 仓库名称
    }  # 结束仓库序列化


def serialize_import_batch(batch: DataImportBatch) -> dict:  # 把导入批次序列化为接口字典
    return {  # 组装导入结果
        "batch_id": batch.batch_id,  # 批次主键
        "batch_no": batch.batch_no,  # 批次号
        "dataset_name": batch.dataset_name,  # 数据集/文件名
        "dataset_version": batch.dataset_version,  # 数据版本
        "imported_at": batch.imported_at.isoformat() if batch.imported_at else None,  # 导入时间转 ISO
        "total_rows": batch.total_rows,  # 总行数
        "valid_rows": batch.valid_rows,  # 有效行数
        "invalid_rows": batch.invalid_rows,  # 无效行数
        "status": batch.status,  # 导入状态
        "notes": batch.notes,  # 失败摘要
    }  # 结束批次序列化


def require_usable_product(db: Session, product_id: int) -> Product:  # 要求商品存在且启用
    product = db.get(Product, product_id)  # 按主键读取商品
    if product is None:  # 商品不存在
        raise AppError("PRODUCT_NOT_FOUND", "商品不存在", 404, {"product_id": product_id})  # 返回 404
    if not product.is_active:  # 商品已禁用
        raise AppError("PRODUCT_INACTIVE", "商品已禁用", 409, {"product_id": product_id})  # 禁用商品不可用于作业
    return product  # 返回可用商品


def require_usable_location(db: Session, location_id: int) -> WarehouseLocation:  # 要求库位存在且启用
    location = db.get(WarehouseLocation, location_id)  # 按主键读取库位
    if location is None:  # 库位不存在
        raise AppError("WAREHOUSE_LOCATION_NOT_FOUND", "库位不存在", 404, {"location_id": location_id})  # 返回 404
    if not location.is_active:  # 库位已禁用
        raise AppError("LOCATION_INACTIVE", "库位已禁用", 409, {"location_id": location_id})  # 禁用库位不可收发货
    return location  # 返回可用库位


def create_product(db: Session, payload: ProductCreate, user_id: int, key: str) -> dict:  # 创建商品主数据
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已创建过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    if db.scalar(select(Product).where(Product.sku_code == payload.sku_code)):  # SKU 已存在
        raise AppError("SKU_EXISTS", "系统 SKU 已存在", 409)  # 拒绝重复 SKU
    product = Product(**payload.model_dump())  # 按入参构造商品
    db.add(product)  # 加入会话
    db.flush()  # 刷盘拿到 product_id
    body = serialize_product(product)  # 序列化创建结果
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/products", body=body, status=201)  # 缓存创建响应
    write_audit(db, user_id=user_id, action="product_create", entity_type="product", entity_id=product.product_id, after=body)  # 写创建审计
    db.commit()  # 提交事务
    return body  # 返回创建结果


def update_product(db: Session, product_id: int, payload: ProductUpdate, user_id: int, key: str) -> dict:  # 部分更新商品
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已更新过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    product = db.get(Product, product_id)  # 按主键读取商品
    if product is None:  # 商品不存在
        raise AppError("PRODUCT_NOT_FOUND", "商品不存在", 404)  # 返回 404
    before = serialize_product(product)  # 更新前快照，供审计对比
    changes = payload.model_dump(exclude_unset=True)  # 只取客户端显式传入的字段
    if not changes:  # 没有任何字段
        raise AppError("NO_CHANGES", "没有需要更新的字段", 400)  # 拒绝空更新
    for field, value in changes.items():  # 逐字段覆盖
        setattr(product, field, value)  # 动态设置属性，保持部分更新语义
    db.flush()  # 刷盘变更
    body = serialize_product(product)  # 序列化更新结果
    record_idempotent_response(  # 缓存更新响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="PATCH",  # 更新方法
        path=f"/api/v1/products/{product_id}",  # 更新路径
        body=body,  # 响应体
    )  # 结束幂等缓存
    write_audit(  # 写更新审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="product_update",  # 审计动作
        entity_type="product",  # 实体类型
        entity_id=product_id,  # 商品 ID
        before=before,  # 更新前
        after=body,  # 更新后
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回更新结果


def create_location(db: Session, payload: LocationCreate, user_id: int, key: str) -> dict:  # 创建库位
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已创建过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    if db.get(Warehouse, payload.warehouse_id) is None:  # 所属仓库不存在
        raise AppError("WAREHOUSE_NOT_FOUND", "仓库不存在", 400)  # 不能挂到空仓库
    if db.scalar(select(WarehouseLocation).where(WarehouseLocation.location_code == payload.location_code)):  # 库位编码重复
        raise AppError("LOCATION_EXISTS", "库位编码已存在", 409)  # 编码全局唯一
    location = WarehouseLocation(**payload.model_dump())  # 按入参构造库位
    db.add(location)  # 加入会话
    db.flush()  # 刷盘拿到 location_id
    body = serialize_location(location)  # 序列化创建结果
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/locations", body=body, status=201)  # 缓存创建响应
    write_audit(  # 写创建审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="location_create",  # 审计动作
        entity_type="warehouse_location",  # 实体类型
        entity_id=location.location_id,  # 新库位 ID
        after=body,  # 创建后快照
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回创建结果


def update_location(db: Session, location_id: int, payload: LocationUpdate, user_id: int, key: str) -> dict:  # 部分更新库位
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已更新过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    location = db.get(WarehouseLocation, location_id)  # 按主键读取库位
    if location is None:  # 库位不存在
        raise AppError("WAREHOUSE_LOCATION_NOT_FOUND", "库位不存在", 404)  # 返回 404
    before = serialize_location(location)  # 更新前快照
    changes = payload.model_dump(exclude_unset=True)  # 只取显式传入字段
    if not changes:  # 没有任何字段
        raise AppError("NO_CHANGES", "没有需要更新的字段", 400)  # 拒绝空更新
    for field, value in changes.items():  # 逐字段覆盖
        setattr(location, field, value)  # 动态设置属性
    db.flush()  # 刷盘变更
    body = serialize_location(location)  # 序列化更新结果
    record_idempotent_response(  # 缓存更新响应
        db,  # 当前会话
        user_id=user_id,  # 操作者
        key=key,  # 幂等键
        method="PATCH",  # 更新方法
        path=f"/api/v1/locations/{location_id}",  # 更新路径
        body=body,  # 响应体
    )  # 结束幂等缓存
    write_audit(  # 写更新审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="location_update",  # 审计动作
        entity_type="warehouse_location",  # 实体类型
        entity_id=location_id,  # 库位 ID
        before=before,  # 更新前
        after=body,  # 更新后
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回更新结果


def create_warehouse(db: Session, payload: WarehouseCreate, user_id: int, key: str) -> dict:  # 创建仓库
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已创建过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    if db.scalar(select(Warehouse).where(Warehouse.warehouse_code == payload.warehouse_code.strip())):  # 仓库编码重复
        raise AppError("WAREHOUSE_EXISTS", "仓库编码已存在", 409)  # 编码必须唯一
    warehouse = Warehouse(warehouse_code=payload.warehouse_code.strip(), warehouse_name=payload.warehouse_name.strip())  # 去掉首尾空白后入库
    db.add(warehouse)  # 加入会话
    db.flush()  # 刷盘拿到 warehouse_id
    body = serialize_warehouse(warehouse)  # 序列化创建结果
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/warehouses", body=body, status=201)  # 缓存创建响应
    write_audit(  # 写创建审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="warehouse_create",  # 审计动作
        entity_type="warehouse",  # 实体类型
        entity_id=warehouse.warehouse_id,  # 新仓库 ID
        after=body,  # 创建后快照
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回创建结果


def import_product_csv(db: Session, raw: bytes, filename: str | None, user_id: int, key: str) -> dict:  # 从 CSV 批量导入商品
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已导入过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    try:  # 尝试按 UTF-8（含 BOM）解码
        text = raw.decode("utf-8-sig")  # utf-8-sig 可去掉 Excel 导出的 BOM
    except UnicodeDecodeError as exc:  # 非 UTF-8 编码
        raise AppError("IMPORT_ENCODING", "仅支持 UTF-8 编码的 CSV", 422) from exc  # 明确编码要求
    reader = csv.DictReader(io.StringIO(text))  # 按表头把每行读成字典
    if not reader.fieldnames:  # 没有表头
        raise AppError("IMPORT_EMPTY", "CSV 没有表头", 422)  # 无法识别列
    valid = 0  # 成功导入行数
    invalid = 0  # 跳过/失败行数
    notes: list[str] = []  # 失败原因摘要
    for row in reader:  # 逐行处理
        sku = (row.get("sku_code") or "").strip()  # 系统 SKU，去空白
        source = (row.get("source_product_code") or sku).strip()  # 来源码缺省用 SKU
        name = (row.get("product_name") or "").strip()  # 品名
        if not sku or not name:  # SKU 或品名为空视为无效行
            invalid += 1  # 计入无效
            continue  # 跳过该行
        if db.scalar(select(Product).where(Product.sku_code == sku)):  # SKU 已存在
            invalid += 1  # 计入无效
            notes.append(f"{sku} 已存在")  # 记录冲突原因
            continue  # 不覆盖已有商品
        try:  # 解析托盘容量
            capacity = int(row.get("pallet_capacity") or 10)  # 缺省 10
        except (TypeError, ValueError):  # 非数字则回退默认
            capacity = 10  # 非法容量按 10 处理
        db.add(  # 新增商品
            Product(  # 按 CSV 列填充，缺省给业务默认值
                sku_code=sku,  # 系统 SKU
                source_product_code=source or sku,  # 来源码仍空则再用 SKU
                brand=(row.get("brand") or "未填写").strip() or "未填写",  # 品牌缺省
                product_name=name,  # 品名
                category=(row.get("category") or "通用").strip() or "通用",  # 品类缺省
                size=(row.get("size") or "标准").strip() or "标准",  # 尺寸缺省
                function_feature=(row.get("function_feature") or "普通").strip() or "普通",  # 功能缺省
                color=(row.get("color") or "默认").strip() or "默认",  # 颜色缺省
                pallet_spec=(row.get("pallet_spec") or "箱").strip() or "箱",  # 单位缺省
                pallet_capacity=max(capacity, 1),  # 容量至少为 1
            )  # 结束商品构造
        )  # 结束 add
        db.flush()  # 逐行刷盘，便于后续行检测到刚插入的 SKU
        valid += 1  # 计入有效
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")  # 批次时间戳
    batch = DataImportBatch(  # 记录本次导入批次
        batch_no=f"CSV-{stamp}-{user_id}",  # 批次号含时间与操作者
        dataset_name=(filename or "products.csv")[:128],  # 文件名截断到字段长度
        dataset_version="csv",  # 来源类型
        total_rows=valid + invalid,  # 总处理行数
        valid_rows=valid,  # 成功行
        invalid_rows=invalid,  # 失败行
        status="imported" if valid else "failed",  # 至少一行成功才算导入成功
        notes="; ".join(notes[:8]) or None,  # 最多保留 8 条失败摘要
    )  # 结束批次构造
    db.add(batch)  # 加入会话
    db.flush()  # 刷盘拿到 batch_id
    body = serialize_import_batch(batch)  # 序列化导入结果
    record_idempotent_response(db, user_id=user_id, key=key, path="/api/v1/imports", body=body, status=201)  # 缓存导入响应
    write_audit(  # 写导入审计
        db,  # 当前会话
        user_id=user_id,  # 操作者
        action="import_csv",  # 审计动作
        entity_type="data_import_batch",  # 实体类型
        entity_id=batch.batch_id,  # 批次 ID
        after=body,  # 导入后快照
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回导入结果
