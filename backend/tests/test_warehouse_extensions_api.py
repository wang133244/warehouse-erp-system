from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.errors import AppError
from backend.app.core.security import hash_password
from backend.app.db.base import Base
from backend.app.db.models import (
    AuditLog,
    IdempotencyRecord,
    Product,
    Role,
    StockBalance,
    StockLedger,
    TransferItem,
    TransferOrder,
    UserAccount,
    UserRole,
    UserWarehouseScope,
    Warehouse,
    WarehouseLocation,
)
from backend.app.db.session import get_db
from backend.app.main import create_app


@dataclass(frozen=True)
class WarehouseEnvironment:
    client: TestClient
    session_factory: sessionmaker
    admin_user_id: int
    operator_user_id: int
    manager_one_user_id: int
    manager_two_user_id: int
    product_id: int


@pytest.fixture
def warehouse_environment() -> Generator[WarehouseEnvironment, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as db:
        admin_role = Role(role_code="admin", role_name="系统管理员")
        operator_role = Role(role_code="warehouse_operator", role_name="仓库操作员")
        manager_role = Role(role_code="warehouse_manager", role_name="仓库管理员")
        admin = UserAccount(
            username="admin",
            password_hash=hash_password("password"),
            display_name="管理员",
        )
        operator = UserAccount(
            username="warehouse_operator",
            password_hash=hash_password("password"),
            display_name="仓库操作员",
        )
        manager_one = UserAccount(
            username="manager_one",
            password_hash=hash_password("password"),
            display_name="一号仓管理员",
        )
        manager_two = UserAccount(
            username="manager_two",
            password_hash=hash_password("password"),
            display_name="二号仓管理员",
        )
        warehouse_one = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")
        warehouse_two = Warehouse(warehouse_code="WH-02", warehouse_name="二号仓")
        db.add_all(
            [
                admin_role,
                operator_role,
                manager_role,
                admin,
                operator,
                manager_one,
                manager_two,
                warehouse_one,
                warehouse_two,
            ]
        )
        db.flush()

        location_one = WarehouseLocation(
            warehouse_id=warehouse_one.warehouse_id,
            location_code="WH1-A-01",
            zone_code="A",
            aisle_code="01",
            rack_code="01",
            position_code="01",
        )
        location_two = WarehouseLocation(
            warehouse_id=warehouse_one.warehouse_id,
            location_code="WH1-A-02",
            zone_code="A",
            aisle_code="02",
            rack_code="01",
            position_code="01",
        )
        location_three = WarehouseLocation(
            warehouse_id=warehouse_two.warehouse_id,
            location_code="WH2-A-01",
            zone_code="A",
            aisle_code="01",
            rack_code="01",
            position_code="01",
        )
        product = Product(
            sku_code="SKU-EXT",
            source_product_code="SRC-EXT",
            brand="品牌",
            product_name="扩展商品",
            category="分类",
            size="标准",
            function_feature="普通",
            color="蓝色",
            pallet_spec="箱",
            pallet_capacity=10,
        )
        db.add_all([location_one, location_two, location_three, product])
        db.flush()

        db.add_all(
            [
                UserRole(user_id=admin.user_id, role_id=admin_role.role_id),
                UserRole(user_id=operator.user_id, role_id=operator_role.role_id),
                UserRole(user_id=manager_one.user_id, role_id=manager_role.role_id),
                UserRole(user_id=manager_two.user_id, role_id=manager_role.role_id),
                UserWarehouseScope(
                    user_id=operator.user_id,
                    warehouse_id=warehouse_one.warehouse_id,
                ),
                UserWarehouseScope(
                    user_id=manager_one.user_id,
                    warehouse_id=warehouse_one.warehouse_id,
                ),
                UserWarehouseScope(
                    user_id=manager_two.user_id,
                    warehouse_id=warehouse_two.warehouse_id,
                ),
                StockBalance(
                    product_id=product.product_id,
                    location_id=location_one.location_id,
                    quantity=10,
                    reserved_quantity=0,
                ),
                StockBalance(
                    product_id=product.product_id,
                    location_id=location_two.location_id,
                    quantity=0,
                    reserved_quantity=0,
                ),
                StockBalance(
                    product_id=product.product_id,
                    location_id=location_three.location_id,
                    quantity=5,
                    reserved_quantity=2,
                ),
            ]
        )

        transfer_order = TransferOrder(
            order_no="TR-EXT-001",
            status="executable",
            transfer_scope="same_warehouse",
            created_by=operator.user_id,
        )
        db.add(transfer_order)
        db.flush()
        db.add_all(
            [
                TransferItem(
                    transfer_order_id=transfer_order.transfer_order_id,
                    product_id=product.product_id,
                    source_location_id=location_one.location_id,
                    target_location_id=location_two.location_id,
                    quantity=2,
                ),
                TransferItem(
                    transfer_order_id=transfer_order.transfer_order_id,
                    product_id=product.product_id,
                    source_location_id=location_two.location_id,
                    target_location_id=location_one.location_id,
                    quantity=20,
                ),
            ]
        )
        db.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield WarehouseEnvironment(
            client=test_client,
            session_factory=session_factory,
            admin_user_id=admin.user_id,
            operator_user_id=operator.user_id,
            manager_one_user_id=manager_one.user_id,
            manager_two_user_id=manager_two.user_id,
            product_id=product.product_id,
        )


@pytest.fixture
def client(warehouse_environment: WarehouseEnvironment) -> TestClient:
    return warehouse_environment.client


def _headers(
    environment: WarehouseEnvironment,
    username: str,
    key: str | None = None,
) -> dict[str, str]:
    login = environment.client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "password"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def _admin_headers(
    environment: WarehouseEnvironment,
    key: str | None = None,
) -> dict[str, str]:
    return _headers(environment, "admin", key)


def _operator_headers(
    environment: WarehouseEnvironment,
    key: str | None = None,
) -> dict[str, str]:
    return _headers(environment, "warehouse_operator", key)


def _balances(environment: WarehouseEnvironment) -> list[tuple[int, int, int, int]]:
    with environment.session_factory() as db:
        return list(
            db.execute(
                select(
                    StockBalance.balance_id,
                    StockBalance.product_id,
                    StockBalance.location_id,
                    StockBalance.quantity,
                ).order_by(StockBalance.balance_id)
            )
        )


def _ledgers(environment: WarehouseEnvironment) -> list[tuple[int, ...]]:
    with environment.session_factory() as db:
        return list(
            db.execute(
                select(
                    StockLedger.ledger_id,
                    StockLedger.product_id,
                    StockLedger.location_id,
                    StockLedger.transaction_type,
                    StockLedger.quantity_delta,
                    StockLedger.before_quantity,
                    StockLedger.after_quantity,
                    StockLedger.source_type,
                    StockLedger.source_id,
                    StockLedger.idempotency_key,
                ).order_by(StockLedger.ledger_id)
            )
        )


def _audits(environment: WarehouseEnvironment) -> list[tuple[int, ...]]:
    with environment.session_factory() as db:
        return list(
            db.execute(
                select(
                    AuditLog.audit_log_id,
                    AuditLog.user_id,
                    AuditLog.action,
                    AuditLog.entity_type,
                    AuditLog.entity_id,
                    AuditLog.quantity_before,
                    AuditLog.quantity_after,
                ).order_by(AuditLog.audit_log_id)
            )
        )


@pytest.mark.xfail(reason="stock-count routes are implemented in a later task", strict=False)
def test_replayed_create_returns_original_created_status(
    warehouse_environment: WarehouseEnvironment,
) -> None:
    headers = _admin_headers(warehouse_environment, "count-create-key")
    first = warehouse_environment.client.post(
        "/api/v1/stock-counts",
        headers=headers,
        json={"items": []},
    )
    replay = warehouse_environment.client.post(
        "/api/v1/stock-counts",
        headers=headers,
        json={"items": []},
    )
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()


@pytest.mark.xfail(reason="stock-count routes are implemented in a later task", strict=False)
def test_warehouse_scope_rejects_operator_outside_scope(
    warehouse_environment: WarehouseEnvironment,
) -> None:
    response = warehouse_environment.client.post(
        "/api/v1/stock-counts",
        headers=_operator_headers(warehouse_environment, "out-of-scope"),
        json={"items": [{"product_id": 1, "location_id": 3, "counted_quantity": 4}]},
    )
    assert response.status_code == 403


@pytest.mark.xfail(reason="transfer routes are implemented in a later task", strict=False)
def test_transfer_insufficient_stock_rolls_back_every_line(
    warehouse_environment: WarehouseEnvironment,
) -> None:
    before_balances = _balances(warehouse_environment)
    before_ledgers = _ledgers(warehouse_environment)
    response = warehouse_environment.client.post(
        "/api/v1/transfers/1/execute",
        headers=_operator_headers(warehouse_environment, "transfer-execute"),
    )
    assert response.status_code == 409
    assert _balances(warehouse_environment) == before_balances
    assert _ledgers(warehouse_environment) == before_ledgers


def test_service_result_replays_original_status_and_body(
    warehouse_environment: WarehouseEnvironment,
) -> None:
    from backend.app.services.inventory_service import (
        ServiceResult,
        existing_idempotent_response,
        record_idempotent_response,
        replay_result,
    )

    body = {"stock_count_order_id": 1, "status": "draft"}
    with warehouse_environment.session_factory() as db:
        record_idempotent_response(
            db,
            user_id=warehouse_environment.admin_user_id,
            key="shared-replay-key",
            method="POST",
            path="/api/v1/stock-counts",
            body=body,
            status=201,
        )
        db.commit()

    with warehouse_environment.session_factory() as db:
        result = replay_result(
            db,
            warehouse_environment.admin_user_id,
            "shared-replay-key",
        )
        assert result == ServiceResult(body, 201, True)
        assert existing_idempotent_response(
            db,
            warehouse_environment.admin_user_id,
            "shared-replay-key",
        ) == body
        assert replay_result(db, warehouse_environment.admin_user_id, "missing") is None
        row = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == "shared-replay-key"
            )
        )
        assert row is not None
        assert row.request_method == "POST"


def test_role_and_warehouse_scope_semantics(
    warehouse_environment: WarehouseEnvironment,
) -> None:
    from backend.app.dependencies import ensure_warehouse_scope, get_current_user_roles

    with warehouse_environment.session_factory() as db:
        admin_roles = get_current_user_roles(db, warehouse_environment.admin_user_id)
        operator_roles = get_current_user_roles(
            db,
            warehouse_environment.operator_user_id,
        )
        manager_one_roles = get_current_user_roles(
            db,
            warehouse_environment.manager_one_user_id,
        )
        manager_two_roles = get_current_user_roles(
            db,
            warehouse_environment.manager_two_user_id,
        )
        assert admin_roles == {"admin"}
        assert operator_roles == {"warehouse_operator"}
        assert manager_one_roles == {"warehouse_manager"}
        assert manager_two_roles == {"warehouse_manager"}

        ensure_warehouse_scope(db, warehouse_environment.admin_user_id, admin_roles, {1, 2})
        ensure_warehouse_scope(
            db,
            warehouse_environment.operator_user_id,
            operator_roles,
            {1},
        )
        ensure_warehouse_scope(
            db,
            warehouse_environment.manager_two_user_id,
            manager_two_roles,
            {2},
        )

        with pytest.raises(AppError) as exc_info:
            ensure_warehouse_scope(
                db,
                warehouse_environment.operator_user_id,
                operator_roles,
                {1, 2},
            )
        assert exc_info.value.code == "WAREHOUSE_SCOPE_FORBIDDEN"
        assert exc_info.value.status_code == 403


def test_apply_count_adjustment_writes_ledger_and_audit_without_commit(
    warehouse_environment: WarehouseEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.services.inventory_service import apply_count_adjustment

    with warehouse_environment.session_factory() as db:
        monkeypatch.setattr(
            db,
            "commit",
            lambda: pytest.fail("count adjustment must not commit"),
        )
        apply_count_adjustment(
            db,
            product_id=warehouse_environment.product_id,
            location_id=1,
            target_quantity=12,
            source_id=1,
            item_id=1,
            key="count-approve",
            user_id=warehouse_environment.operator_user_id,
        )
        db.flush()

        balance = db.scalar(
            select(StockBalance).where(
                StockBalance.product_id == warehouse_environment.product_id,
                StockBalance.location_id == 1,
            )
        )
        assert balance is not None
        assert balance.quantity == 12
        ledger = db.scalar(
            select(StockLedger).where(
                StockLedger.idempotency_key == "count-approve:stock-count-item-1:apply"
            )
        )
        assert ledger is not None
        assert ledger.transaction_type == "count_gain"
        assert ledger.quantity_delta == 2
        assert ledger.before_quantity == 10
        assert ledger.after_quantity == 12
        assert ledger.source_type == "stock_count_order"
        assert ledger.source_id == 1
        assert ledger.operator_id == warehouse_environment.operator_user_id

        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "stock_count_apply",
                AuditLog.entity_type == "stock_balance",
                AuditLog.entity_id == str(balance.balance_id),
            )
        )
        assert audit is not None
        assert audit.quantity_before == 10
        assert audit.quantity_after == 12

        db.rollback()

    with warehouse_environment.session_factory() as db:
        balance = db.scalar(
            select(StockBalance).where(
                StockBalance.product_id == warehouse_environment.product_id,
                StockBalance.location_id == 1,
            )
        )
        assert balance is not None
        assert balance.quantity == 10
        assert db.scalar(select(StockLedger)) is None
        assert db.scalar(select(AuditLog)) is None


def test_execute_transfer_line_moves_stock_and_writes_paired_ledgers(
    warehouse_environment: WarehouseEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.services.inventory_service import execute_transfer_line

    with warehouse_environment.session_factory() as db:
        monkeypatch.setattr(
            db,
            "commit",
            lambda: pytest.fail("transfer line must not commit"),
        )
        execute_transfer_line(
            db,
            product_id=warehouse_environment.product_id,
            source_location_id=1,
            target_location_id=2,
            quantity=3,
            source_id=1,
            item_id=1,
            key="transfer-execute",
            user_id=warehouse_environment.operator_user_id,
        )
        db.flush()

        source = db.scalar(
            select(StockBalance).where(
                StockBalance.product_id == warehouse_environment.product_id,
                StockBalance.location_id == 1,
            )
        )
        target = db.scalar(
            select(StockBalance).where(
                StockBalance.product_id == warehouse_environment.product_id,
                StockBalance.location_id == 2,
            )
        )
        assert source is not None
        assert target is not None
        assert source.quantity == 7
        assert target.quantity == 3

        out_ledger = db.scalar(
            select(StockLedger).where(
                StockLedger.idempotency_key == "transfer-execute:transfer-item-1:out"
            )
        )
        in_ledger = db.scalar(
            select(StockLedger).where(
                StockLedger.idempotency_key == "transfer-execute:transfer-item-1:in"
            )
        )
        assert out_ledger is not None
        assert in_ledger is not None
        assert out_ledger.transaction_type == "transfer_out"
        assert in_ledger.transaction_type == "transfer_in"
        assert out_ledger.quantity_delta == -3
        assert in_ledger.quantity_delta == 3
        assert (out_ledger.before_quantity, out_ledger.after_quantity) == (10, 7)
        assert (in_ledger.before_quantity, in_ledger.after_quantity) == (0, 3)
        assert out_ledger.source_type == in_ledger.source_type == "transfer_order"
        assert out_ledger.source_id == in_ledger.source_id == 1
        assert out_ledger.operator_id == in_ledger.operator_id

        audits = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.action.in_(("transfer_out", "transfer_in")),
                ).order_by(AuditLog.action)
            )
        )
        assert [
            (audit.action, audit.quantity_before, audit.quantity_after)
            for audit in audits
        ] == [
            ("transfer_in", 0, 3),
            ("transfer_out", 10, 7),
        ]

        db.rollback()

    with warehouse_environment.session_factory() as db:
        assert db.scalar(select(StockLedger)) is None
        assert db.scalar(select(AuditLog)) is None


def test_transfer_insufficient_stock_rolls_back_shared_primitive_lines(
    warehouse_environment: WarehouseEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.services.inventory_service import execute_transfer_line

    before_balances = _balances(warehouse_environment)
    before_ledgers = _ledgers(warehouse_environment)
    before_audits = _audits(warehouse_environment)

    with warehouse_environment.session_factory() as db:
        monkeypatch.setattr(
            db,
            "commit",
            lambda: pytest.fail("transfer line must not commit"),
        )
        execute_transfer_line(
            db,
            product_id=warehouse_environment.product_id,
            source_location_id=1,
            target_location_id=2,
            quantity=2,
            source_id=1,
            item_id=1,
            key="transfer-failure",
            user_id=warehouse_environment.operator_user_id,
        )
        db.flush()

        with pytest.raises(AppError) as exc_info:
            execute_transfer_line(
                db,
                product_id=warehouse_environment.product_id,
                source_location_id=2,
                target_location_id=1,
                quantity=20,
                source_id=1,
                item_id=2,
                key="transfer-failure",
                user_id=warehouse_environment.operator_user_id,
            )
        assert exc_info.value.code == "INVENTORY_INSUFFICIENT"
        assert exc_info.value.status_code == 409

        db.rollback()

    assert _balances(warehouse_environment) == before_balances
    assert _ledgers(warehouse_environment) == before_ledgers
    assert _audits(warehouse_environment) == before_audits
