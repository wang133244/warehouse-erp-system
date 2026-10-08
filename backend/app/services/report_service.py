"""只读报表：ABC（出库量否则现存量）、周转、日报周报、拣货效率。"""

from __future__ import annotations  # 启用延后求值类型注解

from collections import defaultdict  # 按日累加入库/出库量
from datetime import UTC, datetime, timedelta  # 报表时间窗口按 UTC 计算

from sqlalchemy import func, select  # 聚合流水与余额，只读不改库存
from sqlalchemy.orm import Session  # 只读会话

from backend.app.models import PickingTask, Product, StockBalance, StockLedger  # 报表数据源：商品、余额、流水、拣货


def elapsed_seconds(start: datetime | None, end: datetime | None) -> float | None:  # 计算拣货确认耗时秒数
    if start is None or end is None:  # 缺时间无法算效率
        return None  # 该任务不计入平均耗时
    start_naive = start.astimezone(UTC).replace(tzinfo=None) if start.tzinfo is not None else start  # 统一成无时区 UTC
    end_naive = end.astimezone(UTC).replace(tzinfo=None) if end.tzinfo is not None else end  # 结束时间同样规范化
    seconds = (end_naive - start_naive).total_seconds()  # 得到秒差
    return max(0.0, seconds)  # 负间隔按 0，避免脏数据拉低效率


def _product_maps(db: Session, days: int | None = None) -> tuple[dict[int, Product], dict[int, int], dict[int, int]]:  # 只读：商品、出库量、现存量三张映射
    products = {row.product_id: row for row in db.scalars(select(Product))}  # 全量商品，报表展示 SKU/品名
    outbound_stmt = select(StockLedger.product_id, func.coalesce(func.sum(-StockLedger.quantity_delta), 0)).where(  # 出库流水数量为负，取相反数得出发货量
        StockLedger.transaction_type == "outbound"  # 只统计出库过账，不含预留
    )  # 结束出库条件
    if days:  # 限定统计窗口时过滤流水时间
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)  # 窗口起点（无时区便于与库中时间比较）
        outbound_stmt = outbound_stmt.where(StockLedger.created_at >= cutoff)  # 只算窗口内出库
    outbound_map = {  # 商品 ID → 出库数量
        product_id: int(quantity)  # 转整数
        for product_id, quantity in db.execute(outbound_stmt.group_by(StockLedger.product_id))  # 按商品汇总出库
    }  # 结束出库映射
    stock_map = {  # 商品 ID → 当前实际库存合计（跨库位）
        product_id: int(quantity)  # 转整数
        for product_id, quantity in db.execute(  # 只读合计余额，不锁行
            select(StockBalance.product_id, func.coalesce(func.sum(StockBalance.quantity), 0)).group_by(  # 按商品加总实际数量
                StockBalance.product_id  # 分组键
            )  # 结束 group_by
        )  # 结束执行
    }  # 结束存量映射
    return products, outbound_map, stock_map  # 供 ABC/周转排序使用，全程只读


def _ranked_product_ids(products: dict[int, Product], outbound_map: dict[int, int], stock_map: dict[int, int]) -> list[int]:  # 有出库按出库量排，否则按现存量
    ids = set(products) | set(outbound_map) | set(stock_map)  # 并集：避免漏掉无主数据但有流水的商品
    use_outbound = any(outbound_map.values())  # 只要有过出库就用出库量作为排序依据
    scores = {product_id: outbound_map.get(product_id, 0) if use_outbound else stock_map.get(product_id, 0) for product_id in ids}  # 每个商品的排序分
    return [product_id for product_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]  # 分高在前，同分按 ID 稳定排序


def abc_report(db: Session, days: int | None = None) -> dict:  # 只读 ABC 分类，不改库存
    # 有出库按出库量排序，否则按现存量。累计份额 <80% 为 A，<95% 为 B，其余 C。
    products, outbound_map, stock_map = _product_maps(db, days)  # 取只读映射
    ranked = _ranked_product_ids(products, outbound_map, stock_map)  # 得到排序后的商品 ID
    use_outbound = any(outbound_map.values())  # 与排序同一依据，写入 basis 字段
    scores = {  # 每个上榜商品的分值
        product_id: outbound_map.get(product_id, 0) if use_outbound else stock_map.get(product_id, 0) for product_id in ranked  # 按依据取值
    }  # 结束分值表
    positive = [product_id for product_id in ranked if scores.get(product_id, 0) > 0]  # 去掉零分商品，避免把无业务 SKU 算进 ABC
    if positive:  # 有正分才收窄名单
        ranked = positive  # 只用有贡献的商品做累计份额
    total = sum(scores[product_id] for product_id in ranked)  # 总分，用于算份额
    items: list[dict] = []  # ABC 行结果
    previous = 0.0  # 进入本行前的累计份额
    for index, product_id in enumerate(ranked):  # 按排序逐个打 A/B/C
        score = scores[product_id]  # 本行分值
        share = (score / total) if total > 0 else (1 / len(ranked) if ranked else 0)  # 份额；总分为 0 时均分
        if previous < 0.80:  # 累计尚未到 80% 的商品为 A
            klass = "A"  # A 类
        elif previous < 0.95:  # 80%~95% 为 B
            klass = "B"  # B 类
        else:  # 其余为 C
            klass = "C"  # C 类
        previous += share  # 累加本行份额，供下一行判断
        product = products.get(product_id)  # 取主数据展示字段
        items.append(  # 追加一行 ABC
            {  # 报表行
                "product_id": product_id,  # 商品 ID
                "sku_code": product.sku_code if product else str(product_id),  # 无主数据时用 ID
                "product_name": product.product_name if product else "",  # 品名
                "score": score,  # 出库量或现存量
                "share": round(share, 6),  # 本行份额
                "class": klass,  # A/B/C
                "basis": "outbound" if use_outbound else "on_hand",  # 分类依据
            }  # 结束行
        )  # 结束 append
        if index == 0 and len(ranked) == 1:  # 只有一个商品时强制 A，避免均分落到 C
            items[-1]["class"] = "A"  # 单品定为 A 类
    if items:  # 用余数修正最后一行份额，保证加总为 1
        remainder = 1 - sum(item["share"] for item in items[:-1])  # 前面份额之和的补数
        items[-1]["share"] = round(remainder, 6)  # 写回末行
    return {"items": items, "basis": "outbound" if use_outbound else "on_hand"}  # 只读返回，助手可展示但不会改库存


def turnover_report(db: Session) -> dict:  # 只读周转率：出库量 / max(现存量, 1)
    products, outbound_map, stock_map = _product_maps(db)  # 全量映射，不限天数
    ranked = _ranked_product_ids(products, outbound_map, stock_map)  # 先按同样规则列出商品
    items = []  # 周转行
    for product_id in ranked:  # 逐商品计算
        product = products.get(product_id)  # 主数据
        outbound_quantity = outbound_map.get(product_id, 0)  # 累计出库量
        on_hand = stock_map.get(product_id, 0)  # 当前实际库存
        items.append(  # 一行周转
            {  # 字段
                "product_id": product_id,  # ID
                "sku_code": product.sku_code if product else str(product_id),  # SKU
                "product_name": product.product_name if product else "",  # 品名
                "outbound_quantity": outbound_quantity,  # 出库量
                "on_hand_quantity": on_hand,  # 现存量（只读）
                "turnover_rate": round(outbound_quantity / max(on_hand, 1), 6),  # 现存量 0 时分母取 1 避免除零
            }  # 结束行
        )  # 结束 append
    items.sort(key=lambda row: (-row["turnover_rate"], row["sku_code"]))  # 周转率高优先，同分按 SKU
    return {"items": items}  # 只读


def _ledger_day(value: datetime | None) -> str | None:  # 流水时间归到 UTC 日期字符串
    if value is None:  # 无时间无法归日
        return None  # 调用方跳过该行
    if value.tzinfo is not None:  # 带时区则转到 UTC 再去时区
        value = value.astimezone(UTC).replace(tzinfo=None)  # 与库中 naive 时间对齐
    return value.date().isoformat()  # YYYY-MM-DD 作为日报键


def _movement_totals(db: Session, cutoff: datetime) -> tuple[dict[str, int], dict[str, int]]:  # 只读按日累加入库/出库流水
    inbound: dict[str, int] = defaultdict(int)  # 日期 → 入库数量
    outbound: dict[str, int] = defaultdict(int)  # 日期 → 出库数量
    rows = db.execute(  # 只读扫流水，不锁库存行
        select(StockLedger.created_at, StockLedger.transaction_type, StockLedger.quantity_delta).where(  # 取时间、类型、数量差
            StockLedger.created_at >= cutoff,  # 窗口内
            StockLedger.transaction_type.in_(("inbound", "outbound")),  # 只统计收发，不含盘点/移库
        )  # 结束条件
    )  # 结束执行
    for created_at, transaction_type, delta in rows:  # 逐条归日
        key = _ledger_day(created_at)  # 得到日期键
        if not key:  # 时间为空则丢弃
            continue  # 下一条
        amount = int(delta or 0)  # 数量差转整数
        if transaction_type == "inbound":  # 入库流水为正
            inbound[key] += amount  # 累加入库
        else:  # outbound，流水为负，取绝对值
            outbound[key] += abs(amount)  # 累加出库量
    return inbound, outbound  # 供日报/周报填桶


def daily_report(db: Session, days: int = 7) -> dict:  # 只读近 N 日入出库，默认 7 天
    days = max(1, min(days, 31))  # 限制 1~31 天，避免过大扫描
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days - 1)  # 含今天共 days 天的起点
    inbound, outbound = _movement_totals(db, cutoff)  # 只读按日合计
    items = []  # 每日一行
    today = datetime.now(UTC).date()  # 今天（UTC 日期）
    for offset in range(days):  # 从最早一天填到今天，没有流水也出 0
        day = (today - timedelta(days=days - 1 - offset)).isoformat()  # 该格日期
        items.append(  # 日报行
            {  # 字段
                "date": day,  # 日期
                "inbound_quantity": inbound[day],  # 当天入库（无则 0）
                "outbound_quantity": outbound[day],  # 当天出库（无则 0）
            }  # 结束行
        )  # 结束 append
    return {"items": items, "days": days}  # 只读，助手展示用


def weekly_report(db: Session, weeks: int = 4) -> dict:  # 只读近 N 周入出库，按 ISO 周聚合
    weeks = max(1, min(weeks, 12))  # 限制 1~12 周
    today = datetime.now(UTC).date()  # 今天
    start = today - timedelta(days=today.isoweekday() - 1 + 7 * (weeks - 1))  # 最早一周的周一
    cutoff = datetime.combine(start, datetime.min.time())  # 该周一 00:00 作为流水窗口
    inbound, outbound = _movement_totals(db, cutoff)  # 先按日合计再归周
    buckets: dict[str, dict[str, int]] = {}  # ISO 周键 → 入出库
    current = start  # 从最早周一开始填桶
    for _ in range(weeks):  # 预创建每一周，保证无流水周也出现
        iso = current.isocalendar()  # 取 ISO 年与周
        key = f"{iso.year}-W{iso.week:02d}"  # 如 2026-W12
        buckets[key] = {"inbound_quantity": 0, "outbound_quantity": 0}  # 先放 0
        current += timedelta(days=7)  # 下一周
    for day, quantity in inbound.items():  # 把每日入库归到 ISO 周
        parsed = datetime.fromisoformat(day).date()  # 解析日期
        iso = parsed.isocalendar()  # ISO 周
        key = f"{iso.year}-W{iso.week:02d}"  # 周键
        if key in buckets:  # 只累加窗口内的周
            buckets[key]["inbound_quantity"] += quantity  # 加入该周入库
    for day, quantity in outbound.items():  # 每日出库归周
        parsed = datetime.fromisoformat(day).date()  # 解析日期
        iso = parsed.isocalendar()  # ISO 周
        key = f"{iso.year}-W{iso.week:02d}"  # 周键
        if key in buckets:  # 窗口内
            buckets[key]["outbound_quantity"] += quantity  # 加入该周出库
    items = [{"week": week, **totals} for week, totals in buckets.items()]  # 展开为列表，保持插入顺序
    return {"items": items, "weeks": weeks}  # 只读


def picking_efficiency(db: Session) -> dict:  # 只读拣货效率：完成率与平均确认秒数
    rows = list(db.scalars(select(PickingTask)))  # 全量拣货任务，不改状态
    total = len(rows)  # 任务总数
    completed = sum(1 for row in rows if row.status in {"picked", "completed"})  # 已拣或已完成都算完成
    durations = []  # 有效确认耗时
    for row in rows:  # 逐任务算耗时
        if row.confirmed_at and row.created_at:  # 必须有创建与确认时间
            seconds = elapsed_seconds(row.created_at, row.confirmed_at)  # 规范化后的秒数
            if seconds is not None:  # 能算出才计入
                durations.append(seconds)  # 收集样本
    avg_seconds = round(sum(durations) / len(durations), 2) if durations else 0  # 无样本则为 0
    return {  # 效率指标
        "total_tasks": total,  # 总任务
        "completed_tasks": completed,  # 已完成数
        "completion_rate": round(completed / total, 6) if total else 0,  # 完成率，无任务为 0
        "average_confirm_seconds": avg_seconds,  # 平均确认秒数
    }  # 只读返回
