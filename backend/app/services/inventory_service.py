"""唯一写库存服务：行锁改余额、写流水与审计、校验幂等键。"""

from __future__ import annotations  # 启用延后求值类型注解，避免循环引用

from contextlib import contextmanager  # 引入上下文管理器，用于库存锁的获取与释放
from datetime import UTC, datetime  # 引入时区常量与时间类型（本文件签名/调用链可能用到）
from dataclasses import dataclass  # 引入数据类，封装幂等回放的服务结果
from typing import Any, Iterator  # 引入任意类型与迭代器类型，标注锁与响应体

from sqlalchemy import select  # 引入查询构造器，按 SKU+库位读取库存行
from sqlalchemy.orm import Session  # 引入会话类型，所有写库存都走同一事务

from backend.app.core.cache import acquire_stock_lock, invalidate_stock_cache, release_stock_lock  # 分布式库存锁与缓存失效
from backend.app.core.errors import AppError  # 业务错误，库存不足/状态异常时抛出
from backend.app.core.logging import current_request_id, get_logger  # 取请求号与库存日志器
from backend.app.models import AuditLog, IdempotencyRecord, StockBalance, StockCountItem, StockCountOrder, StockLedger, WarehouseLocation  # 余额、流水、幂等、审计与盘点模型

inventory_logger = get_logger("inventory")  # 库存写路径专用日志，便于追踪过账


@dataclass(frozen=True)  # 冻结结果对象，防止回放响应被意外改写
class ServiceResult:  # 封装接口回放体：响应、状态码、是否幂等重放
    body: dict[str, Any]  # 上次成功写入时保存的响应 JSON
    status_code: int  # 上次成功写入时的 HTTP 状态码
    replayed: bool = False  # 标记本次是否因幂等键直接回放而未再改库存


def require_idempotency_key(key: str | None) -> str:  # 写库存前强制校验幂等键，防止连点重复过账
    # 防止连点造成重复收货、重复预留、重复扣账。
    if not key or not key.strip():  # 空键视为非法写操作，拒绝进入库存事务
        raise AppError("IDEMPOTENCY_KEY_REQUIRED", "写操作必须提供 Idempotency-Key", 400)  # 缺少幂等键直接 400
    return key.strip()  # 去掉首尾空白后作为幂等键使用


def existing_idempotent_response(db: Session, user_id: int, key: str) -> dict[str, Any] | None:  # 查该用户该键是否已成功写过
    row = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user_id, IdempotencyRecord.idempotency_key == key))  # 按用户+键取幂等记录
    return row.response_body if row is not None and row.response_body is not None else None  # 有缓存体则回放，避免再次改库存


def replay_result(db: Session, user_id: int, key: str) -> ServiceResult | None:  # 把幂等记录包装成可直接返回的服务结果
    row = db.scalar(  # 查询该用户该幂等键对应的历史记录
        select(IdempotencyRecord).where(  # 只匹配幂等表，不碰库存余额
            IdempotencyRecord.user_id == user_id,  # 幂等作用域限定到当前用户
            IdempotencyRecord.idempotency_key == key,  # 精确匹配本次请求的幂等键
        )  # 结束 where 条件
    )  # 取单行幂等记录
    if row is None or row.response_body is None:  # 没有可回放的成功响应则继续走真实写库存
        return None  # 告知调用方需要执行业务而不是回放
    return ServiceResult(row.response_body, row.response_status or 200, True)  # 回放历史响应并标记 replayed


def record_idempotent_response(  # 写库存成功后落幂等记录，供下次相同键直接回放
    db: Session,  # 当前事务会话，与库存写入同一提交
    *,  # 后续一律关键字传参，避免键/路径传错位
    user_id: int,  # 幂等作用域：同一用户
    key: str,  # 客户端幂等键
    method: str = "POST",  # 记录原请求方法，默认写操作
    path: str,  # 记录原请求路径，区分入库/出库/盘点
    body: dict[str, Any],  # 成功响应体，下次原样返回
    status: int = 200,  # 成功状态码，创建类接口可传 201
) -> None:  # 只写幂等表，不改库存数量
    db.add(  # 把本次成功结果插入幂等表
        IdempotencyRecord(  # 构造幂等行：键+路径+响应
            user_id=user_id,  # 绑定操作用户
            idempotency_key=key,  # 保存幂等键
            request_method=method,  # 保存方法便于审计对照
            request_path=path,  # 保存路径避免跨接口误回放
            response_status=status,  # 保存状态码
            response_body=body,  # 保存响应 JSON 供回放
        )  # 结束幂等记录字段
    )  # 加入会话，等待与库存变更一并提交


def write_audit(  # 写库存相关审计：谁改了哪条实体、改前改后数量
    db: Session,  # 同一事务写入审计，保证与余额变更一致
    *,  # 关键字传参，避免动作与实体类型传混
    user_id: int,  # 操作人
    action: str,  # 业务动作名，如 inbound_confirm
    entity_type: str,  # 实体类型，如 stock_balance
    entity_id: int | str,  # 实体主键，统一转字符串存储
    before: dict | None = None,  # 变更前快照（可选）
    after: dict | None = None,  # 变更后快照（可选）
    quantity_before: int | None = None,  # 库存改前数量
    quantity_after: int | None = None,  # 库存改后数量
    request_id: str = "api",  # 请求追踪号，默认可替换为当前请求
) -> None:  # 只写审计日志，不直接改余额
    resolved_request_id = request_id if request_id != "api" else (current_request_id() or "api")  # 优先用调用方传入，否则取当前请求号
    db.add(  # 插入一条审计记录
        AuditLog(  # 构造审计行
            request_id=resolved_request_id,  # 关联本次 HTTP 请求
            user_id=user_id,  # 记录操作人
            action=action,  # 记录动作
            entity_type=entity_type,  # 记录实体类型
            entity_id=str(entity_id),  # 主键转字符串便于通用存储
            before_state=before,  # 改前状态 JSON
            after_state=after,  # 改后状态 JSON
            quantity_before=quantity_before,  # 库存改前
            quantity_after=quantity_after,  # 库存改后
        )  # 结束审计字段
    )  # 加入会话待提交


@contextmanager  # 把获取/释放库存锁包装成 with 语句
def _stock_lock(product_id: int, location_id: int) -> Iterator[None]:  # 按 SKU+库位加锁，串行化同一余额的并发过账
    key = acquire_stock_lock(product_id, location_id)  # 申请该 SKU+库位的库存锁
    try:  # 锁持有期间执行调用方的库存写入
        yield  # 把控制权交给 with 块内的过账逻辑
    finally:  # 无论成功失败都释放锁，避免死锁
        release_stock_lock(key)  # 释放刚才申请的库存锁


def available_units(balance: StockBalance) -> int:  # 计算可被分配/移库的数量，助手查询也复用此公式
    # 可用 = 实际 − 出库预留 − 冻结（盘点等），不能为负。
    frozen = int(balance.frozen_quantity or 0)  # 盘点等冻结量，空值当 0
    return max(0, int(balance.quantity) - int(balance.reserved_quantity) - frozen)  # 按公式算可用并禁止负数


def _locked_balance(db: Session, product_id: int, location_id: int, *, create: bool = False) -> StockBalance:  # 行锁读取（可创建）库存余额
    # 行锁：同一 SKU+库位并发过账时串行，避免超卖。
    statement = select(StockBalance).where(StockBalance.product_id == product_id, StockBalance.location_id == location_id).with_for_update()  # SELECT FOR UPDATE 锁住该余额行
    balance = db.scalar(statement)  # 取出被行锁保护的余额
    if balance is None and create:  # 入库/盘点允许没有余额时新建零库存行
        balance = StockBalance(  # 新建 SKU+库位余额，数量从 0 起
            product_id=product_id,  # 绑定商品
            location_id=location_id,  # 绑定库位
            quantity=0,  # 实际库存初始为 0
            reserved_quantity=0,  # 预留初始为 0
            frozen_quantity=0,  # 冻结初始为 0
        )  # 结束新建余额字段
        db.add(balance); db.flush()  # 插入并 flush 以拿到 balance_id
    if balance is None:  # 不允许创建且行不存在时，不能凭空扣账
        raise AppError("STOCK_BALANCE_NOT_FOUND", "库位库存不存在", 404, {"product_id": product_id, "location_id": location_id})  # 余额缺失返回 404
    return balance  # 返回已加行锁的余额对象，供后续改数量


def apply_inbound(db: Session, *, product_id: int, location_id: int, quantity: int, source_id: int, key: str, user_id: int) -> None:  # 唯一入库加库存入口：加实际数量并写流水
    with _stock_lock(product_id, location_id):  # 先拿 SKU+库位锁再改余额
        balance = _locked_balance(db, product_id, location_id, create=True)  # 行锁读取，没有则创建零库存行
        before = balance.quantity  # 记下加库存前的实际数量
        balance.quantity += quantity  # 实际库存增加收货数量
        db.add(StockLedger(product_id=product_id, location_id=location_id, transaction_type="inbound", quantity_delta=quantity, before_quantity=before, after_quantity=balance.quantity, source_type="inbound_order", source_id=source_id, idempotency_key=f"{key}:{product_id}:{location_id}", operator_id=None))  # 写入库流水，键含 SKU+库位防重复过账
        write_audit(db, user_id=user_id, action="inbound_confirm", entity_type="stock_balance", entity_id=balance.balance_id, quantity_before=before, quantity_after=balance.quantity)  # 审计入库确认前后数量
        invalidate_stock_cache()  # 库存已变，作废看板等库存缓存
        inventory_logger.info(  # 记录入库过账日志
            "inbound product_id=%s location_id=%s qty=%s source_id=%s",  # 日志模板：商品、库位、数量、来源单
            product_id,  # 商品 ID
            location_id,  # 库位 ID
            quantity,  # 本次加库存数量
            source_id,  # 入库单 ID
        )  # 结束入库日志参数


def set_frozen_quantity(db: Session, *, product_id: int, location_id: int, frozen_quantity: int) -> None:  # 设置冻结量（盘点占用），不改实际库存
    with _stock_lock(product_id, location_id):  # 锁住该余额后再改冻结
        balance = _locked_balance(db, product_id, location_id, create=True)  # 行锁读取或创建余额
        balance.frozen_quantity = max(0, frozen_quantity)  # 冻结量不能为负
        invalidate_stock_cache()  # 可用量变化，失效库存缓存


def refresh_count_freeze(db: Session, pairs: set[tuple[int, int]]) -> None:  # 按盘点待审状态刷新 SKU+库位冻结
    for product_id, location_id in pairs:  # 逐对处理需要重算冻结的 SKU+库位
        active = db.scalar(  # 查该对是否仍有待审批盘点
            select(StockCountOrder.stock_count_order_id)  # 只取盘点单号判断是否存在
            .join(StockCountItem, StockCountItem.stock_count_order_id == StockCountOrder.stock_count_order_id)  # 关联盘点明细
            .where(  # 匹配商品、库位且盘点单待审批
                StockCountItem.product_id == product_id,  # 同一商品
                StockCountItem.location_id == location_id,  # 同一库位
                StockCountOrder.status == "pending_approval",  # 仅待审批盘点才冻结
            )  # 结束盘点条件
            .limit(1)  # 有一条即可视为仍需冻结
        )  # 得到待审盘点单号或空
        with _stock_lock(product_id, location_id):  # 锁余额后改冻结量
            balance = _locked_balance(db, product_id, location_id, create=True)  # 行锁读取余额
            if active:  # 仍有待审盘点：把未预留部分全部冻结，防止盘中出库
                balance.frozen_quantity = max(0, balance.quantity - balance.reserved_quantity)  # 冻结 = 实际 − 已预留
            else:  # 没有待审盘点则解冻
                balance.frozen_quantity = 0  # 清零冻结，恢复可用
            invalidate_stock_cache()  # 冻结变化后失效缓存


def reserve(  # 出库分配：按库位占用预留，不扣实际库存
    db: Session,  # 当前事务
    *,  # 关键字传参
    product_id: int,  # 要预留的商品
    quantity: int,  # 需要预留的总数量
    source_id: int,  # 出库单 ID，写入审计
    key: str,  # 幂等键（由上层保证，本函数按行改预留）
    user_id: int,  # 操作人
    warehouse_ids: set[int] | None = None,  # 可选仓库范围，限制只能从授权仓分配
) -> list[tuple[int, int]]:  # 返回 [(库位, 预留数量)] 供生成拣货任务
    with _stock_lock(product_id, 0):  # 按商品加锁（库位 0 表示整 SKU 分配串行），避免并发超卖
        statement = (  # 构造可分配余额查询
            select(StockBalance)  # 读取库存余额
            .join(WarehouseLocation, WarehouseLocation.location_id == StockBalance.location_id)  # 关联库位以过滤启用仓位
            .where(  # 只从有可用量的启用库位分配
                StockBalance.product_id == product_id,  # 同一商品
                WarehouseLocation.is_active.is_(True),  # 停用库位不参与分配
                (StockBalance.quantity - StockBalance.reserved_quantity - StockBalance.frozen_quantity) > 0,  # 必须有可用量
            )  # 结束筛选
            .order_by(StockBalance.location_id)  # 按库位 ID 稳定分配，保证幂等结果一致
            .with_for_update()  # 行锁这些余额，防止并发预留超卖
        )  # 结束查询构造
        if warehouse_ids is not None:  # 若限定仓库范围（授权仓）
            statement = statement.where(WarehouseLocation.warehouse_id.in_(warehouse_ids or [-1]))  # 只从授权仓库分配；空集合用 -1 匹配不到
        rows = list(db.scalars(statement))  # 取出所有可分配且已行锁的余额
        remaining = quantity  # 还需要预留的数量
        allocations: list[tuple[int, int]] = []  # 记录每个库位分到的预留量
        for balance in rows:  # 按库位依次占用可用量
            take = min(remaining, available_units(balance))  # 本库位最多能拿剩余需求与可用量的较小值
            if take:  # 本库位能分到货才改预留
                balance.reserved_quantity += take  # 增加预留，实际库存暂不减少
                allocations.append((balance.location_id, take))  # 记下库位与预留数量
                remaining -= take  # 扣减尚未满足的需求
            if remaining == 0:  # 已分配满则停止扫库位
                break  # 结束分配循环
        if remaining:  # 扫完仍不够，视为库存不足，整单回滚
            raise AppError(  # 抛出不足错误，不提交部分预留
                "INVENTORY_INSUFFICIENT",  # 库存不足错误码
                "库存不足",  # 中文提示
                409,  # 冲突状态，前端可重试或改数量
                {"product_id": product_id, "required": quantity, "shortage": remaining},  # 带上缺口便于排查
            )  # 结束不足错误
        for location_id, amount in allocations:  # 为每个库位的预留写审计
            write_audit(  # 记录出库分配动作
                db,  # 同一事务
                user_id=user_id,  # 操作人
                action="outbound_allocate",  # 动作：出库分配预留
                entity_type="outbound_order",  # 实体是出库单
                entity_id=source_id,  # 出库单 ID
                after={"location_id": location_id, "reserved_quantity": amount},  # 记录库位与预留量
            )  # 结束单条分配审计
        invalidate_stock_cache()  # 可用量因预留下降，失效缓存
        inventory_logger.info(  # 记录预留成功日志
            "reserve product_id=%s qty=%s locations=%s source_id=%s",  # 模板：商品、数量、库位分配、出库单
            product_id,  # 商品
            quantity,  # 总需求
            allocations,  # 各库位预留明细
            source_id,  # 出库单
        )  # 结束预留日志
        return allocations  # 返回分配结果给拣货任务生成


def deduct_reserved(db: Session, *, product_id: int, location_id: int, quantity: int, source_id: int, key: str, user_id: int) -> None:  # 出库完成：同时扣实际库存与预留
    with _stock_lock(product_id, location_id):  # 锁该 SKU+库位后再扣账
        balance = _locked_balance(db, product_id, location_id)  # 行锁读取已有余额，不存在则失败
        if balance.reserved_quantity < quantity or balance.quantity < quantity:  # 预留或实际不足说明状态被并发破坏
            raise AppError("INVENTORY_STATE_INVALID", "预留库存状态异常", 409)  # 拒绝扣账，避免把库存扣成不一致
        before = balance.quantity  # 记下扣账前实际数量
        balance.quantity -= quantity; balance.reserved_quantity -= quantity  # 实际与预留同步减少，完成出库过账
        db.add(StockLedger(product_id=product_id, location_id=location_id, transaction_type="outbound", quantity_delta=-quantity, before_quantity=before, after_quantity=balance.quantity, source_type="outbound_order", source_id=source_id, idempotency_key=f"{key}:{product_id}:{location_id}", operator_id=None))  # 写出库流水，数量为负
        write_audit(db, user_id=user_id, action="outbound_complete", entity_type="stock_balance", entity_id=balance.balance_id, quantity_before=before, quantity_after=balance.quantity)  # 审计出库完成前后数量
        invalidate_stock_cache()  # 实际库存已减，失效缓存
        inventory_logger.info(  # 记录出库扣账日志
            "outbound product_id=%s location_id=%s qty=%s source_id=%s",  # 模板：商品、库位、数量、出库单
            product_id,  # 商品
            location_id,  # 库位
            quantity,  # 扣账数量
            source_id,  # 出库单
        )  # 结束出库日志


def apply_count_adjustment(  # 盘点过账：把余额改到实盘目标数量并写盈亏流水
    db: Session,  # 当前事务
    *,  # 关键字传参
    product_id: int,  # 盘点商品
    location_id: int,  # 盘点库位
    target_quantity: int,  # 实盘目标实际库存
    source_id: int,  # 盘点单 ID
    item_id: int,  # 盘点明细 ID，编入幂等键
    key: str,  # 请求幂等键
    user_id: int,  # 操作人，写入流水操作者
    request_id: str = "api",  # 请求追踪号
) -> None:  # 改实际库存，是写库存路径
    with _stock_lock(product_id, location_id):  # 锁该余额后调整
        balance = _locked_balance(db, product_id, location_id, create=True)  # 行锁读取或创建
        before = balance.quantity  # 账存数量
        delta = target_quantity - before  # 盈为正、亏为负
        if delta == 0:  # 账实一致则不写流水、不改库存
            return  # 直接返回，保持幂等无副作用
        balance.quantity = target_quantity  # 把实际库存改成实盘数量
        db.add(  # 写入盘点盈亏流水
            StockLedger(  # 构造流水：盘盈或盘亏
                product_id=product_id,  # 商品
                location_id=location_id,  # 库位
                transaction_type="count_gain" if delta > 0 else "count_loss",  # 正数盘盈、负数盘亏
                quantity_delta=delta,  # 差额
                before_quantity=before,  # 改前
                after_quantity=target_quantity,  # 改后即实盘
                source_type="stock_count_order",  # 来源盘点单
                source_id=source_id,  # 盘点单 ID
                idempotency_key=f"{key}:stock-count-item-{item_id}:apply",  # 明细级幂等键，防同一行重复过账
                operator_id=user_id,  # 记录盘点过账人
            )  # 结束流水字段
        )  # 加入会话
        write_audit(  # 审计盘点过账
            db,  # 同一事务
            user_id=user_id,  # 操作人
            action="stock_count_apply",  # 动作：盘点应用
            entity_type="stock_balance",  # 改的是余额
            entity_id=balance.balance_id,  # 余额主键
            quantity_before=before,  # 账存
            quantity_after=target_quantity,  # 实盘
            request_id=request_id,  # 追踪号
        )  # 结束审计
        invalidate_stock_cache()  # 实际库存已按盘点调整，失效缓存
        inventory_logger.info(  # 记录盘点调整日志
            "count_adjust product_id=%s location_id=%s before=%s after=%s source_id=%s",  # 模板：商品库位及前后数量
            product_id,  # 商品
            location_id,  # 库位
            before,  # 账存
            target_quantity,  # 实盘
            source_id,  # 盘点单
        )  # 结束盘点日志


def execute_transfer_line(  # 移库一行：源库位减、目标库位加，成对写流水
    db: Session,  # 当前事务
    *,  # 关键字传参
    product_id: int,  # 移库商品
    source_location_id: int,  # 源库位
    target_location_id: int,  # 目标库位
    quantity: int,  # 移库数量
    source_id: int,  # 移库单 ID
    item_id: int,  # 移库明细 ID，编入幂等键
    key: str,  # 请求幂等键
    user_id: int,  # 操作人
) -> None:  # 同时改两个库位的实际库存
    first_location_id, second_location_id = sorted((source_location_id, target_location_id))  # 按库位 ID 排序加锁，避免交叉死锁
    with _stock_lock(product_id, first_location_id), _stock_lock(product_id, second_location_id):  # 按固定顺序锁两个库位
        first_balance = _locked_balance(db, product_id, first_location_id, create=True)  # 行锁较小库位余额
        second_balance = _locked_balance(db, product_id, second_location_id, create=True)  # 行锁较大库位余额
        source, target = (  # 按真实源/目标重新映射余额对象
            (first_balance, second_balance)  # 源库位 ID 更小则 first 是源
            if source_location_id < target_location_id  # 比较源目标库位 ID
            else (second_balance, first_balance)  # 否则 second 才是源
        )  # 得到 source/target 余额

        available_quantity = available_units(source)  # 源库位可用量（扣预留与冻结）
        if available_quantity < quantity:  # 可用不足则不能移库，避免把预留货移走
            raise AppError(  # 抛库存不足
                "INVENTORY_INSUFFICIENT",  # 错误码
                "库存不足",  # 提示
                409,  # 冲突
                {  # 带上需求与可用便于前端展示
                    "required": quantity,  # 本次要移的数量
                    "available": available_quantity,  # 源库位当前可用
                },  # 结束详情
            )  # 结束不足错误

        source_before = source.quantity  # 源库位改前实际数量
        target_before = target.quantity  # 目标库位改前实际数量
        source.quantity -= quantity  # 源库位减库存
        target.quantity += quantity  # 目标库位加库存
        db.add(  # 写移出流水
            StockLedger(  # 源库位 transfer_out
                product_id=product_id,  # 商品
                location_id=source_location_id,  # 源库位
                transaction_type="transfer_out",  # 移出类型
                quantity_delta=-quantity,  # 数量为负
                before_quantity=source_before,  # 源改前
                after_quantity=source.quantity,  # 源改后
                source_type="transfer_order",  # 来源移库单
                source_id=source_id,  # 移库单 ID
                idempotency_key=f"{key}:transfer-item-{item_id}:out",  # 明细移出幂等键
                operator_id=user_id,  # 操作人
            )  # 结束移出流水
        )  # 加入会话
        db.add(  # 写移入流水
            StockLedger(  # 目标库位 transfer_in
                product_id=product_id,  # 商品
                location_id=target_location_id,  # 目标库位
                transaction_type="transfer_in",  # 移入类型
                quantity_delta=quantity,  # 数量为正
                before_quantity=target_before,  # 目标改前
                after_quantity=target.quantity,  # 目标改后
                source_type="transfer_order",  # 来源移库单
                source_id=source_id,  # 移库单 ID
                idempotency_key=f"{key}:transfer-item-{item_id}:in",  # 明细移入幂等键
                operator_id=user_id,  # 操作人
            )  # 结束移入流水
        )  # 加入会话
        write_audit(  # 审计源库位移出
            db,  # 同一事务
            user_id=user_id,  # 操作人
            action="transfer_out",  # 移出动作
            entity_type="stock_balance",  # 改余额
            entity_id=source.balance_id,  # 源余额 ID
            quantity_before=source_before,  # 源改前
            quantity_after=source.quantity,  # 源改后
        )  # 结束移出审计
        write_audit(  # 审计目标库位移入
            db,  # 同一事务
            user_id=user_id,  # 操作人
            action="transfer_in",  # 移入动作
            entity_type="stock_balance",  # 改余额
            entity_id=target.balance_id,  # 目标余额 ID
            quantity_before=target_before,  # 目标改前
            quantity_after=target.quantity,  # 目标改后
        )  # 结束移入审计
        invalidate_stock_cache()  # 两库位库存已变，失效缓存
        inventory_logger.info(  # 记录移库日志
            "transfer product_id=%s source=%s target=%s qty=%s source_id=%s",  # 模板：商品、源、目标、数量、单据
            product_id,  # 商品
            source_location_id,  # 源库位
            target_location_id,  # 目标库位
            quantity,  # 移库数量
            source_id,  # 移库单
        )  # 结束移库日志
