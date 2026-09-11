from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from backend.app.db.models import UserAccount
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, get_current_user_roles, require_roles
from backend.app.schemas.stock_counts import StockCountUpsert
from backend.app.services.stock_count_service import (
    create_stock_count,
    get_stock_count,
    list_stock_counts,
    submit_stock_count,
    update_stock_count,
)


router = APIRouter(prefix="/stock-counts", tags=["盘点"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "api")


@router.get("")
def list_orders(
    _: Annotated[UserAccount, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = Query(default=None, max_length=32),
    order_no: str | None = Query(default=None, max_length=64),
) -> dict:
    return list_stock_counts(
        db,
        page=page,
        page_size=page_size,
        status=status,
        order_no=order_no,
    )


@router.post("")
def create(
    payload: StockCountUpsert,
    request: Request,
    response: Response,
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    roles = get_current_user_roles(db, current_user.user_id)
    result = create_stock_count(
        db,
        payload=payload,
        user_id=current_user.user_id,
        roles=roles,
        key=idempotency_key,
        request_id=_request_id(request),
    )
    response.status_code = result.status_code
    return result.body


@router.get("/{count_id}")
def get_order(
    count_id: int,
    _: Annotated[UserAccount, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return get_stock_count(db, count_id)


@router.put("/{count_id}")
def update(
    count_id: int,
    payload: StockCountUpsert,
    request: Request,
    response: Response,
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    roles = get_current_user_roles(db, current_user.user_id)
    result = update_stock_count(
        db,
        count_id=count_id,
        payload=payload,
        user_id=current_user.user_id,
        roles=roles,
        key=idempotency_key,
        request_id=_request_id(request),
    )
    response.status_code = result.status_code
    return result.body


@router.post("/{count_id}/submit")
def submit(
    count_id: int,
    request: Request,
    response: Response,
    current_user: Annotated[UserAccount, Depends(require_roles("admin", "warehouse_operator"))],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    roles = get_current_user_roles(db, current_user.user_id)
    result = submit_stock_count(
        db,
        count_id=count_id,
        user_id=current_user.user_id,
        roles=roles,
        key=idempotency_key,
        request_id=_request_id(request),
    )
    response.status_code = result.status_code
    return result.body
