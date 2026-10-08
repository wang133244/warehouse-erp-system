"""低库存扫描、确认 ack、补货草稿数量。"""

from __future__ import annotations  # 启用延后求值注解，支持前向引用类型

import csv  # 导入 CSV 写入器
from io import StringIO  # 导入内存文本缓冲，用于生成 CSV 字符串

from sqlalchemy import and_, func, or_, select  # 导入组合条件、聚合与查询构造
from sqlalchemy.orm import Session  # 导入 ORM 会话类型

from backend.app.core.errors import AppError  # 导入业务异常
from backend.app.models import (  # 从 models 导入预警相关实体
    AlertAck,  # 预警确认记录
    AuditLog,  # 审计日志
    Product,  # 商品
    StockBalance,  # 库存余额
    StockLedger,  # 库存流水
    WarehouseLocation,  # 库位
)  # 结束 models 导入
from backend.app.services.user_service import account_names  # 批量解析用户名
from backend.app.services.dashboard_service import LOW_STOCK_THRESHOLD  # 默认低库存阈值
from backend.app.services.inventory_service import (  # 从库存服务导入可用量与幂等辅助
    available_units,  # 计算可用库存
    existing_idempotent_response,  # 查询已缓存的幂等响应
    record_idempotent_response,  # 写入幂等响应缓存
    require_idempotency_key,  # 校验幂等键必填
    write_audit,  # 写审计日志
)  # 结束 inventory_service 导入

AVAILABLE_EXPR = (  # 可用量表达式：实际 − 预留 − 冻结
    StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity  # 与 available_units 口径一致
)  # 结束可用量表达式
STALE_LIMIT = 50  # 呆滞库存最多展示 50 条，避免列表被无出库 SKU 淹没


def _serialize_alert(  # 把余额行序列化为预警项
    row: StockBalance,  # 库存余额
    products: dict[int, str],  # 商品 ID -> SKU
    locations: dict[int, str],  # 库位 ID -> 编码
    acked: dict,  # 已确认记录
    threshold: int,  # 低库存阈值
    alert_type: str,  # 预警类型
) -> dict:  # 前端表格行
    ack = acked.get(row.balance_id)  # 取该余额对应的确认记录（可能为空）
    created = row.updated_at or row.created_at  # 预警时间用余额最近变更
    return {  # 组装预警字典
        "balance_id": row.balance_id,  # 余额主键
        "product_id": row.product_id,  # 商品 ID
        "sku_code": products.get(row.product_id),  # 商品 SKU，缺失则为 None
        "location_id": row.location_id,  # 库位 ID
        "location_code": locations.get(row.location_id),  # 库位编码，避免前端只缓存前 200 条时显示库位#
        "quantity": row.quantity,  # 实际库存
        "reserved_quantity": row.reserved_quantity,  # 已预留数量
        "frozen_quantity": row.frozen_quantity,  # 已冻结数量
        "available_quantity": available_units(row),  # 当前可用量
        "threshold": threshold,  # 本次扫描使用的阈值
        "alert_type": alert_type,  # 预警类型：低库存或呆滞
        "status": "acked" if ack else "pending",  # 已确认或待处理
        "ack_note": ack.note if ack else None,  # 确认备注
        "created_at": created.isoformat() if created else None,  # 产生时间，ISO 供前端格式化
    }  # 结束预警序列化


def list_alerts(  # 分页列出低库存与呆滞预警
    db: Session,  # 数据库会话
    threshold: int = LOW_STOCK_THRESHOLD,  # 低库存阈值，默认沿用看板常量
    offset: int = 0,  # 分页偏移
    limit: int = 50,  # 每页条数
    keyword: str | None = None,  # 可选关键字：SKU/品名/库位
) -> dict:  # 返回阈值、总数与预警列表
    products = {row.product_id: row.sku_code for row in db.scalars(select(Product))}  # 预加载商品 ID 到 SKU 映射
    locations = {row.location_id: row.location_code for row in db.scalars(select(WarehouseLocation))}  # 预加载库位编码，表格不依赖前端 200 条缓存
    low_filter = AVAILABLE_EXPR <= threshold  # 低库存：可用量低于或等于阈值
    outbound_products = set(  # 曾经发生过出库的商品，用于排除“有流动”的库存
        db.scalars(select(StockLedger.product_id).where(StockLedger.transaction_type == "outbound").distinct())  # 只看出库流水中的商品
    )  # 结束出库商品集合
    outbound_exclude = list(outbound_products) or [-1]  # SQLAlchemy in_ 不能传空列表，用 -1 占位
    stale_filter = and_(  # 呆滞：可用量高于阈值且从未出库
        AVAILABLE_EXPR > threshold,  # 不是低库存
        StockBalance.product_id.not_in(outbound_exclude),  # 排除有出库记录的商品
    )  # 结束呆滞过滤
    if keyword:  # 有关键字则收窄商品与库位
        like = f"%{keyword.strip()}%"  # 构造模糊匹配模式
        product_ids = list(  # 按 SKU、来源码、品名匹配商品
            db.scalars(  # 取商品 ID
                select(Product.product_id).where(  # 只查主键
                    or_(Product.sku_code.like(like), Product.source_product_code.like(like), Product.product_name.like(like))  # 任一字段命中即可
                )  # 结束商品 where
            )  # 结束商品 scalars
        )  # 结束商品 ID 列表
        location_ids = list(  # 按库位编码匹配
            db.scalars(select(WarehouseLocation.location_id).where(WarehouseLocation.location_code.like(like)))  # 只取库位 ID
        )  # 结束库位 ID 列表
        extra = or_(  # 余额行命中商品或库位即可
            StockBalance.product_id.in_(product_ids or [-1]),  # 空结果用 -1 占位避免非法 IN ()
            StockBalance.location_id.in_(location_ids or [-1]),  # 同上
        )  # 结束关键字附加条件
        low_filter = and_(low_filter, extra)  # 低库存再叠加关键字
        stale_filter = and_(stale_filter, extra)  # 呆滞同样叠加关键字
    low_count = db.scalar(select(func.count()).select_from(StockBalance).where(low_filter)) or 0  # 低库存条数
    stale_total = min(  # 呆滞展示上限与实际条数取较小值
        STALE_LIMIT,  # 最多 50 条呆滞
        db.scalar(select(func.count()).select_from(StockBalance).where(stale_filter)) or 0,  # 实际呆滞条数
    )  # 结束呆滞展示总数
    total = low_count + stale_total  # 分页用的总条数：低库存 + 截断后的呆滞
    items: list[dict] = []  # 本页预警项
    remaining = limit  # 本页还需要补多少条
    current_offset = offset  # 当前还要跳过多少条

    if current_offset < low_count and remaining > 0:  # 偏移还落在低库存段且本页还有空位
        low_rows = list(  # 取出本页低库存余额
            db.scalars(  # 执行余额查询
                select(StockBalance)  # 选库存余额
                .where(low_filter)  # 套用低库存条件
                .order_by(AVAILABLE_EXPR, StockBalance.balance_id)  # 可用量升序，ID 作稳定次序
                .offset(current_offset)  # 跳过已翻过的低库存
                .limit(remaining)  # 只取本页剩余名额
            )  # 结束 scalars
        )  # 结束低库存行列表
        low_acks = {  # 预加载这些余额的确认记录
            row.balance_id: row  # 以余额 ID 为键
            for row in db.scalars(  # 查询确认表
                select(AlertAck).where(AlertAck.balance_id.in_([item.balance_id for item in low_rows] or [0]))  # 空列表用 0 占位
            )  # 结束确认查询
        }  # 结束低库存确认映射
        items.extend(_serialize_alert(row, products, locations, low_acks, threshold, "low_stock") for row in low_rows)  # 追加低库存预警
        remaining -= len(low_rows)  # 扣减已占用名额
        current_offset = 0  # 低库存段已处理完，呆滞段从 0 开始
    else:  # 偏移越过全部低库存
        current_offset -= low_count  # 把剩余偏移换算到呆滞段

    if remaining > 0 and current_offset < stale_total:  # 还有名额且偏移仍在呆滞窗口内
        stale_rows = list(  # 取出本页呆滞余额
            db.scalars(  # 执行余额查询
                select(StockBalance)  # 选库存余额
                .where(stale_filter)  # 套用呆滞条件
                .order_by(StockBalance.quantity.desc(), StockBalance.balance_id)  # 存量高的呆滞优先
                .offset(current_offset)  # 跳过已翻过的呆滞
                .limit(min(remaining, stale_total - current_offset))  # 不超过剩余名额和呆滞窗口
            )  # 结束 scalars
        )  # 结束呆滞行列表
        stale_acks = {  # 预加载这些余额的确认记录
            row.balance_id: row  # 以余额 ID 为键
            for row in db.scalars(  # 查询确认表
                select(AlertAck).where(AlertAck.balance_id.in_([item.balance_id for item in stale_rows] or [0]))  # 空列表用 0 占位
            )  # 结束确认查询
        }  # 结束呆滞确认映射
        items.extend(_serialize_alert(row, products, locations, stale_acks, threshold, "stale_stock") for row in stale_rows)  # 追加呆滞预警

    return {  # 组装分页响应
        "threshold": threshold,  # 本次阈值
        "total": total,  # 可分页总条数
        "offset": offset,  # 回显偏移
        "limit": limit,  # 回显每页大小
        "items": items,  # 本页预警
    }  # 结束列表响应


def ack_alert(db: Session, balance_id: int, user_id: int, key: str, note: str | None) -> dict:  # 确认一条库存预警
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, user_id, key)  # 查是否已确认过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    balance = db.get(StockBalance, balance_id)  # 按主键读取余额
    if balance is None:  # 余额不存在
        raise AppError("NOT_FOUND", "库存记录不存在", 404)  # 无法确认不存在的库存
    existing = db.scalar(select(AlertAck).where(AlertAck.balance_id == balance_id))  # 查是否已有确认行
    if existing is None:  # 首次确认
        existing = AlertAck(  # 新建确认记录
            balance_id=balance_id,  # 关联余额
            product_id=balance.product_id,  # 冗余商品，便于事后追溯
            location_id=balance.location_id,  # 冗余库位
            acked_by=user_id,  # 确认人
            note=note,  # 确认备注
        )  # 结束确认实体构造
        db.add(existing)  # 加入会话
    else:  # 重复确认则覆盖备注
        existing.note = note  # 更新确认备注
    body = {"balance_id": balance_id, "status": "acked", "note": note}  # 确认成功响应
    record_idempotent_response(db, user_id=user_id, key=key, path=f"/api/v1/alerts/{balance_id}/ack", body=body)  # 缓存确认响应
    write_audit(db, user_id=user_id, action="alert_ack", entity_type="stock_balance", entity_id=balance_id, after=body)  # 写确认审计
    db.commit()  # 提交事务
    return body  # 返回确认结果


def inventory_csv(db: Session) -> str:  # 导出库存 CSV 文本
    buffer = StringIO()  # 内存缓冲，避免落临时文件
    writer = csv.writer(buffer)  # CSV 写入器
    writer.writerow(  # 写表头
        [  # 列顺序与前端导入约定一致
            "sku_code",  # SKU
            "product_name",  # 品名
            "location_code",  # 库位编码
            "quantity",  # 实际库存
            "reserved_quantity",  # 预留
            "frozen_quantity",  # 冻结
            "available_quantity",  # 可用
        ]  # 结束表头列
    )  # 结束表头写入
    rows = db.execute(  # 联表查出商品、库位与余额
        select(Product, WarehouseLocation, StockBalance)  # 三表同行返回
        .join(StockBalance, StockBalance.product_id == Product.product_id)  # 商品关联余额
        .join(WarehouseLocation, WarehouseLocation.location_id == StockBalance.location_id)  # 余额关联库位
        .order_by(Product.sku_code, WarehouseLocation.location_code)  # 按 SKU、库位排序
    )  # 结束联表查询
    for product, location, balance in rows:  # 逐行写出
        writer.writerow(  # 写一条库存记录
            [  # 与表头一一对应
                product.sku_code,  # SKU
                product.product_name,  # 品名
                location.location_code,  # 库位
                balance.quantity,  # 实际
                balance.reserved_quantity,  # 预留
                balance.frozen_quantity,  # 冻结
                available_units(balance),  # 可用
            ]  # 结束行字段
        )  # 结束一行写入
    return buffer.getvalue()  # 返回完整 CSV 文本


def ledger_csv(db: Session, limit: int = 500) -> str:  # 导出最近库存流水 CSV
    buffer = StringIO()  # 内存缓冲
    writer = csv.writer(buffer)  # CSV 写入器
    writer.writerow(  # 写表头
        ["ledger_id", "product_id", "location_id", "transaction_type", "quantity_delta", "before_quantity", "after_quantity", "created_at"]  # 流水关键字段
    )  # 结束表头写入
    rows = list(db.scalars(select(StockLedger).order_by(StockLedger.ledger_id.desc()).limit(limit)))  # 取最近 limit 条流水
    for row in rows:  # 逐条写出
        writer.writerow(  # 写一条流水
            [  # 与表头一一对应
                row.ledger_id,  # 流水主键
                row.product_id,  # 商品
                row.location_id,  # 库位
                row.transaction_type,  # 事务类型
                row.quantity_delta,  # 数量变化
                row.before_quantity,  # 过账前数量
                row.after_quantity,  # 过账后数量
                row.created_at,  # 过账时间
            ]  # 结束行字段
        )  # 结束一行写入
    return buffer.getvalue()  # 返回完整 CSV 文本


def audit_csv(db: Session, limit: int = 500) -> str:  # 导出最近审计日志 CSV
    buffer = StringIO()  # 内存缓冲
    writer = csv.writer(buffer)  # CSV 写入器
    writer.writerow(["audit_log_id", "username", "action", "entity_type", "entity_id", "created_at"])  # 审计关键字段
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.audit_log_id.desc()).limit(limit)))  # 取最近 limit 条审计
    names = account_names(db, {row.user_id for row in rows if row.user_id})  # 批量解析操作者用户名
    for row in rows:  # 逐条写出
        writer.writerow(  # 写一条审计
            [  # 与表头一一对应
                row.audit_log_id,  # 审计主键
                names.get(row.user_id) if row.user_id else "",  # 有用户则填用户名，系统动作留空
                row.action,  # 动作
                row.entity_type,  # 实体类型
                row.entity_id,  # 实体 ID
                row.created_at,  # 发生时间
            ]  # 结束行字段
        )  # 结束一行写入
    return buffer.getvalue()  # 返回完整 CSV 文本
