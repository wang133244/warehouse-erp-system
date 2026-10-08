"""看板汇总与 7 日图；LOW_STOCK_THRESHOLD 为低库存阈值。"""

from __future__ import annotations  # 启用延后求值类型注解

from collections import defaultdict  # 按日累加收发单量与数量
from datetime import UTC, datetime, timedelta  # 图表窗口按 UTC 切日

from sqlalchemy import func, select  # 聚合余额与单据，只读不改库存
from sqlalchemy.orm import Session  # 只读会话

from backend.app.core.cache import (  # 看板结果短缓存，减少扫库存
    DASHBOARD_CHARTS_KEY,  # 图表缓存键前缀
    DASHBOARD_SUMMARY_KEY,  # 汇总缓存键
    DASHBOARD_TTL_SECONDS,  # 缓存秒数
    cache_get_json,  # 读缓存
    cache_set_json,  # 写缓存；库存过账时会失效
)  # 结束看板缓存导入
from backend.app.models import (  # 看板只读这些表，不调用写库存服务
    AlertAck,  # 已确认预警，从低库存条数中剔除
    ApprovalTask,  # 待审批计数
    InboundItem,  # 入库数量（图表）
    InboundOrder,  # 待收货草稿单
    OutboundItem,  # 出库数量（图表）
    OutboundOrder,  # 待出库/待复核
    StockBalance,  # 实际/预留/冻结合计
    Warehouse,  # 分仓存量
    WarehouseLocation,  # 库位归属仓库
)  # 结束模型导入：看板只读聚合，不改库存


LOW_STOCK_THRESHOLD = 10  # 可用量 <= 10 视为低库存预警


def dashboard_summary(db: Session) -> dict:  # 看板汇总：优先读缓存，未命中再算
    cached = cache_get_json(DASHBOARD_SUMMARY_KEY)  # 取汇总缓存
    if cached is not None:  # 缓存有效则不扫库
        return cached  # 直接返回，仍是只读快照
    data = _compute_dashboard_summary(db)  # 实时聚合库存与待办
    cache_set_json(DASHBOARD_SUMMARY_KEY, data, DASHBOARD_TTL_SECONDS)  # 写入短缓存
    return data  # 只读结果，不改库存


def _compute_dashboard_summary(db: Session) -> dict:  # 实际计算看板数字，全程 SELECT
    total, reserved, frozen = db.execute(  # 一次查出全仓实际、预留、冻结合计
        select(  # 三列聚合
            func.coalesce(func.sum(StockBalance.quantity), 0),  # 实际库存总量
            func.coalesce(func.sum(StockBalance.reserved_quantity), 0),  # 出库预留总量
            func.coalesce(func.sum(StockBalance.frozen_quantity), 0),  # 盘点等冻结总量
        )  # 结束 select
    ).one()  # 恰好一行合计
    inbound_draft = db.scalar(select(func.count()).select_from(InboundOrder).where(InboundOrder.status == "draft")) or 0  # 待收货草稿单数
    pending_review = (  # 已拣待复核出库单
        db.scalar(select(func.count()).select_from(OutboundOrder).where(OutboundOrder.status == "picked")) or 0  # picked 态计数
    )  # 待复核
    outbound_pending = (  # 尚未完成的出库单（含草稿到已复核）
        db.scalar(  # 计数
            select(func.count())  # COUNT(*)
            .select_from(OutboundOrder)  # 出库单
            .where(OutboundOrder.status.in_(("draft", "allocated", "picked", "reviewed")))  # 未 completed 的在途状态
        )  # 结束查询
        or 0  # 空则 0
    )  # 待出库合计
    pending_approvals = (  # 待审批任务数
        db.scalar(select(func.count()).select_from(ApprovalTask).where(ApprovalTask.status == "pending")) or 0  # pending 计数
    )  # 待审批
    low_stock = list(  # 可用量低于阈值的余额行
        db.scalars(select(StockBalance).where(  # 可用 = 实际 − 预留 − 冻结
            StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity <= LOW_STOCK_THRESHOLD  # 阈值 10
        ))  # 结束 where
    )  # 物化低库存行
    acked = set(db.scalars(select(AlertAck.balance_id)))  # 已确认预警的余额 ID
    return {  # 看板卡片数字
        "stock_quantity": int(total),  # 实际总量
        "reserved_quantity": int(reserved),  # 预留总量
        "frozen_quantity": int(frozen),  # 冻结总量
        "available_quantity": int(total) - int(reserved) - int(frozen),  # 可用 = 实际 − 预留 − 冻结
        "inbound_draft": inbound_draft,  # 入库草稿
        "outbound_pending": outbound_pending,  # 在途出库
        "pending_receiving": inbound_draft,  # 待收货与草稿同义
        "pending_review": pending_review,  # 待复核
        "pending_approvals": pending_approvals,  # 待审批
        "low_stock_alerts": sum(1 for row in low_stock if row.balance_id not in acked),  # 未确认的低库存条数
    }  # 只读返回


def _day_key(value: datetime | None) -> str | None:  # 单据时间归到 UTC 日期
    if value is None:  # 无时间无法入图
        return None  # 调用方跳过
    if value.tzinfo is not None:  # 带时区先转 UTC
        value = value.astimezone(UTC).replace(tzinfo=None)  # 去掉时区
    return value.date().isoformat()  # YYYY-MM-DD


def dashboard_charts(db: Session, days: int = 7) -> dict:  # 7 日图：缓存键含天数
    cache_key = f"{DASHBOARD_CHARTS_KEY}:{days}"  # 不同天数分开缓存
    cached = cache_get_json(cache_key)  # 读图表缓存
    if cached is not None:  # 命中则不扫单
        return cached  # 只读快照
    data = _compute_dashboard_charts(db, days)  # 实时聚合
    cache_set_json(cache_key, data, DASHBOARD_TTL_SECONDS)  # 写入短缓存
    return data  # 不改库存


def _compute_dashboard_charts(db: Session, days: int = 7) -> dict:  # 计算分日收发、分仓库存、低库存 Top
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days - 1)  # 含今天共 days 天
    inbound_qty = defaultdict(int)  # 日入库数量
    inbound_count = defaultdict(int)  # 日入库单数
    for order, quantity in db.execute(  # 按入库单分组求明细合计
        select(InboundOrder.created_at, func.coalesce(func.sum(InboundItem.quantity), 0))  # 创建日与数量
        .join(InboundItem, InboundItem.inbound_order_id == InboundOrder.inbound_order_id)  # 关联明细
        .where(InboundOrder.created_at >= cutoff)  # 窗口内单据
        .group_by(InboundOrder.inbound_order_id, InboundOrder.created_at)  # 一单一行
    ):  # 结束入库查询
        key = _day_key(order)  # 归日
        if key:  # 有日期才入图
            inbound_count[key] += 1  # 当天单数 +1
            inbound_qty[key] += int(quantity)  # 当天数量累加

    outbound_qty = defaultdict(int)  # 日出库数量
    outbound_count = defaultdict(int)  # 日出库单数
    for created_at, quantity in db.execute(  # 按出库单分组
        select(OutboundOrder.created_at, func.coalesce(func.sum(OutboundItem.quantity), 0))  # 创建日与需求数量
        .join(OutboundItem, OutboundItem.outbound_order_id == OutboundOrder.outbound_order_id)  # 关联明细
        .where(OutboundOrder.created_at >= cutoff)  # 窗口内
        .group_by(OutboundOrder.outbound_order_id, OutboundOrder.created_at)  # 一单一行
    ):  # 结束出库查询
        key = _day_key(created_at)  # 归日
        if key:  # 有日期
            outbound_count[key] += 1  # 当天单数
            outbound_qty[key] += int(quantity)  # 当天数量

    series = []  # 连续日期轴，保证无单日也出 0
    for offset in range(days):  # 从最早一天到今天
        day = (datetime.now(UTC).date() - timedelta(days=days - 1 - offset)).isoformat()  # 该格日期
        series.append(day)  # 加入横轴

    stock_rows = list(  # 分仓实际库存合计（只读）
        db.execute(  # 仓 → 库位 → 余额
            select(  # 仓库维度
                Warehouse.warehouse_id,  # 仓 ID
                Warehouse.warehouse_code,  # 仓编码
                Warehouse.warehouse_name,  # 仓名
                func.coalesce(func.sum(StockBalance.quantity), 0),  # 该仓实际库存
            )  # 结束列
            .select_from(Warehouse)  # 从仓库表出发
            .join(WarehouseLocation, WarehouseLocation.warehouse_id == Warehouse.warehouse_id)  # 库位
            .join(StockBalance, StockBalance.location_id == WarehouseLocation.location_id)  # 余额
            .group_by(Warehouse.warehouse_id, Warehouse.warehouse_code, Warehouse.warehouse_name)  # 按仓分组
        )  # 结束执行
    )  # 物化分仓行
    low_stock = list(  # 可用量最低的若干余额，供图表告警点
        db.execute(  # 只读
            select(  # 余额与可用量
                StockBalance.balance_id,  # 余额 ID
                StockBalance.product_id,  # 商品
                StockBalance.location_id,  # 库位
                StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity,  # 可用量
            )  # 结束列
            .where(  # 低于阈值
                StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity  # 可用
                <= LOW_STOCK_THRESHOLD  # <= 10
            )  # 结束 where
            .order_by(StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity)  # 最紧缺在前
            .limit(8)  # 图表只展示 8 条
        )  # 结束查询
    )  # 物化
    return {  # 图表 JSON
        "inbound_by_day": [  # 分日入库
            {"date": day, "count": inbound_count[day], "quantity": inbound_qty[day]} for day in series  # 无单则为 0
        ],  # 结束入库序列
        "outbound_by_day": [  # 分日出库
            {"date": day, "count": outbound_count[day], "quantity": outbound_qty[day]} for day in series  # 无单则为 0
        ],  # 结束出库序列
        "stock_by_warehouse": [  # 分仓库存
            {  # 一仓
                "warehouse_id": warehouse_id,  # ID
                "warehouse_code": warehouse_code,  # 编码
                "warehouse_name": warehouse_name,  # 名称
                "quantity": int(quantity),  # 实际库存
            }  # 结束一仓
            for warehouse_id, warehouse_code, warehouse_name, quantity in stock_rows  # 解包查询行
        ],  # 结束分仓
        "low_stock": [  # 低库存点
            {  # 一条
                "balance_id": balance_id,  # 余额
                "product_id": product_id,  # 商品
                "location_id": location_id,  # 库位
                "available_quantity": int(available),  # 可用量（只读）
            }  # 结束一条
            for balance_id, product_id, location_id, available in low_stock  # 解包
        ],  # 结束低库存
    }  # 只读图表数据
