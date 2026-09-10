from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.models import AuditLog, IdempotencyRecord, StockBalance, StockLedger


def require_idempotency_key(key: str | None) -> str:
    if not key or not key.strip():
        raise AppError("IDEMPOTENCY_KEY_REQUIRED", "写操作必须提供 Idempotency-Key", 400)
    return key.strip()


def existing_idempotent_response(db: Session, user_id: int, key: str) -> dict[str, Any] | None:
    row = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user_id, IdempotencyRecord.idempotency_key == key))
    return row.response_body if row is not None and row.response_body is not None else None


def record_idempotent_response(db: Session, *, user_id: int, key: str, path: str, body: dict[str, Any], status: int = 200) -> None:
    db.add(IdempotencyRecord(user_id=user_id, idempotency_key=key, request_method="POST", request_path=path, response_status=status, response_body=body))


def write_audit(db: Session, *, user_id: int, action: str, entity_type: str, entity_id: int | str, before: dict | None = None, after: dict | None = None, quantity_before: int | None = None, quantity_after: int | None = None) -> None:
    db.add(AuditLog(request_id="api", user_id=user_id, action=action, entity_type=entity_type, entity_id=str(entity_id), before_state=before, after_state=after, quantity_before=quantity_before, quantity_after=quantity_after))


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
