from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.models import (
    ApprovalTask,
    Product,
    StockBalance,
    StockCountItem,
    StockCountOrder,
    WarehouseLocation,
)
from backend.app.dependencies import ensure_warehouse_scope
from backend.app.schemas.stock_counts import StockCountUpsert
from backend.app.services.inventory_service import (
    ServiceResult,
    apply_count_adjustment,
    record_idempotent_response,
    replay_result,
    require_idempotency_key,
    write_audit,
)


def _item_contexts(
    db: Session,
    payload: StockCountUpsert,
    *,
    user_id: int,
    roles: set[str],
) -> list[tuple[int, int, int, int]]:
    contexts: list[tuple[int, int, int, int]] = []
    warehouse_ids: set[int] = set()
    for item in payload.items:
        product = db.get(Product, item.product_id)
        location = db.get(WarehouseLocation, item.location_id)
        if product is None:
            raise AppError(
                "PRODUCT_NOT_FOUND",
                "商品不存在",
                404,
                {"product_id": item.product_id},
            )
        if location is None:
            raise AppError(
                "WAREHOUSE_LOCATION_NOT_FOUND",
                "库位不存在",
                404,
                {"location_id": item.location_id},
            )
        warehouse_ids.add(location.warehouse_id)
        contexts.append(
            (item.product_id, item.location_id, item.counted_quantity, location.warehouse_id)
        )
    ensure_warehouse_scope(db, user_id, roles, warehouse_ids)
    return contexts


def _warehouse_ids_for_items(db: Session, items: list[StockCountItem]) -> set[int]:
    warehouse_ids: set[int] = set()
    for item in items:
        location = db.get(WarehouseLocation, item.location_id)
        if location is not None:
            warehouse_ids.add(location.warehouse_id)
    return warehouse_ids


def _create_order(db: Session, *, user_id: int, note: str | None, status: str) -> StockCountOrder:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    order = StockCountOrder(
        order_no=f"SC-{date_part}-TEMP",
        status=status,
        created_by=user_id,
        note=note,
    )
    db.add(order)
    db.flush()
    order.order_no = f"SC-{date_part}-{order.stock_count_order_id:06d}"
    db.flush()
    return order


def _serialize_order(
    db: Session,
    order: StockCountOrder,
    *,
    include_items: bool = True,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "stock_count_order_id": order.stock_count_order_id,
        "order_no": order.order_no,
        "status": order.status,
        "created_by": order.created_by,
        "submitted_by": order.submitted_by,
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        "completed_by": order.completed_by,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "note": order.note,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }
    if include_items:
        items = list(
            db.scalars(
                select(StockCountItem)
                .where(StockCountItem.stock_count_order_id == order.stock_count_order_id)
                .order_by(StockCountItem.stock_count_item_id)
            )
        )
        body["items"] = [
            {
                "stock_count_item_id": item.stock_count_item_id,
                "product_id": item.product_id,
                "location_id": item.location_id,
                "book_quantity": item.book_quantity,
                "counted_quantity": item.counted_quantity,
                "variance_quantity": item.variance_quantity,
            }
            for item in items
        ]
        approval = db.scalar(
            select(ApprovalTask).where(
                ApprovalTask.business_type == "stock_count",
                ApprovalTask.business_id == order.stock_count_order_id,
            )
        )
        if approval is not None:
            body["approval_summary"] = {
                "approval_task_id": approval.approval_task_id,
                "business_type": approval.business_type,
                "business_id": approval.business_id,
                "status": approval.status,
                "requested_by": approval.requested_by,
                "requested_at": approval.requested_at.isoformat()
                if approval.requested_at
                else None,
                "decided_by": approval.decided_by,
                "decided_at": approval.decided_at.isoformat()
                if approval.decided_at
                else None,
                "comment": approval.comment,
            }
        else:
            body["approval_summary"] = None
    return body


def create_stock_count(
    db: Session,
    *,
    payload: StockCountUpsert,
    user_id: int,
    roles: set[str],
    key: str | None,
    request_id: str = "api",
) -> ServiceResult:
    key = require_idempotency_key(key)
    prior = replay_result(db, user_id, key)
    if prior is not None:
        return prior

    contexts = _item_contexts(db, payload, user_id=user_id, roles=roles)
    status = "counting" if contexts else "draft"
    order = _create_order(db, user_id=user_id, note=payload.note, status=status)
    db.add_all(
        [
            StockCountItem(
                stock_count_order_id=order.stock_count_order_id,
                product_id=product_id,
                location_id=location_id,
                counted_quantity=counted_quantity,
            )
            for product_id, location_id, counted_quantity, _warehouse_id in contexts
        ]
    )
    db.flush()
    body = _serialize_order(db, order)
    record_idempotent_response(
        db,
        user_id=user_id,
        key=key,
        method="POST",
        path="/api/v1/stock-counts",
        body=body,
        status=201,
    )
    write_audit(
        db,
        user_id=user_id,
        action="stock_count_create",
        entity_type="stock_count_order",
        entity_id=order.stock_count_order_id,
        after=body,
        request_id=request_id,
    )
    db.commit()
    return ServiceResult(body, 201)


def update_stock_count(
    db: Session,
    *,
    count_id: int,
    payload: StockCountUpsert,
    user_id: int,
    roles: set[str],
    key: str | None,
    request_id: str = "api",
) -> ServiceResult:
    key = require_idempotency_key(key)
    prior = replay_result(db, user_id, key)
    if prior is not None:
        return prior

    order = db.get(StockCountOrder, count_id)
    if order is None:
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)
    if order.status not in ("draft", "counting"):
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可编辑", 409)
    if order.created_by != user_id and "admin" not in roles:
        raise AppError("STOCK_COUNT_FORBIDDEN", "只能编辑自己创建的盘点单", 403)

    contexts = _item_contexts(db, payload, user_id=user_id, roles=roles)
    db.execute(
        delete(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)
    )
    db.add_all(
        [
            StockCountItem(
                stock_count_order_id=count_id,
                product_id=product_id,
                location_id=location_id,
                counted_quantity=counted_quantity,
            )
            for product_id, location_id, counted_quantity, _warehouse_id in contexts
        ]
    )
    order.note = payload.note
    order.status = "counting" if contexts else "draft"
    db.flush()
    body = _serialize_order(db, order)
    record_idempotent_response(
        db,
        user_id=user_id,
        key=key,
        method="PUT",
        path=f"/api/v1/stock-counts/{count_id}",
        body=body,
        status=200,
    )
    write_audit(
        db,
        user_id=user_id,
        action="stock_count_update",
        entity_type="stock_count_order",
        entity_id=count_id,
        after=body,
        request_id=request_id,
    )
    db.commit()
    return ServiceResult(body, 200)


def submit_stock_count(
    db: Session,
    *,
    count_id: int,
    user_id: int,
    roles: set[str],
    key: str | None,
    request_id: str = "api",
) -> ServiceResult:
    key = require_idempotency_key(key)
    prior = replay_result(db, user_id, key)
    if prior is not None:
        return prior

    order = db.get(StockCountOrder, count_id)
    if order is None:
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)
    items = list(
        db.scalars(
            select(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)
        )
    )
    if not items:
        raise AppError("COUNT_ITEMS_REQUIRED", "盘点明细不能为空", 422)
    if order.status != "counting":
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可提交", 409)

    ensure_warehouse_scope(
        db,
        user_id,
        roles,
        _warehouse_ids_for_items(db, items),
    )
    now = datetime.now(UTC)
    order.submitted_by = user_id
    order.submitted_at = now

    variances: list[int] = []
    for item in items:
        balance = db.scalar(
            select(StockBalance)
            .where(
                StockBalance.product_id == item.product_id,
                StockBalance.location_id == item.location_id,
            )
            .with_for_update()
        )
        book_quantity = balance.quantity if balance is not None else 0
        item.book_quantity = book_quantity
        item.variance_quantity = item.counted_quantity - book_quantity
        variances.append(item.variance_quantity)
    db.flush()

    if all(variance == 0 for variance in variances):
        order.status = "completed"
        order.completed_by = user_id
        order.completed_at = now
    else:
        order.status = "pending_approval"
        db.add(
            ApprovalTask(
                business_type="stock_count",
                business_id=count_id,
                status="pending",
                requested_by=user_id,
                requested_at=now,
            )
        )
        db.flush()

    body = _serialize_order(db, order)
    record_idempotent_response(
        db,
        user_id=user_id,
        key=key,
        method="POST",
        path=f"/api/v1/stock-counts/{count_id}/submit",
        body=body,
        status=200,
    )
    write_audit(
        db,
        user_id=user_id,
        action="stock_count_submit",
        entity_type="stock_count_order",
        entity_id=count_id,
        after=body,
        request_id=request_id,
    )
    db.commit()
    return ServiceResult(body, 200)


def approve_stock_count(
    db: Session,
    *,
    count_id: int,
    user_id: int,
    key: str | None,
    request_id: str = "api",
    path: str = "/api/v1/stock-counts/{count_id}/approve",
) -> ServiceResult:
    key = require_idempotency_key(key)
    prior = replay_result(db, user_id, key)
    if prior is not None:
        return prior

    order = db.get(StockCountOrder, count_id)
    if order is None:
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)
    if order.status != "pending_approval":
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可审批", 409)

    items = list(
        db.scalars(
            select(StockCountItem).where(StockCountItem.stock_count_order_id == count_id)
        )
    )
    for item in items:
        apply_count_adjustment(
            db,
            product_id=item.product_id,
            location_id=item.location_id,
            target_quantity=item.counted_quantity,
            source_id=count_id,
            item_id=item.stock_count_item_id,
            key=key,
            user_id=user_id,
            request_id=request_id,
        )

    now = datetime.now(UTC)
    order.status = "applied"
    order.completed_by = user_id
    order.completed_at = now
    db.flush()
    body = _serialize_order(db, order)
    record_idempotent_response(
        db,
        user_id=user_id,
        key=key,
        method="POST",
        path=path.format(count_id=count_id),
        body=body,
        status=200,
    )
    write_audit(
        db,
        user_id=user_id,
        action="stock_count_approve",
        entity_type="stock_count_order",
        entity_id=count_id,
        after=body,
        request_id=request_id,
    )
    db.commit()
    return ServiceResult(body, 200)


def reject_stock_count(
    db: Session,
    *,
    count_id: int,
    user_id: int,
    key: str | None,
    comment: str | None = None,
    request_id: str = "api",
    path: str = "/api/v1/stock-counts/{count_id}/reject",
) -> ServiceResult:
    key = require_idempotency_key(key)
    prior = replay_result(db, user_id, key)
    if prior is not None:
        return prior

    order = db.get(StockCountOrder, count_id)
    if order is None:
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)
    if order.status != "pending_approval":
        raise AppError("STOCK_COUNT_STATE_INVALID", "当前盘点单不可驳回", 409)

    order.status = "rejected"
    db.flush()
    body = _serialize_order(db, order)
    record_idempotent_response(
        db,
        user_id=user_id,
        key=key,
        method="POST",
        path=path.format(count_id=count_id),
        body=body,
        status=200,
    )
    write_audit(
        db,
        user_id=user_id,
        action="stock_count_reject",
        entity_type="stock_count_order",
        entity_id=count_id,
        after=body,
        request_id=request_id,
    )
    db.commit()
    return ServiceResult(body, 200)


def list_stock_counts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    order_no: str | None = None,
) -> dict[str, Any]:
    statement = select(StockCountOrder).order_by(StockCountOrder.stock_count_order_id.desc())
    count_statement = select(func.count()).select_from(StockCountOrder)
    if status:
        statement = statement.where(StockCountOrder.status == status)
        count_statement = count_statement.where(StockCountOrder.status == status)
    if order_no:
        statement = statement.where(StockCountOrder.order_no.ilike(f"%{order_no}%"))
        count_statement = count_statement.where(StockCountOrder.order_no.ilike(f"%{order_no}%"))

    total = int(db.scalar(count_statement) or 0)
    rows = list(
        db.scalars(
            statement.limit(page_size).offset((page - 1) * page_size)
        )
    )
    return {
        "items": [_serialize_order(db, row, include_items=False) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_stock_count(db: Session, count_id: int) -> dict[str, Any]:
    order = db.get(StockCountOrder, count_id)
    if order is None:
        raise AppError("STOCK_COUNT_NOT_FOUND", "盘点单不存在", 404)
    return _serialize_order(db, order)
