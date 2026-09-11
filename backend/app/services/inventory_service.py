from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.models import AuditLog, IdempotencyRecord, StockBalance, StockLedger


@dataclass(frozen=True)
class ServiceResult:
    body: dict[str, Any]
    status_code: int
    replayed: bool = False


def require_idempotency_key(key: str | None) -> str:
    if not key or not key.strip():
        raise AppError("IDEMPOTENCY_KEY_REQUIRED", "写操作必须提供 Idempotency-Key", 400)
    return key.strip()


def existing_idempotent_response(db: Session, user_id: int, key: str) -> dict[str, Any] | None:
    row = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user_id, IdempotencyRecord.idempotency_key == key))
    return row.response_body if row is not None and row.response_body is not None else None


def replay_result(db: Session, user_id: int, key: str) -> ServiceResult | None:
    row = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    if row is None or row.response_body is None:
        return None
    return ServiceResult(row.response_body, row.response_status or 200, True)


def record_idempotent_response(
    db: Session,
    *,
    user_id: int,
    key: str,
    method: str = "POST",
    path: str,
    body: dict[str, Any],
    status: int = 200,
) -> None:
    db.add(
        IdempotencyRecord(
            user_id=user_id,
            idempotency_key=key,
            request_method=method,
            request_path=path,
            response_status=status,
            response_body=body,
        )
    )


def write_audit(
    db: Session,
    *,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int | str,
    before: dict | None = None,
    after: dict | None = None,
    quantity_before: int | None = None,
    quantity_after: int | None = None,
    request_id: str = "api",
) -> None:
    db.add(
        AuditLog(
            request_id=request_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before_state=before,
            after_state=after,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
        )
    )


def _locked_balance(db: Session, product_id: int, location_id: int, *, create: bool = False) -> StockBalance:
    statement = select(StockBalance).where(StockBalance.product_id == product_id, StockBalance.location_id == location_id).with_for_update()
    balance = db.scalar(statement)
    if balance is None and create:
        balance = StockBalance(product_id=product_id, location_id=location_id, quantity=0, reserved_quantity=0)
        db.add(balance); db.flush()
    if balance is None:
        raise AppError("STOCK_BALANCE_NOT_FOUND", "库位库存不存在", 404, {"product_id": product_id, "location_id": location_id})
    return balance


def apply_inbound(db: Session, *, product_id: int, location_id: int, quantity: int, source_id: int, key: str, user_id: int) -> None:
    balance = _locked_balance(db, product_id, location_id, create=True)
    before = balance.quantity
    balance.quantity += quantity
    db.add(StockLedger(product_id=product_id, location_id=location_id, transaction_type="inbound", quantity_delta=quantity, before_quantity=before, after_quantity=balance.quantity, source_type="inbound_order", source_id=source_id, idempotency_key=f"{key}:{product_id}:{location_id}", operator_id=None))
    write_audit(db, user_id=user_id, action="inbound_confirm", entity_type="stock_balance", entity_id=balance.balance_id, quantity_before=before, quantity_after=balance.quantity)


def reserve(db: Session, *, product_id: int, quantity: int, source_id: int, key: str, user_id: int) -> list[tuple[int, int]]:
    rows = list(db.scalars(select(StockBalance).where(StockBalance.product_id == product_id, StockBalance.quantity > StockBalance.reserved_quantity).order_by(StockBalance.location_id).with_for_update()))
    remaining = quantity; allocations: list[tuple[int, int]] = []
    for balance in rows:
        take = min(remaining, balance.quantity - balance.reserved_quantity)
        if take:
            balance.reserved_quantity += take; allocations.append((balance.location_id, take)); remaining -= take
        if remaining == 0: break
    if remaining:
        raise AppError("INVENTORY_INSUFFICIENT", "可用库存不足", 409, {"product_id": product_id, "required": quantity, "shortage": remaining})
    for location_id, amount in allocations:
        write_audit(db, user_id=user_id, action="outbound_allocate", entity_type="outbound_order", entity_id=source_id, after={"location_id": location_id, "reserved_quantity": amount})
    return allocations


def deduct_reserved(db: Session, *, product_id: int, location_id: int, quantity: int, source_id: int, key: str, user_id: int) -> None:
    balance = _locked_balance(db, product_id, location_id)
    if balance.reserved_quantity < quantity or balance.quantity < quantity:
        raise AppError("INVENTORY_STATE_INVALID", "预留库存状态异常", 409)
    before = balance.quantity
    balance.quantity -= quantity; balance.reserved_quantity -= quantity
    db.add(StockLedger(product_id=product_id, location_id=location_id, transaction_type="outbound", quantity_delta=-quantity, before_quantity=before, after_quantity=balance.quantity, source_type="outbound_order", source_id=source_id, idempotency_key=f"{key}:{product_id}:{location_id}", operator_id=None))
    write_audit(db, user_id=user_id, action="outbound_complete", entity_type="stock_balance", entity_id=balance.balance_id, quantity_before=before, quantity_after=balance.quantity)


def apply_count_adjustment(
    db: Session,
    *,
    product_id: int,
    location_id: int,
    target_quantity: int,
    source_id: int,
    item_id: int,
    key: str,
    user_id: int,
    request_id: str = "api",
) -> None:
    balance = _locked_balance(db, product_id, location_id, create=True)
    before = balance.quantity
    delta = target_quantity - before
    if delta == 0:
        return
    balance.quantity = target_quantity
    db.add(
        StockLedger(
            product_id=product_id,
            location_id=location_id,
            transaction_type="count_gain" if delta > 0 else "count_loss",
            quantity_delta=delta,
            before_quantity=before,
            after_quantity=target_quantity,
            source_type="stock_count_order",
            source_id=source_id,
            idempotency_key=f"{key}:stock-count-item-{item_id}:apply",
            operator_id=user_id,
        )
    )
    write_audit(
        db,
        user_id=user_id,
        action="stock_count_apply",
        entity_type="stock_balance",
        entity_id=balance.balance_id,
        quantity_before=before,
        quantity_after=target_quantity,
        request_id=request_id,
    )


def execute_transfer_line(
    db: Session,
    *,
    product_id: int,
    source_location_id: int,
    target_location_id: int,
    quantity: int,
    source_id: int,
    item_id: int,
    key: str,
    user_id: int,
) -> None:
    first_location_id, second_location_id = sorted((source_location_id, target_location_id))
    first_balance = _locked_balance(db, product_id, first_location_id, create=True)
    second_balance = _locked_balance(db, product_id, second_location_id, create=True)
    source, target = (
        (first_balance, second_balance)
        if source_location_id < target_location_id
        else (second_balance, first_balance)
    )

    available_quantity = source.quantity - source.reserved_quantity
    if available_quantity < quantity:
        raise AppError(
            "INVENTORY_INSUFFICIENT",
            "可用库存不足",
            409,
            {
                "product_id": product_id,
                "location_id": source_location_id,
                "required": quantity,
                "available": available_quantity,
            },
        )

    source_before = source.quantity
    target_before = target.quantity
    source.quantity -= quantity
    target.quantity += quantity
    db.add(
        StockLedger(
            product_id=product_id,
            location_id=source_location_id,
            transaction_type="transfer_out",
            quantity_delta=-quantity,
            before_quantity=source_before,
            after_quantity=source.quantity,
            source_type="transfer_order",
            source_id=source_id,
            idempotency_key=f"{key}:transfer-item-{item_id}:out",
            operator_id=user_id,
        )
    )
    db.add(
        StockLedger(
            product_id=product_id,
            location_id=target_location_id,
            transaction_type="transfer_in",
            quantity_delta=quantity,
            before_quantity=target_before,
            after_quantity=target.quantity,
            source_type="transfer_order",
            source_id=source_id,
            idempotency_key=f"{key}:transfer-item-{item_id}:in",
            operator_id=user_id,
        )
    )
    write_audit(
        db,
        user_id=user_id,
        action="transfer_out",
        entity_type="stock_balance",
        entity_id=source.balance_id,
        quantity_before=source_before,
        quantity_after=source.quantity,
    )
    write_audit(
        db,
        user_id=user_id,
        action="transfer_in",
        entity_type="stock_balance",
        entity_id=target.balance_id,
        quantity_before=target_before,
        quantity_after=target.quantity,
    )
