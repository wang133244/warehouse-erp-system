"""库位地图与主数据写入。"""

from collections.abc import Generator  # from collections.abc imp
from dataclasses import dataclass  # from dataclasses import 

import pytest  # import pytest
from fastapi.testclient import TestClient  # from fastapi.testclient 
from sqlalchemy import create_engine, select  # from sqlalchemy import c
from sqlalchemy.orm import Session, sessionmaker  # from sqlalchemy.orm impo
from sqlalchemy.pool import StaticPool  # from sqlalchemy.pool imp

from backend.app.core.errors import AppError  # from backend.app.core.er
from backend.app.core.security import hash_password  # from backend.app.core.se
from backend.app.db.base import Base  # from backend.app.db.base
from backend.app.models import (  # from backend.app.models 
    ApprovalTask,  # ApprovalTask,
    AuditLog,  # AuditLog,
    IdempotencyRecord,  # IdempotencyRecord,
    Product,  # Product,
    Role,  # Role,
    StockBalance,  # StockBalance,
    StockCountItem,  # StockCountItem,
    StockCountOrder,  # StockCountOrder,
    StockLedger,  # StockLedger,
    TransferItem,  # TransferItem,
    TransferOrder,  # TransferOrder,
    UserAccount,  # UserAccount,
    UserRole,  # UserRole,
    UserWarehouseScope,  # UserWarehouseScope,
    Warehouse,  # Warehouse,
    WarehouseLocation,  # WarehouseLocation,
)  # )
from backend.app.db.session import get_db  # from backend.app.db.sess
from backend.app.main import create_app  # from backend.app.main im


@dataclass(frozen=True)  # @dataclass(frozen=True)
class WarehouseEnvironment:  # class WarehouseEnvironme
    client: TestClient  # client: TestClient
    session_factory: sessionmaker  # session_factory: session
    admin_user_id: int  # admin_user_id: int
    operator_user_id: int  # operator_user_id: int
    operator_two_user_id: int  # operator_two_user_id: in
    manager_one_user_id: int  # manager_one_user_id: int
    manager_two_user_id: int  # manager_two_user_id: int
    product_id: int  # product_id: int


@pytest.fixture  # @pytest.fixture
def warehouse_environment() -> Generator[WarehouseEnvironment, None, None]:  # def warehouse_environmen
    engine = create_engine(  # engine = create_engine(
        "sqlite+pysqlite:///:memory:",  # 'sqlite+pysqlite:///:mem
        connect_args={"check_same_thread": False},  # connect_args={'check_sam
        poolclass=StaticPool,  # poolclass=StaticPool,
    )  # )
    Base.metadata.create_all(engine)  # Base.metadata.create_all
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)  # session_factory = sessio

    with session_factory() as db:  # with session_factory() a
        admin_role = Role(role_code="admin", role_name="系统管理员")  # admin_role = Role(role_c
        operator_role = Role(role_code="warehouse_operator", role_name="仓库操作员")  # operator_role = Role(rol
        manager_role = Role(role_code="warehouse_manager", role_name="仓库管理员")  # manager_role = Role(role
        admin = UserAccount(  # admin = UserAccount(
            username="admin",  # username='admin',
            password_hash=hash_password("password"),  # password_hash=hash_passw
            display_name="管理员",  # display_name='管理员',
        )  # )
        operator = UserAccount(  # operator = UserAccount(
            username="warehouse_operator",  # username='warehouse_oper
            password_hash=hash_password("password"),  # password_hash=hash_passw
            display_name="仓库操作员",  # display_name='仓库操作员',
        )  # )
        operator_two = UserAccount(  # operator_two = UserAccou
            username="warehouse_operator_two",  # username='warehouse_oper
            password_hash=hash_password("password"),  # password_hash=hash_passw
            display_name="二号操作员",  # display_name='二号操作员',
        )  # )
        manager_one = UserAccount(  # manager_one = UserAccoun
            username="manager_one",  # username='manager_one',
            password_hash=hash_password("password"),  # password_hash=hash_passw
            display_name="一号仓管理员",  # display_name='一号仓管理员',
        )  # )
        manager_two = UserAccount(  # manager_two = UserAccoun
            username="manager_two",  # username='manager_two',
            password_hash=hash_password("password"),  # password_hash=hash_passw
            display_name="二号仓管理员",  # display_name='二号仓管理员',
        )  # )
        warehouse_one = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")  # warehouse_one = Warehous
        warehouse_two = Warehouse(warehouse_code="WH-02", warehouse_name="二号仓")  # warehouse_two = Warehous
        db.add_all(  # db.add_all(
            [  # [
                admin_role,  # admin_role,
                operator_role,  # operator_role,
                manager_role,  # manager_role,
                admin,  # admin,
                operator,  # operator,
                operator_two,  # operator_two,
                manager_one,  # manager_one,
                manager_two,  # manager_two,
                warehouse_one,  # warehouse_one,
                warehouse_two,  # warehouse_two,
            ]  # ]
        )  # )
        db.flush()  # db.flush()

        location_one = WarehouseLocation(  # location_one = Warehouse
            warehouse_id=warehouse_one.warehouse_id,  # warehouse_id=warehouse_o
            location_code="WH1-A-01",  # location_code='WH1-A-01'
            zone_code="A",  # zone_code='A',
            aisle_code="01",  # aisle_code='01',
            rack_code="01",  # rack_code='01',
            position_code="01",  # position_code='01',
        )  # )
        location_two = WarehouseLocation(  # location_two = Warehouse
            warehouse_id=warehouse_one.warehouse_id,  # warehouse_id=warehouse_o
            location_code="WH1-A-02",  # location_code='WH1-A-02'
            zone_code="A",  # zone_code='A',
            aisle_code="02",  # aisle_code='02',
            rack_code="01",  # rack_code='01',
            position_code="01",  # position_code='01',
        )  # )
        location_three = WarehouseLocation(  # location_three = Warehou
            warehouse_id=warehouse_two.warehouse_id,  # warehouse_id=warehouse_t
            location_code="WH2-A-01",  # location_code='WH2-A-01'
            zone_code="A",  # zone_code='A',
            aisle_code="01",  # aisle_code='01',
            rack_code="01",  # rack_code='01',
            position_code="01",  # position_code='01',
        )  # )
        product = Product(  # product = Product(
            sku_code="SKU-EXT",  # sku_code='SKU-EXT',
            source_product_code="SRC-EXT",  # source_product_code='SRC
            brand="品牌",  # brand='品牌',
            product_name="扩展商品",  # product_name='扩展商品',
            category="分类",  # category='分类',
            size="标准",  # size='标准',
            function_feature="普通",  # function_feature='普通',
            color="蓝色",  # color='蓝色',
            pallet_spec="箱",  # pallet_spec='箱',
            pallet_capacity=10,  # pallet_capacity=10,
        )  # )
        db.add_all([location_one, location_two, location_three, product])  # db.add_all([location_one
        db.flush()  # db.flush()

        db.add_all(  # db.add_all(
            [  # [
                UserRole(user_id=admin.user_id, role_id=admin_role.role_id),  # UserRole(user_id=admin.u
                UserRole(user_id=operator.user_id, role_id=operator_role.role_id),  # UserRole(user_id=operato
                UserRole(user_id=operator_two.user_id, role_id=operator_role.role_id),  # UserRole(user_id=operato
                UserRole(user_id=manager_one.user_id, role_id=manager_role.role_id),  # UserRole(user_id=manager
                UserRole(user_id=manager_two.user_id, role_id=manager_role.role_id),  # UserRole(user_id=manager
                UserWarehouseScope(  # UserWarehouseScope(
                    user_id=operator.user_id,  # user_id=operator.user_id
                    warehouse_id=warehouse_one.warehouse_id,  # warehouse_id=warehouse_o
                ),  # ),
                UserWarehouseScope(  # UserWarehouseScope(
                    user_id=operator_two.user_id,  # user_id=operator_two.use
                    warehouse_id=warehouse_one.warehouse_id,  # warehouse_id=warehouse_o
                ),  # ),
                UserWarehouseScope(  # UserWarehouseScope(
                    user_id=manager_one.user_id,  # user_id=manager_one.user
                    warehouse_id=warehouse_one.warehouse_id,  # warehouse_id=warehouse_o
                ),  # ),
                UserWarehouseScope(  # UserWarehouseScope(
                    user_id=manager_one.user_id,  # user_id=manager_one.user
                    warehouse_id=warehouse_two.warehouse_id,  # warehouse_id=warehouse_t
                ),  # ),
                UserWarehouseScope(  # UserWarehouseScope(
                    user_id=manager_two.user_id,  # user_id=manager_two.user
                    warehouse_id=warehouse_two.warehouse_id,  # warehouse_id=warehouse_t
                ),  # ),
                StockBalance(  # StockBalance(
                    product_id=product.product_id,  # product_id=product.produ
                    location_id=location_one.location_id,  # location_id=location_one
                    quantity=10,  # quantity=10,
                    reserved_quantity=0,  # reserved_quantity=0,
                ),  # ),
                StockBalance(  # StockBalance(
                    product_id=product.product_id,  # product_id=product.produ
                    location_id=location_two.location_id,  # location_id=location_two
                    quantity=0,  # quantity=0,
                    reserved_quantity=0,  # reserved_quantity=0,
                ),  # ),
                StockBalance(  # StockBalance(
                    product_id=product.product_id,  # product_id=product.produ
                    location_id=location_three.location_id,  # location_id=location_thr
                    quantity=5,  # quantity=5,
                    reserved_quantity=2,  # reserved_quantity=2,
                ),  # ),
            ]  # ]
        )  # )

        transfer_order = TransferOrder(  # transfer_order = Transfe
            order_no="TR-EXT-001",  # order_no='TR-EXT-001',
            status="executable",  # status='executable',
            transfer_scope="same_warehouse",  # transfer_scope='same_war
            created_by=operator.user_id,  # created_by=operator.user
        )  # )
        db.add(transfer_order)  # db.add(transfer_order)
        db.flush()  # db.flush()
        db.add_all(  # db.add_all(
            [  # [
                TransferItem(  # TransferItem(
                    transfer_order_id=transfer_order.transfer_order_id,  # transfer_order_id=transf
                    product_id=product.product_id,  # product_id=product.produ
                    source_location_id=location_one.location_id,  # source_location_id=locat
                    target_location_id=location_two.location_id,  # target_location_id=locat
                    quantity=2,  # quantity=2,
                ),  # ),
                TransferItem(  # TransferItem(
                    transfer_order_id=transfer_order.transfer_order_id,  # transfer_order_id=transf
                    product_id=product.product_id,  # product_id=product.produ
                    source_location_id=location_two.location_id,  # source_location_id=locat
                    target_location_id=location_one.location_id,  # target_location_id=locat
                    quantity=20,  # quantity=20,
                ),  # ),
            ]  # ]
        )  # )
        db.commit()  # db.commit()

    app = create_app()  # app = create_app()

    def override_get_db() -> Generator[Session, None, None]:  # def override_get_db() ->
        with session_factory() as db:  # with session_factory() a
            yield db  # yield db

    app.dependency_overrides[get_db] = override_get_db  # app.dependency_overrides
    with TestClient(app) as test_client:  # with TestClient(app) as 
        yield WarehouseEnvironment(  # yield WarehouseEnvironme
            client=test_client,  # client=test_client,
            session_factory=session_factory,  # session_factory=session_
            admin_user_id=admin.user_id,  # admin_user_id=admin.user
            operator_user_id=operator.user_id,  # operator_user_id=operato
            operator_two_user_id=operator_two.user_id,  # operator_two_user_id=ope
            manager_one_user_id=manager_one.user_id,  # manager_one_user_id=mana
            manager_two_user_id=manager_two.user_id,  # manager_two_user_id=mana
            product_id=product.product_id,  # product_id=product.produ
        )  # )


@pytest.fixture  # @pytest.fixture
def client(warehouse_environment: WarehouseEnvironment) -> TestClient:  # def client(warehouse_env
    return warehouse_environment.client  # return warehouse_environ


def _headers(  # def _headers(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    username: str,  # username: str,
    key: str | None = None,  # key: str | None = None,
) -> dict[str, str]:  # ) -> dict[str, str]:
    login = environment.client.post(  # login = environment.clie
        "/api/v1/auth/login",  # '/api/v1/auth/login',
        json={"username": username, "password": "password"},  # json={'username': userna
    )  # )
    assert login.status_code == 200  # assert login.status_code
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}  # headers = {'Authorizatio
    if key:  # if key:
        headers["Idempotency-Key"] = key  # headers['Idempotency-Key
    return headers  # return headers


def _admin_headers(  # def _admin_headers(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    key: str | None = None,  # key: str | None = None,
) -> dict[str, str]:  # ) -> dict[str, str]:
    return _headers(environment, "admin", key)  # return _headers(environm


def _operator_headers(  # def _operator_headers(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    key: str | None = None,  # key: str | None = None,
) -> dict[str, str]:  # ) -> dict[str, str]:
    return _headers(environment, "warehouse_operator", key)  # return _headers(environm


def _manager_headers(  # def _manager_headers(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    key: str | None = None,  # key: str | None = None,
    username: str = "manager_one",  # username: str = 'manager
) -> dict[str, str]:  # ) -> dict[str, str]:
    return _headers(environment, username, key)  # return _headers(environm


def _balances(environment: WarehouseEnvironment) -> list[tuple[int, int, int, int]]:  # def _balances(environmen
    with environment.session_factory() as db:  # with environment.session
        return list(  # return list(
            db.execute(  # db.execute(
                select(  # select(
                    StockBalance.balance_id,  # StockBalance.balance_id,
                    StockBalance.product_id,  # StockBalance.product_id,
                    StockBalance.location_id,  # StockBalance.location_id
                    StockBalance.quantity,  # StockBalance.quantity,
                ).order_by(StockBalance.balance_id)  # ).order_by(StockBalance.
            )  # )
        )  # )


def _ledgers(environment: WarehouseEnvironment) -> list[tuple[int, ...]]:  # def _ledgers(environment
    with environment.session_factory() as db:  # with environment.session
        return list(  # return list(
            db.execute(  # db.execute(
                select(  # select(
                    StockLedger.ledger_id,  # StockLedger.ledger_id,
                    StockLedger.product_id,  # StockLedger.product_id,
                    StockLedger.location_id,  # StockLedger.location_id,
                    StockLedger.transaction_type,  # StockLedger.transaction_
                    StockLedger.quantity_delta,  # StockLedger.quantity_del
                    StockLedger.before_quantity,  # StockLedger.before_quant
                    StockLedger.after_quantity,  # StockLedger.after_quanti
                    StockLedger.source_type,  # StockLedger.source_type,
                    StockLedger.source_id,  # StockLedger.source_id,
                    StockLedger.idempotency_key,  # StockLedger.idempotency_
                ).order_by(StockLedger.ledger_id)  # ).order_by(StockLedger.l
            )  # )
        )  # )


def _audits(environment: WarehouseEnvironment) -> list[tuple[int, ...]]:  # def _audits(environment:
    with environment.session_factory() as db:  # with environment.session
        return list(  # return list(
            db.execute(  # db.execute(
                select(  # select(
                    AuditLog.audit_log_id,  # AuditLog.audit_log_id,
                    AuditLog.user_id,  # AuditLog.user_id,
                    AuditLog.action,  # AuditLog.action,
                    AuditLog.entity_type,  # AuditLog.entity_type,
                    AuditLog.entity_id,  # AuditLog.entity_id,
                    AuditLog.quantity_before,  # AuditLog.quantity_before
                    AuditLog.quantity_after,  # AuditLog.quantity_after,
                ).order_by(AuditLog.audit_log_id)  # ).order_by(AuditLog.audi
            )  # )
        )  # )


def _count_headers(  # def _count_headers(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    username: str = "warehouse_operator",  # username: str = 'warehou
    key: str | None = None,  # key: str | None = None,
) -> dict[str, str]:  # ) -> dict[str, str]:
    return _headers(environment, username, key)  # return _headers(environm


def _create_stock_count(  # def _create_stock_count(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    *,  # *,
    counted_quantity: int,  # counted_quantity: int,
    location_id: int = 1,  # location_id: int = 1,
    note: str | None = None,  # note: str | None = None,
    key: str = "count-create",  # key: str = 'count-create
) -> dict:  # ) -> dict:
    response = environment.client.post(  # response = environment.c
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(environment, key=key),  # headers=_count_headers(e
        json={  # json={
            "note": note,  # 'note': note,
            "items": [  # 'items': [
                {  # {
                    "product_id": environment.product_id,  # 'product_id': environmen
                    "location_id": location_id,  # 'location_id': location_
                    "counted_quantity": counted_quantity,  # 'counted_quantity': coun
                }  # }
            ],  # ],
        },  # },
    )  # )
    assert response.status_code == 201  # assert response.status_c
    return response.json()  # return response.json()


def _submit_stock_count(  # def _submit_stock_count(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    count_id: int,  # count_id: int,
    *,  # *,
    key: str = "count-submit",  # key: str = 'count-submit
) -> dict:  # ) -> dict:
    response = environment.client.post(  # response = environment.c
        f"/api/v1/stock-counts/{count_id}/submit",  # f'/api/v1/stock-counts/{
        headers=_count_headers(environment, key=key),  # headers=_count_headers(e
    )  # )
    assert response.status_code == 200  # assert response.status_c
    return response.json()  # return response.json()


def _stock_count_detail(environment: WarehouseEnvironment, count_id: int) -> dict:  # def _stock_count_detail(
    response = environment.client.get(  # response = environment.c
        f"/api/v1/stock-counts/{count_id}",  # f'/api/v1/stock-counts/{
        headers=_count_headers(environment),  # headers=_count_headers(e
    )  # )
    assert response.status_code == 200  # assert response.status_c
    return response.json()  # return response.json()


def _count_approval_tasks(environment: WarehouseEnvironment, count_id: int) -> list[ApprovalTask]:  # def _count_approval_task
    with environment.session_factory() as db:  # with environment.session
        return list(  # return list(
            db.scalars(  # db.scalars(
                select(ApprovalTask).where(  # select(ApprovalTask).whe
                    ApprovalTask.business_type == "stock_count",  # ApprovalTask.business_ty
                    ApprovalTask.business_id == count_id,  # ApprovalTask.business_id
                )  # )
            )  # )
        )  # )


def _count_ledgers(environment: WarehouseEnvironment, count_id: int) -> list[StockLedger]:  # def _count_ledgers(envir
    with environment.session_factory() as db:  # with environment.session
        return list(  # return list(
            db.scalars(  # db.scalars(
                select(StockLedger).where(  # select(StockLedger).wher
                    StockLedger.source_type == "stock_count_order",  # StockLedger.source_type 
                    StockLedger.source_id == count_id,  # StockLedger.source_id ==
                )  # )
            )  # )
        )  # )


def _stock_quantity(environment: WarehouseEnvironment, location_id: int = 1) -> int:  # def _stock_quantity(envi
    with environment.session_factory() as db:  # with environment.session
        balance = db.scalar(  # balance = db.scalar(
            select(StockBalance).where(  # select(StockBalance).whe
                StockBalance.product_id == environment.product_id,  # StockBalance.product_id 
                StockBalance.location_id == location_id,  # StockBalance.location_id
            )  # )
        )  # )
        assert balance is not None  # assert balance is not No
        return balance.quantity  # return balance.quantity


def _count_items(environment: WarehouseEnvironment, count_id: int) -> list[StockCountItem]:  # def _count_items(environ
    with environment.session_factory() as db:  # with environment.session
        return list(  # return list(
            db.scalars(  # db.scalars(
                select(StockCountItem).where(  # select(StockCountItem).w
                    StockCountItem.stock_count_order_id == count_id  # StockCountItem.stock_cou
                )  # )
            )  # )
        )  # )


def test_replayed_create_returns_original_created_status(  # def test_replayed_create
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    headers = _admin_headers(warehouse_environment, "count-create-key")  # headers = _admin_headers
    first = warehouse_environment.client.post(  # first = warehouse_enviro
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=headers,  # headers=headers,
        json={"items": []},  # json={'items': []},
    )  # )
    replay = warehouse_environment.client.post(  # replay = warehouse_envir
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=headers,  # headers=headers,
        json={"items": []},  # json={'items': []},
    )  # )
    assert first.status_code == replay.status_code == 201  # assert first.status_code
    assert first.json() == replay.json()  # assert first.json() == r


def test_warehouse_scope_rejects_operator_outside_scope(  # def test_warehouse_scope
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    response = warehouse_environment.client.post(  # response = warehouse_env
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_operator_headers(warehouse_environment, "out-of-scope"),  # headers=_operator_header
        json={"items": [{"product_id": 1, "location_id": 3, "counted_quantity": 4}]},  # json={'items': [{'produc
    )  # )
    assert response.status_code == 403  # assert response.status_c


def test_stock_count_reads_are_limited_to_warehouse_scope(  # def test_stock_count_rea
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=10,  # counted_quantity=10,
        key="scope-read-create",  # key='scope-read-create',
    )  # )

    list_response = warehouse_environment.client.get(  # list_response = warehous
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment, "manager_two"),  # headers=_count_headers(w
    )  # )
    detail_response = warehouse_environment.client.get(  # detail_response = wareho
        f"/api/v1/stock-counts/{created['stock_count_order_id']}",  # f'/api/v1/stock-counts/{
        headers=_count_headers(warehouse_environment, "manager_two"),  # headers=_count_headers(w
    )  # )

    assert list_response.status_code == 200  # assert list_response.sta
    assert list_response.json()["total"] == 0  # assert list_response.jso
    assert detail_response.status_code == 403  # assert detail_response.s
    assert detail_response.json()["code"] == "WAREHOUSE_SCOPE_FORBIDDEN"  # assert detail_response.j


def test_stock_count_submit_rejects_non_creator_operator(  # def test_stock_count_sub
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=10,  # counted_quantity=10,
        key="non-creator-create",  # key='non-creator-create'
    )  # )

    response = warehouse_environment.client.post(  # response = warehouse_env
        f"/api/v1/stock-counts/{created['stock_count_order_id']}/submit",  # f'/api/v1/stock-counts/{
        headers=_count_headers(  # headers=_count_headers(
            warehouse_environment,  # warehouse_environment,
            "warehouse_operator_two",  # 'warehouse_operator_two'
            key="non-creator-submit",  # key='non-creator-submit'
        ),  # ),
    )  # )

    assert response.status_code == 403  # assert response.status_c
    assert response.json()["code"] == "STOCK_COUNT_FORBIDDEN"  # assert response.json()['
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w
    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        order = db.get(StockCountOrder, created["stock_count_order_id"])  # order = db.get(StockCoun
        assert order is not None  # assert order is not None
        assert order.status == "counting"  # assert order.status == '


def test_stock_count_repeated_submit_with_new_key_returns_conflict(  # def test_stock_count_rep
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=7,  # counted_quantity=7,
        key="repeat-submit-create",  # key='repeat-submit-creat
    )  # )
    count_id = created["stock_count_order_id"]  # count_id = created['stoc
    first = _submit_stock_count(  # first = _submit_stock_co
        warehouse_environment,  # warehouse_environment,
        count_id,  # count_id,
        key="repeat-submit-first",  # key='repeat-submit-first
    )  # )

    second = warehouse_environment.client.post(  # second = warehouse_envir
        f"/api/v1/stock-counts/{count_id}/submit",  # f'/api/v1/stock-counts/{
        headers=_count_headers(  # headers=_count_headers(
            warehouse_environment,  # warehouse_environment,
            key="repeat-submit-second",  # key='repeat-submit-secon
        ),  # ),
    )  # )

    assert first["status"] == "pending_approval"  # assert first['status'] =
    assert second.status_code == 409  # assert second.status_cod
    assert second.json()["code"] == "STOCK_COUNT_STATE_INVALID"  # assert second.json()['co
    assert _count_approval_tasks(warehouse_environment, count_id) is not None  # assert _count_approval_t
    assert len(_count_approval_tasks(warehouse_environment, count_id)) == 1  # assert len(_count_approv
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w
    assert _count_ledgers(warehouse_environment, count_id) == []  # assert _count_ledgers(wa


def test_zero_variance_count_completes_without_ledger_or_approval(  # def test_zero_variance_c
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=10,  # counted_quantity=10,
        key="zero-variance-create",  # key='zero-variance-creat
    )  # )
    count_id = created["stock_count_order_id"]  # count_id = created['stoc
    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        count_id,  # count_id,
        key="zero-variance-submit",  # key='zero-variance-submi
    )  # )

    assert submitted["status"] == "completed"  # assert submitted['status
    assert _count_approval_tasks(warehouse_environment, count_id) == []  # assert _count_approval_t
    assert _count_ledgers(warehouse_environment, count_id) == []  # assert _count_ledgers(wa
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w

    detail = _stock_count_detail(warehouse_environment, count_id)  # detail = _stock_count_de
    assert detail["items"][0]["book_quantity"] == 10  # assert detail['items'][0
    assert detail["items"][0]["counted_quantity"] == 10  # assert detail['items'][0
    assert detail["items"][0]["variance_quantity"] == 0  # assert detail['items'][0


def test_count_variance_waits_for_approval_without_inventory_mutation(  # def test_count_variance_
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=7,  # counted_quantity=7,
        key="variance-create",  # key='variance-create',
    )  # )
    count_id = created["stock_count_order_id"]  # count_id = created['stoc
    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        count_id,  # count_id,
        key="variance-submit",  # key='variance-submit',
    )  # )

    assert submitted["status"] == "pending_approval"  # assert submitted['status
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w
    tasks = _count_approval_tasks(warehouse_environment, count_id)  # tasks = _count_approval_
    assert len(tasks) == 1  # assert len(tasks) == 1
    assert tasks[0].status == "pending"  # assert tasks[0].status =
    assert tasks[0].requested_by == warehouse_environment.operator_user_id  # assert tasks[0].requeste
    assert _count_ledgers(warehouse_environment, count_id) == []  # assert _count_ledgers(wa

    detail = _stock_count_detail(warehouse_environment, count_id)  # detail = _stock_count_de
    assert detail["items"][0]["book_quantity"] == 10  # assert detail['items'][0
    assert detail["items"][0]["counted_quantity"] == 7  # assert detail['items'][0
    assert detail["items"][0]["variance_quantity"] == -3  # assert detail['items'][0
    assert detail["approval_summary"]["status"] == "pending"  # assert detail['approval_


def test_count_rejects_negative_and_duplicate_lines(  # def test_count_rejects_n
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    negative = warehouse_environment.client.post(  # negative = warehouse_env
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment, key="negative-count"),  # headers=_count_headers(w
        json={  # json={
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "location_id": 1,  # 'location_id': 1,
                    "counted_quantity": -1,  # 'counted_quantity': -1,
                }  # }
            ]  # ]
        },  # },
    )  # )
    duplicate = warehouse_environment.client.post(  # duplicate = warehouse_en
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment, key="duplicate-count"),  # headers=_count_headers(w
        json={  # json={
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "location_id": 1,  # 'location_id': 1,
                    "counted_quantity": 1,  # 'counted_quantity': 1,
                },  # },
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "location_id": 1,  # 'location_id': 1,
                    "counted_quantity": 2,  # 'counted_quantity': 2,
                },  # },
            ]  # ]
        },  # },
    )  # )

    assert negative.status_code == 422  # assert negative.status_c
    assert duplicate.status_code == 422  # assert duplicate.status_


def test_count_update_replaces_items_and_uses_server_book_quantity(  # def test_count_update_re
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = warehouse_environment.client.post(  # created = warehouse_envi
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment, key="update-create"),  # headers=_count_headers(w
        json={"items": []},  # json={'items': []},
    )  # )
    assert created.status_code == 201  # assert created.status_co
    count_id = created.json()["stock_count_order_id"]  # count_id = created.json(

    updated = warehouse_environment.client.put(  # updated = warehouse_envi
        f"/api/v1/stock-counts/{count_id}",  # f'/api/v1/stock-counts/{
        headers=_count_headers(warehouse_environment, key="update-items"),  # headers=_count_headers(w
        json={  # json={
            "note": "cycle count",  # 'note': 'cycle count',
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "location_id": 1,  # 'location_id': 1,
                    "counted_quantity": 10,  # 'counted_quantity': 10,
                }  # }
            ],  # ],
        },  # },
    )  # )
    assert updated.status_code == 200  # assert updated.status_co
    assert updated.json()["status"] == "counting"  # assert updated.json()['s

    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        count_id,  # count_id,
        key="update-submit",  # key='update-submit',
    )  # )
    assert submitted["status"] == "completed"  # assert submitted['status
    items = _count_items(warehouse_environment, count_id)  # items = _count_items(war
    assert len(items) == 1  # assert len(items) == 1
    assert items[0].book_quantity == 10  # assert items[0].book_qua
    assert items[0].counted_quantity == 10  # assert items[0].counted_
    assert items[0].variance_quantity == 0  # assert items[0].variance

    late_update = warehouse_environment.client.put(  # late_update = warehouse_
        f"/api/v1/stock-counts/{count_id}",  # f'/api/v1/stock-counts/{
        headers=_count_headers(warehouse_environment, key="late-update"),  # headers=_count_headers(w
        json={"items": []},  # json={'items': []},
    )  # )
    assert late_update.status_code == 409  # assert late_update.statu


def test_stock_count_list_filters_status_and_paginates(  # def test_stock_count_lis
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    completed = _create_stock_count(  # completed = _create_stoc
        warehouse_environment,  # warehouse_environment,
        counted_quantity=10,  # counted_quantity=10,
        key="list-completed-create",  # key='list-completed-crea
    )  # )
    _submit_stock_count(  # _submit_stock_count(
        warehouse_environment,  # warehouse_environment,
        completed["stock_count_order_id"],  # completed['stock_count_o
        key="list-completed-submit",  # key='list-completed-subm
    )  # )
    draft = warehouse_environment.client.post(  # draft = warehouse_enviro
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment, key="list-draft-create"),  # headers=_count_headers(w
        json={"items": []},  # json={'items': []},
    )  # )
    assert draft.status_code == 201  # assert draft.status_code

    response = warehouse_environment.client.get(  # response = warehouse_env
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment),  # headers=_count_headers(w
        params={"status": "completed", "page": 1, "page_size": 10},  # params={'status': 'compl
    )  # )
    assert response.status_code == 200  # assert response.status_c
    body = response.json()  # body = response.json()
    assert body["total"] >= 1  # assert body['total'] >= 
    assert body["page"] == 1  # assert body['page'] == 1
    assert body["page_size"] == 10  # assert body['page_size']
    assert all(item["status"] == "completed" for item in body["items"])  # assert all(item['status'


def test_stock_count_service_approval_applies_loss_and_rejection_keeps_inventory(  # def test_stock_count_ser
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    from backend.app.services.stock_count_service import (  # from backend.app.service
        approve_stock_count,  # approve_stock_count,
        reject_stock_count,  # reject_stock_count,
    )  # )

    approved_count = _create_stock_count(  # approved_count = _create
        warehouse_environment,  # warehouse_environment,
        counted_quantity=7,  # counted_quantity=7,
        key="approve-service-create",  # key='approve-service-cre
    )  # )
    approved_count_id = approved_count["stock_count_order_id"]  # approved_count_id = appr
    _submit_stock_count(  # _submit_stock_count(
        warehouse_environment,  # warehouse_environment,
        approved_count_id,  # approved_count_id,
        key="approve-service-submit",  # key='approve-service-sub
    )  # )
    approved_result = approve_stock_count(  # approved_result = approv
        warehouse_environment.session_factory(),  # warehouse_environment.se
        count_id=approved_count_id,  # count_id=approved_count_
        user_id=warehouse_environment.admin_user_id,  # user_id=warehouse_enviro
        key="approve-service-key",  # key='approve-service-key
        request_id="test-request",  # request_id='test-request
    )  # )
    assert approved_result.status_code == 200  # assert approved_result.s
    assert approved_result.body["status"] == "applied"  # assert approved_result.b
    assert _stock_quantity(warehouse_environment) == 7  # assert _stock_quantity(w
    ledgers = _count_ledgers(warehouse_environment, approved_count_id)  # ledgers = _count_ledgers
    assert len(ledgers) == 1  # assert len(ledgers) == 1
    assert ledgers[0].transaction_type == "count_loss"  # assert ledgers[0].transa
    assert ledgers[0].quantity_delta == -3  # assert ledgers[0].quanti

    rejected_count = _create_stock_count(  # rejected_count = _create
        warehouse_environment,  # warehouse_environment,
        counted_quantity=6,  # counted_quantity=6,
        key="reject-service-create",  # key='reject-service-crea
    )  # )
    rejected_count_id = rejected_count["stock_count_order_id"]  # rejected_count_id = reje
    _submit_stock_count(  # _submit_stock_count(
        warehouse_environment,  # warehouse_environment,
        rejected_count_id,  # rejected_count_id,
        key="reject-service-submit",  # key='reject-service-subm
    )  # )
    rejected_result = reject_stock_count(  # rejected_result = reject
        warehouse_environment.session_factory(),  # warehouse_environment.se
        count_id=rejected_count_id,  # count_id=rejected_count_
        user_id=warehouse_environment.admin_user_id,  # user_id=warehouse_enviro
        key="reject-service-key",  # key='reject-service-key'
        comment="资料不完整",  # comment='资料不完整',
        request_id="test-request",  # request_id='test-request
    )  # )
    assert rejected_result.status_code == 200  # assert rejected_result.s
    assert rejected_result.body["status"] == "rejected"  # assert rejected_result.b
    assert _stock_quantity(warehouse_environment) == 7  # assert _stock_quantity(w
    assert _count_ledgers(warehouse_environment, rejected_count_id) == []  # assert _count_ledgers(wa


def test_stock_count_mutations_write_before_and_after_audit_snapshots(  # def test_stock_count_mut
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    from backend.app.services.stock_count_service import approve_stock_count  # from backend.app.service

    created = warehouse_environment.client.post(  # created = warehouse_envi
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_count_headers(warehouse_environment, key="audit-create"),  # headers=_count_headers(w
        json={"items": []},  # json={'items': []},
    )  # )
    assert created.status_code == 201  # assert created.status_co
    count_id = created.json()["stock_count_order_id"]  # count_id = created.json(

    updated = warehouse_environment.client.put(  # updated = warehouse_envi
        f"/api/v1/stock-counts/{count_id}",  # f'/api/v1/stock-counts/{
        headers=_count_headers(warehouse_environment, key="audit-update"),  # headers=_count_headers(w
        json={  # json={
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "location_id": 1,  # 'location_id': 1,
                    "counted_quantity": 7,  # 'counted_quantity': 7,
                }  # }
            ]  # ]
        },  # },
    )  # )
    assert updated.status_code == 200  # assert updated.status_co
    _submit_stock_count(warehouse_environment, count_id, key="audit-submit")  # _submit_stock_count(ware
    approved = approve_stock_count(  # approved = approve_stock
        warehouse_environment.session_factory(),  # warehouse_environment.se
        count_id=count_id,  # count_id=count_id,
        user_id=warehouse_environment.admin_user_id,  # user_id=warehouse_enviro
        key="audit-approve",  # key='audit-approve',
        request_id="audit-request",  # request_id='audit-reques
    )  # )
    assert approved.status_code == 200  # assert approved.status_c

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        audits = list(  # audits = list(
            db.scalars(  # db.scalars(
                select(AuditLog)  # select(AuditLog)
                .where(  # .where(
                    AuditLog.entity_type == "stock_count_order",  # AuditLog.entity_type == 
                    AuditLog.entity_id == str(count_id),  # AuditLog.entity_id == st
                )  # )
                .order_by(AuditLog.audit_log_id)  # .order_by(AuditLog.audit
            )  # )
        )  # )
    by_action = {audit.action: audit for audit in audits}  # by_action = {audit.actio
    assert by_action["stock_count_update"].before_state is not None  # assert by_action['stock_
    assert by_action["stock_count_update"].after_state is not None  # assert by_action['stock_
    assert by_action["stock_count_submit"].before_state is not None  # assert by_action['stock_
    assert by_action["stock_count_submit"].after_state is not None  # assert by_action['stock_
    assert by_action["stock_count_approve"].before_state is not None  # assert by_action['stock_
    assert by_action["stock_count_approve"].after_state is not None  # assert by_action['stock_
    assert by_action["stock_count_approve"].after_state["execution_items"][0][  # assert by_action['stock_
        "submitted_book_quantity"  # 'submitted_book_quantity
    ] == 10  # ] == 10
    assert by_action["stock_count_approve"].after_state["execution_items"][0][  # assert by_action['stock_
        "execution_book_quantity"  # 'execution_book_quantity
    ] == 10  # ] == 10


def test_apply_count_adjustment_zero_delta_writes_no_ledger(  # def test_apply_count_adj
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    from backend.app.services.inventory_service import apply_count_adjustment  # from backend.app.service

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        before_quantity = _stock_quantity(warehouse_environment)  # before_quantity = _stock
        apply_count_adjustment(  # apply_count_adjustment(
            db,  # db,
            product_id=warehouse_environment.product_id,  # product_id=warehouse_env
            location_id=1,  # location_id=1,
            target_quantity=before_quantity,  # target_quantity=before_q
            source_id=999,  # source_id=999,
            item_id=999,  # item_id=999,
            key="zero-delta-key",  # key='zero-delta-key',
            user_id=warehouse_environment.admin_user_id,  # user_id=warehouse_enviro
        )  # )
        db.commit()  # db.commit()

    assert _stock_quantity(warehouse_environment) == before_quantity  # assert _stock_quantity(w
    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        ledger = db.scalar(  # ledger = db.scalar(
            select(StockLedger).where(  # select(StockLedger).wher
                StockLedger.idempotency_key == "zero-delta-key:stock-count-item-999:apply"  # StockLedger.idempotency_
            )  # )
        )  # )
        assert ledger is None  # assert ledger is None


def test_transfer_insufficient_stock_rolls_back_every_line(  # def test_transfer_insuff
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    before_balances = _balances(warehouse_environment)  # before_balances = _balan
    before_ledgers = _ledgers(warehouse_environment)  # before_ledgers = _ledger
    response = warehouse_environment.client.post(  # response = warehouse_env
        "/api/v1/transfers/1/execute",  # '/api/v1/transfers/1/exe
        headers=_operator_headers(warehouse_environment, "transfer-execute"),  # headers=_operator_header
    )  # )
    assert response.status_code == 409  # assert response.status_c
    assert _balances(warehouse_environment) == before_balances  # assert _balances(warehou
    assert _ledgers(warehouse_environment) == before_ledgers  # assert _ledgers(warehous


def test_service_result_replays_original_status_and_body(  # def test_service_result_
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    from backend.app.services.inventory_service import (  # from backend.app.service
        ServiceResult,  # ServiceResult,
        existing_idempotent_response,  # existing_idempotent_resp
        record_idempotent_response,  # record_idempotent_respon
        replay_result,  # replay_result,
    )  # )

    body = {"stock_count_order_id": 1, "status": "draft"}  # body = {'stock_count_ord
    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        record_idempotent_response(  # record_idempotent_respon
            db,  # db,
            user_id=warehouse_environment.admin_user_id,  # user_id=warehouse_enviro
            key="shared-replay-key",  # key='shared-replay-key',
            method="POST",  # method='POST',
            path="/api/v1/stock-counts",  # path='/api/v1/stock-coun
            body=body,  # body=body,
            status=201,  # status=201,
        )  # )
        db.commit()  # db.commit()

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        result = replay_result(  # result = replay_result(
            db,  # db,
            warehouse_environment.admin_user_id,  # warehouse_environment.ad
            "shared-replay-key",  # 'shared-replay-key',
        )  # )
        assert result == ServiceResult(body, 201, True)  # assert result == Service
        assert existing_idempotent_response(  # assert existing_idempote
            db,  # db,
            warehouse_environment.admin_user_id,  # warehouse_environment.ad
            "shared-replay-key",  # 'shared-replay-key',
        ) == body  # ) == body
        assert replay_result(db, warehouse_environment.admin_user_id, "missing") is None  # assert replay_result(db,
        row = db.scalar(  # row = db.scalar(
            select(IdempotencyRecord).where(  # select(IdempotencyRecord
                IdempotencyRecord.idempotency_key == "shared-replay-key"  # IdempotencyRecord.idempo
            )  # )
        )  # )
        assert row is not None  # assert row is not None
        assert row.request_method == "POST"  # assert row.request_metho


def test_role_and_warehouse_scope_semantics(  # def test_role_and_wareho
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    from backend.app.dependencies import ensure_warehouse_scope, get_current_user_roles  # from backend.app.depende

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        admin_roles = get_current_user_roles(db, warehouse_environment.admin_user_id)  # admin_roles = get_curren
        operator_roles = get_current_user_roles(  # operator_roles = get_cur
            db,  # db,
            warehouse_environment.operator_user_id,  # warehouse_environment.op
        )  # )
        manager_one_roles = get_current_user_roles(  # manager_one_roles = get_
            db,  # db,
            warehouse_environment.manager_one_user_id,  # warehouse_environment.ma
        )  # )
        manager_two_roles = get_current_user_roles(  # manager_two_roles = get_
            db,  # db,
            warehouse_environment.manager_two_user_id,  # warehouse_environment.ma
        )  # )
        assert admin_roles == {"admin"}  # assert admin_roles == {'
        assert operator_roles == {"warehouse_operator"}  # assert operator_roles ==
        assert manager_one_roles == {"warehouse_manager"}  # assert manager_one_roles
        assert manager_two_roles == {"warehouse_manager"}  # assert manager_two_roles

        ensure_warehouse_scope(db, warehouse_environment.admin_user_id, admin_roles, {1, 2})  # ensure_warehouse_scope(d
        ensure_warehouse_scope(  # ensure_warehouse_scope(
            db,  # db,
            warehouse_environment.operator_user_id,  # warehouse_environment.op
            operator_roles,  # operator_roles,
            {1},  # {1},
        )  # )
        ensure_warehouse_scope(  # ensure_warehouse_scope(
            db,  # db,
            warehouse_environment.manager_two_user_id,  # warehouse_environment.ma
            manager_two_roles,  # manager_two_roles,
            {2},  # {2},
        )  # )

        with pytest.raises(AppError) as exc_info:  # with pytest.raises(AppEr
            ensure_warehouse_scope(  # ensure_warehouse_scope(
                db,  # db,
                warehouse_environment.operator_user_id,  # warehouse_environment.op
                operator_roles,  # operator_roles,
                {1, 2},  # {1, 2},
            )  # )
        assert exc_info.value.code == "WAREHOUSE_SCOPE_FORBIDDEN"  # assert exc_info.value.co
        assert exc_info.value.status_code == 403  # assert exc_info.value.st


def test_apply_count_adjustment_writes_ledger_and_audit_without_commit(  # def test_apply_count_adj
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
    monkeypatch: pytest.MonkeyPatch,  # monkeypatch: pytest.Monk
) -> None:  # ) -> None:
    from backend.app.services.inventory_service import apply_count_adjustment  # from backend.app.service

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        monkeypatch.setattr(  # monkeypatch.setattr(
            db,  # db,
            "commit",  # 'commit',
            lambda: pytest.fail("count adjustment must not commit"),  # lambda: pytest.fail('cou
        )  # )
        apply_count_adjustment(  # apply_count_adjustment(
            db,  # db,
            product_id=warehouse_environment.product_id,  # product_id=warehouse_env
            location_id=1,  # location_id=1,
            target_quantity=12,  # target_quantity=12,
            source_id=1,  # source_id=1,
            item_id=1,  # item_id=1,
            key="count-approve",  # key='count-approve',
            user_id=warehouse_environment.operator_user_id,  # user_id=warehouse_enviro
        )  # )
        db.flush()  # db.flush()

        balance = db.scalar(  # balance = db.scalar(
            select(StockBalance).where(  # select(StockBalance).whe
                StockBalance.product_id == warehouse_environment.product_id,  # StockBalance.product_id 
                StockBalance.location_id == 1,  # StockBalance.location_id
            )  # )
        )  # )
        assert balance is not None  # assert balance is not No
        assert balance.quantity == 12  # assert balance.quantity 
        ledger = db.scalar(  # ledger = db.scalar(
            select(StockLedger).where(  # select(StockLedger).wher
                StockLedger.idempotency_key == "count-approve:stock-count-item-1:apply"  # StockLedger.idempotency_
            )  # )
        )  # )
        assert ledger is not None  # assert ledger is not Non
        assert ledger.transaction_type == "count_gain"  # assert ledger.transactio
        assert ledger.quantity_delta == 2  # assert ledger.quantity_d
        assert ledger.before_quantity == 10  # assert ledger.before_qua
        assert ledger.after_quantity == 12  # assert ledger.after_quan
        assert ledger.source_type == "stock_count_order"  # assert ledger.source_typ
        assert ledger.source_id == 1  # assert ledger.source_id 
        assert ledger.operator_id == warehouse_environment.operator_user_id  # assert ledger.operator_i

        audit = db.scalar(  # audit = db.scalar(
            select(AuditLog).where(  # select(AuditLog).where(
                AuditLog.action == "stock_count_apply",  # AuditLog.action == 'stoc
                AuditLog.entity_type == "stock_balance",  # AuditLog.entity_type == 
                AuditLog.entity_id == str(balance.balance_id),  # AuditLog.entity_id == st
            )  # )
        )  # )
        assert audit is not None  # assert audit is not None
        assert audit.quantity_before == 10  # assert audit.quantity_be
        assert audit.quantity_after == 12  # assert audit.quantity_af

        db.rollback()  # db.rollback()

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        balance = db.scalar(  # balance = db.scalar(
            select(StockBalance).where(  # select(StockBalance).whe
                StockBalance.product_id == warehouse_environment.product_id,  # StockBalance.product_id 
                StockBalance.location_id == 1,  # StockBalance.location_id
            )  # )
        )  # )
        assert balance is not None  # assert balance is not No
        assert balance.quantity == 10  # assert balance.quantity 
        assert db.scalar(select(StockLedger)) is None  # assert db.scalar(select(
        assert db.scalar(select(AuditLog)) is None  # assert db.scalar(select(


def test_execute_transfer_line_moves_stock_and_writes_paired_ledgers(  # def test_execute_transfe
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
    monkeypatch: pytest.MonkeyPatch,  # monkeypatch: pytest.Monk
) -> None:  # ) -> None:
    from backend.app.services.inventory_service import execute_transfer_line  # from backend.app.service

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        monkeypatch.setattr(  # monkeypatch.setattr(
            db,  # db,
            "commit",  # 'commit',
            lambda: pytest.fail("transfer line must not commit"),  # lambda: pytest.fail('tra
        )  # )
        execute_transfer_line(  # execute_transfer_line(
            db,  # db,
            product_id=warehouse_environment.product_id,  # product_id=warehouse_env
            source_location_id=1,  # source_location_id=1,
            target_location_id=2,  # target_location_id=2,
            quantity=3,  # quantity=3,
            source_id=1,  # source_id=1,
            item_id=1,  # item_id=1,
            key="transfer-execute",  # key='transfer-execute',
            user_id=warehouse_environment.operator_user_id,  # user_id=warehouse_enviro
        )  # )
        db.flush()  # db.flush()

        source = db.scalar(  # source = db.scalar(
            select(StockBalance).where(  # select(StockBalance).whe
                StockBalance.product_id == warehouse_environment.product_id,  # StockBalance.product_id 
                StockBalance.location_id == 1,  # StockBalance.location_id
            )  # )
        )  # )
        target = db.scalar(  # target = db.scalar(
            select(StockBalance).where(  # select(StockBalance).whe
                StockBalance.product_id == warehouse_environment.product_id,  # StockBalance.product_id 
                StockBalance.location_id == 2,  # StockBalance.location_id
            )  # )
        )  # )
        assert source is not None  # assert source is not Non
        assert target is not None  # assert target is not Non
        assert source.quantity == 7  # assert source.quantity =
        assert target.quantity == 3  # assert target.quantity =

        out_ledger = db.scalar(  # out_ledger = db.scalar(
            select(StockLedger).where(  # select(StockLedger).wher
                StockLedger.idempotency_key == "transfer-execute:transfer-item-1:out"  # StockLedger.idempotency_
            )  # )
        )  # )
        in_ledger = db.scalar(  # in_ledger = db.scalar(
            select(StockLedger).where(  # select(StockLedger).wher
                StockLedger.idempotency_key == "transfer-execute:transfer-item-1:in"  # StockLedger.idempotency_
            )  # )
        )  # )
        assert out_ledger is not None  # assert out_ledger is not
        assert in_ledger is not None  # assert in_ledger is not 
        assert out_ledger.transaction_type == "transfer_out"  # assert out_ledger.transa
        assert in_ledger.transaction_type == "transfer_in"  # assert in_ledger.transac
        assert out_ledger.quantity_delta == -3  # assert out_ledger.quanti
        assert in_ledger.quantity_delta == 3  # assert in_ledger.quantit
        assert (out_ledger.before_quantity, out_ledger.after_quantity) == (10, 7)  # assert (out_ledger.befor
        assert (in_ledger.before_quantity, in_ledger.after_quantity) == (0, 3)  # assert (in_ledger.before
        assert out_ledger.source_type == in_ledger.source_type == "transfer_order"  # assert out_ledger.source
        assert out_ledger.source_id == in_ledger.source_id == 1  # assert out_ledger.source
        assert out_ledger.operator_id == in_ledger.operator_id  # assert out_ledger.operat

        audits = list(  # audits = list(
            db.scalars(  # db.scalars(
                select(AuditLog).where(  # select(AuditLog).where(
                    AuditLog.action.in_(("transfer_out", "transfer_in")),  # AuditLog.action.in_(('tr
                ).order_by(AuditLog.action)  # ).order_by(AuditLog.acti
            )  # )
        )  # )
        assert [  # assert [
            (audit.action, audit.quantity_before, audit.quantity_after)  # (audit.action, audit.qua
            for audit in audits  # for audit in audits
        ] == [  # ] == [
            ("transfer_in", 0, 3),  # ('transfer_in', 0, 3),
            ("transfer_out", 10, 7),  # ('transfer_out', 10, 7),
        ]  # ]

        db.rollback()  # db.rollback()

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        assert db.scalar(select(StockLedger)) is None  # assert db.scalar(select(
        assert db.scalar(select(AuditLog)) is None  # assert db.scalar(select(


def test_transfer_insufficient_stock_rolls_back_shared_primitive_lines(  # def test_transfer_insuff
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
    monkeypatch: pytest.MonkeyPatch,  # monkeypatch: pytest.Monk
) -> None:  # ) -> None:
    from backend.app.services.inventory_service import execute_transfer_line  # from backend.app.service

    before_balances = _balances(warehouse_environment)  # before_balances = _balan
    before_ledgers = _ledgers(warehouse_environment)  # before_ledgers = _ledger
    before_audits = _audits(warehouse_environment)  # before_audits = _audits(

    with warehouse_environment.session_factory() as db:  # with warehouse_environme
        monkeypatch.setattr(  # monkeypatch.setattr(
            db,  # db,
            "commit",  # 'commit',
            lambda: pytest.fail("transfer line must not commit"),  # lambda: pytest.fail('tra
        )  # )
        execute_transfer_line(  # execute_transfer_line(
            db,  # db,
            product_id=warehouse_environment.product_id,  # product_id=warehouse_env
            source_location_id=1,  # source_location_id=1,
            target_location_id=2,  # target_location_id=2,
            quantity=2,  # quantity=2,
            source_id=1,  # source_id=1,
            item_id=1,  # item_id=1,
            key="transfer-failure",  # key='transfer-failure',
            user_id=warehouse_environment.operator_user_id,  # user_id=warehouse_enviro
        )  # )
        db.flush()  # db.flush()

        with pytest.raises(AppError) as exc_info:  # with pytest.raises(AppEr
            execute_transfer_line(  # execute_transfer_line(
                db,  # db,
                product_id=warehouse_environment.product_id,  # product_id=warehouse_env
                source_location_id=2,  # source_location_id=2,
                target_location_id=1,  # target_location_id=1,
                quantity=20,  # quantity=20,
                source_id=1,  # source_id=1,
                item_id=2,  # item_id=2,
                key="transfer-failure",  # key='transfer-failure',
                user_id=warehouse_environment.operator_user_id,  # user_id=warehouse_enviro
            )  # )
        assert exc_info.value.code == "INVENTORY_INSUFFICIENT"  # assert exc_info.value.co
        assert exc_info.value.message == "库存不足"  # assert exc_info.value.me
        assert exc_info.value.status_code == 409  # assert exc_info.value.st

        db.rollback()  # db.rollback()

    assert _balances(warehouse_environment) == before_balances  # assert _balances(warehou
    assert _ledgers(warehouse_environment) == before_ledgers  # assert _ledgers(warehous
    assert _audits(warehouse_environment) == before_audits  # assert _audits(warehouse


def _create_transfer(  # def _create_transfer(
    environment: WarehouseEnvironment,  # environment: WarehouseEn
    *,  # *,
    source_location_id: int,  # source_location_id: int,
    target_location_id: int,  # target_location_id: int,
    quantity: int,  # quantity: int,
    username: str = "warehouse_operator",  # username: str = 'warehou
    key: str = "transfer-create",  # key: str = 'transfer-cre
    extra_items: list[dict] | None = None,  # extra_items: list[dict] 
) -> dict:  # ) -> dict:
    items = [  # items = [
        {  # {
            "product_id": environment.product_id,  # 'product_id': environmen
            "source_location_id": source_location_id,  # 'source_location_id': so
            "target_location_id": target_location_id,  # 'target_location_id': ta
            "quantity": quantity,  # 'quantity': quantity,
        }  # }
    ]  # ]
    if extra_items:  # if extra_items:
        items.extend(extra_items)  # items.extend(extra_items
    response = environment.client.post(  # response = environment.c
        "/api/v1/transfers",  # '/api/v1/transfers',
        headers=_headers(environment, username, key),  # headers=_headers(environ
        json={"note": "move", "items": items},  # json={'note': 'move', 'i
    )  # )
    assert response.status_code == 201, response.text  # assert response.status_c
    return response.json()  # return response.json()


def test_same_warehouse_transfer_requires_approval_then_writes_two_ledgers(  # def test_same_warehouse_
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_transfer(  # created = _create_transf
        warehouse_environment,  # warehouse_environment,
        source_location_id=1,  # source_location_id=1,
        target_location_id=2,  # target_location_id=2,
        quantity=3,  # quantity=3,
        key="same-create",  # key='same-create',
    )  # )
    transfer_id = created["transfer_order_id"]  # transfer_id = created['t
    submitted = warehouse_environment.client.post(  # submitted = warehouse_en
        f"/api/v1/transfers/{transfer_id}/submit",  # f'/api/v1/transfers/{tra
        headers=_operator_headers(warehouse_environment, "same-submit"),  # headers=_operator_header
    )  # )
    assert submitted.status_code == 200  # assert submitted.status_
    assert submitted.json()["status"] == "pending_approval"  # assert submitted.json()[
    assert submitted.json()["transfer_scope"] == "intra_warehouse"  # assert submitted.json()[
    approval_id = submitted.json()["approval_summary"]["approval_task_id"]  # approval_id = submitted.

    early = warehouse_environment.client.post(  # early = warehouse_enviro
        f"/api/v1/transfers/{transfer_id}/execute",  # f'/api/v1/transfers/{tra
        headers=_operator_headers(warehouse_environment, "same-early-exec"),  # headers=_operator_header
    )  # )
    assert early.status_code == 409  # assert early.status_code

    approved = warehouse_environment.client.post(  # approved = warehouse_env
        f"/api/v1/approvals/{approval_id}/approve",  # f'/api/v1/approvals/{app
        headers=_manager_headers(warehouse_environment, "same-approve"),  # headers=_manager_headers
        json={},  # json={},
    )  # )
    assert approved.status_code == 200  # assert approved.status_c
    assert approved.json()["business_status"] == "executable"  # assert approved.json()['

    before_source = _stock_quantity(warehouse_environment, 1)  # before_source = _stock_q
    executed = warehouse_environment.client.post(  # executed = warehouse_env
        f"/api/v1/transfers/{transfer_id}/execute",  # f'/api/v1/transfers/{tra
        headers=_operator_headers(warehouse_environment, "same-execute"),  # headers=_operator_header
    )  # )
    assert executed.status_code == 200  # assert executed.status_c
    assert executed.json()["status"] == "completed"  # assert executed.json()['
    assert _stock_quantity(warehouse_environment, 1) == before_source - 3  # assert _stock_quantity(w
    assert _stock_quantity(warehouse_environment, 2) == 3  # assert _stock_quantity(w

    types = sorted(  # types = sorted(
        row[3]  # row[3]
        for row in _ledgers(warehouse_environment)  # for row in _ledgers(ware
        if row[7] == "transfer_order" and row[8] == transfer_id  # if row[7] == 'transfer_o
    )  # )
    assert types == ["transfer_in", "transfer_out"]  # assert types == ['transf

    repeated = warehouse_environment.client.post(  # repeated = warehouse_env
        f"/api/v1/transfers/{transfer_id}/execute",  # f'/api/v1/transfers/{tra
        headers=_operator_headers(warehouse_environment, "same-execute-again"),  # headers=_operator_header
    )  # )
    assert repeated.status_code == 409  # assert repeated.status_c

    active = warehouse_environment.client.get(  # active = warehouse_envir
        "/api/v1/transfers?status=draft,pending_approval,executable",  # '/api/v1/transfers?statu
        headers=_operator_headers(warehouse_environment),  # headers=_operator_header
    )  # )
    assert active.status_code == 200  # assert active.status_cod
    assert all(item["status"] != "completed" for item in active.json()["items"])  # assert all(item['status'
    history = warehouse_environment.client.get(  # history = warehouse_envi
        "/api/v1/transfers?status=completed,rejected",  # '/api/v1/transfers?statu
        headers=_operator_headers(warehouse_environment),  # headers=_operator_header
    )  # )
    assert history.status_code == 200  # assert history.status_co
    assert any(item["transfer_order_id"] == transfer_id for item in history.json()["items"])  # assert any(item['transfe


def test_cross_warehouse_transfer_requires_approval_then_execution(  # def test_cross_warehouse
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_transfer(  # created = _create_transf
        warehouse_environment,  # warehouse_environment,
        source_location_id=1,  # source_location_id=1,
        target_location_id=3,  # target_location_id=3,
        quantity=2,  # quantity=2,
        username="admin",  # username='admin',
        key="cross-create",  # key='cross-create',
    )  # )
    transfer_id = created["transfer_order_id"]  # transfer_id = created['t
    submitted = warehouse_environment.client.post(  # submitted = warehouse_en
        f"/api/v1/transfers/{transfer_id}/submit",  # f'/api/v1/transfers/{tra
        headers=_admin_headers(warehouse_environment, "cross-submit"),  # headers=_admin_headers(w
    )  # )
    assert submitted.status_code == 200  # assert submitted.status_
    assert submitted.json()["status"] == "pending_approval"  # assert submitted.json()[
    assert submitted.json()["transfer_scope"] == "cross_warehouse"  # assert submitted.json()[
    approval_id = submitted.json()["approval_summary"]["approval_task_id"]  # approval_id = submitted.

    early = warehouse_environment.client.post(  # early = warehouse_enviro
        f"/api/v1/transfers/{transfer_id}/execute",  # f'/api/v1/transfers/{tra
        headers=_admin_headers(warehouse_environment, "early-exec"),  # headers=_admin_headers(w
    )  # )
    assert early.status_code == 409  # assert early.status_code
    assert _stock_quantity(warehouse_environment, 1) == 10  # assert _stock_quantity(w

    approved = warehouse_environment.client.post(  # approved = warehouse_env
        f"/api/v1/approvals/{approval_id}/approve",  # f'/api/v1/approvals/{app
        headers=_manager_headers(warehouse_environment, "cross-approve"),  # headers=_manager_headers
        json={},  # json={},
    )  # )
    assert approved.status_code == 200  # assert approved.status_c
    assert approved.json()["business_status"] == "executable"  # assert approved.json()['
    assert _stock_quantity(warehouse_environment, 1) == 10  # assert _stock_quantity(w

    executed = warehouse_environment.client.post(  # executed = warehouse_env
        f"/api/v1/transfers/{transfer_id}/execute",  # f'/api/v1/transfers/{tra
        headers=_admin_headers(warehouse_environment, "cross-execute"),  # headers=_admin_headers(w
    )  # )
    assert executed.status_code == 200  # assert executed.status_c
    assert executed.json()["status"] == "completed"  # assert executed.json()['
    assert _stock_quantity(warehouse_environment, 1) == 8  # assert _stock_quantity(w
    assert _stock_quantity(warehouse_environment, 3) == 7  # assert _stock_quantity(w


def test_transfer_rejects_mixed_scope_same_location_and_insufficient_stock(  # def test_transfer_reject
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    same_location = warehouse_environment.client.post(  # same_location = warehous
        "/api/v1/transfers",  # '/api/v1/transfers',
        headers=_operator_headers(warehouse_environment, "same-location"),  # headers=_operator_header
        json={  # json={
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "source_location_id": 1,  # 'source_location_id': 1,
                    "target_location_id": 1,  # 'target_location_id': 1,
                    "quantity": 1,  # 'quantity': 1,
                }  # }
            ]  # ]
        },  # },
    )  # )
    mixed = warehouse_environment.client.post(  # mixed = warehouse_enviro
        "/api/v1/transfers",  # '/api/v1/transfers',
        headers=_admin_headers(warehouse_environment, "mixed-scope"),  # headers=_admin_headers(w
        json={  # json={
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "source_location_id": 1,  # 'source_location_id': 1,
                    "target_location_id": 2,  # 'target_location_id': 2,
                    "quantity": 1,  # 'quantity': 1,
                },  # },
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "source_location_id": 1,  # 'source_location_id': 1,
                    "target_location_id": 3,  # 'target_location_id': 3,
                    "quantity": 1,  # 'quantity': 1,
                },  # },
            ]  # ]
        },  # },
    )  # )
    assert same_location.status_code == 422  # assert same_location.sta
    assert mixed.status_code == 422  # assert mixed.status_code


def test_count_variance_waits_then_approval_applies_ledger(  # def test_count_variance_
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=7,  # counted_quantity=7,
        key="http-count-create",  # key='http-count-create',
    )  # )
    count_id = created["stock_count_order_id"]  # count_id = created['stoc
    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        count_id,  # count_id,
        key="http-count-submit",  # key='http-count-submit',
    )  # )
    assert submitted["status"] == "pending_approval"  # assert submitted['status
    approval_id = submitted["approval_summary"]["approval_task_id"]  # approval_id = submitted[
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w

    approved = warehouse_environment.client.post(  # approved = warehouse_env
        f"/api/v1/approvals/{approval_id}/approve",  # f'/api/v1/approvals/{app
        headers=_manager_headers(warehouse_environment, "count-approve"),  # headers=_manager_headers
        json={},  # json={},
    )  # )
    assert approved.status_code == 200  # assert approved.status_c
    assert _stock_quantity(warehouse_environment) == 7  # assert _stock_quantity(w
    ledgers = _count_ledgers(warehouse_environment, count_id)  # ledgers = _count_ledgers
    assert len(ledgers) == 1  # assert len(ledgers) == 1
    assert ledgers[0].transaction_type == "count_loss"  # assert ledgers[0].transa


def test_reject_requires_comment_and_does_not_change_inventory(  # def test_reject_requires
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=4,  # counted_quantity=4,
        key="reject-count-create",  # key='reject-count-create
    )  # )
    count_id = created["stock_count_order_id"]  # count_id = created['stoc
    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        count_id,  # count_id,
        key="reject-count-submit",  # key='reject-count-submit
    )  # )
    approval_id = submitted["approval_summary"]["approval_task_id"]  # approval_id = submitted[

    empty = warehouse_environment.client.post(  # empty = warehouse_enviro
        f"/api/v1/approvals/{approval_id}/reject",  # f'/api/v1/approvals/{app
        headers=_manager_headers(warehouse_environment, "empty-reject"),  # headers=_manager_headers
        json={"comment": ""},  # json={'comment': ''},
    )  # )
    assert empty.status_code == 422  # assert empty.status_code
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w

    rejected = warehouse_environment.client.post(  # rejected = warehouse_env
        f"/api/v1/approvals/{approval_id}/reject",  # f'/api/v1/approvals/{app
        headers=_manager_headers(warehouse_environment, "reject"),  # headers=_manager_headers
        json={"comment": "现场记录不完整"},  # json={'comment': '现场记录不完
    )  # )
    assert rejected.status_code == 200  # assert rejected.status_c
    assert rejected.json()["status"] == "rejected"  # assert rejected.json()['
    assert _stock_quantity(warehouse_environment) == 10  # assert _stock_quantity(w
    assert _count_ledgers(warehouse_environment, count_id) == []  # assert _count_ledgers(wa


def test_operator_cannot_approve_and_creator_cannot_self_approve(  # def test_operator_cannot
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=6,  # counted_quantity=6,
        key="auth-count-create",  # key='auth-count-create',
    )  # )
    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        created["stock_count_order_id"],  # created['stock_count_ord
        key="auth-count-submit",  # key='auth-count-submit',
    )  # )
    approval_id = submitted["approval_summary"]["approval_task_id"]  # approval_id = submitted[

    operator_try = warehouse_environment.client.post(  # operator_try = warehouse
        f"/api/v1/approvals/{approval_id}/approve",  # f'/api/v1/approvals/{app
        headers=_operator_headers(warehouse_environment, "operator-approve"),  # headers=_operator_header
        json={},  # json={},
    )  # )
    assert operator_try.status_code == 403  # assert operator_try.stat

    admin_created = warehouse_environment.client.post(  # admin_created = warehous
        "/api/v1/stock-counts",  # '/api/v1/stock-counts',
        headers=_admin_headers(warehouse_environment, "admin-count-create"),  # headers=_admin_headers(w
        json={  # json={
            "items": [  # 'items': [
                {  # {
                    "product_id": warehouse_environment.product_id,  # 'product_id': warehouse_
                    "location_id": 1,  # 'location_id': 1,
                    "counted_quantity": 9,  # 'counted_quantity': 9,
                }  # }
            ]  # ]
        },  # },
    )  # )
    admin_id = admin_created.json()["stock_count_order_id"]  # admin_id = admin_created
    admin_submitted = warehouse_environment.client.post(  # admin_submitted = wareho
        f"/api/v1/stock-counts/{admin_id}/submit",  # f'/api/v1/stock-counts/{
        headers=_admin_headers(warehouse_environment, "admin-count-submit"),  # headers=_admin_headers(w
    )  # )
    admin_approval = admin_submitted.json()["approval_summary"]["approval_task_id"]  # admin_approval = admin_s
    self_approve = warehouse_environment.client.post(  # self_approve = warehouse
        f"/api/v1/approvals/{admin_approval}/approve",  # f'/api/v1/approvals/{adm
        headers=_admin_headers(warehouse_environment, "self-approve"),  # headers=_admin_headers(w
        json={},  # json={},
    )  # )
    assert self_approve.status_code == 200  # assert self_approve.stat
    assert self_approve.json()["status"] == "approved"  # assert self_approve.json


def test_pending_approval_list_contains_business_summary(  # def test_pending_approva
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    created = _create_stock_count(  # created = _create_stock_
        warehouse_environment,  # warehouse_environment,
        counted_quantity=8,  # counted_quantity=8,
        key="list-count-create",  # key='list-count-create',
    )  # )
    _submit_stock_count(  # _submit_stock_count(
        warehouse_environment,  # warehouse_environment,
        created["stock_count_order_id"],  # created['stock_count_ord
        key="list-count-submit",  # key='list-count-submit',
    )  # )
    response = warehouse_environment.client.get(  # response = warehouse_env
        "/api/v1/approvals?status=pending&business_type=stock_count",  # '/api/v1/approvals?statu
        headers=_manager_headers(warehouse_environment),  # headers=_manager_headers
    )  # )
    assert response.status_code == 200  # assert response.status_c
    assert response.json()["items"][0]["business_summary"]["order_no"].startswith("SC-")  # assert response.json()['
    assert response.json()["items"][0]["business_summary"]["status"] == "pending_approval"  # assert response.json()['


def test_stock_count_submit_freezes_stock_until_approval(  # def test_stock_count_sub
    warehouse_environment: WarehouseEnvironment,  # warehouse_environment: W
) -> None:  # ) -> None:
    client = warehouse_environment.client  # client = warehouse_envir
    product_id = warehouse_environment.product_id  # product_id = warehouse_e
    created = client.post(  # created = client.post(
        "/api/v1/outbounds",  # '/api/v1/outbounds',
        headers=_operator_headers(warehouse_environment, "freeze-out-create"),  # headers=_operator_header
        json={"order_no": "OUT-FREEZE", "items": [{"product_id": product_id, "quantity": 1}]},  # json={'order_no': 'OUT-F
    )  # )
    assert created.status_code == 201  # assert created.status_co
    outbound_id = created.json()["outbound_order_id"]  # outbound_id = created.js

    count = _create_stock_count(warehouse_environment, counted_quantity=6, key="freeze-count-create")  # count = _create_stock_co
    submitted = _submit_stock_count(  # submitted = _submit_stoc
        warehouse_environment,  # warehouse_environment,
        count["stock_count_order_id"],  # count['stock_count_order
        key="freeze-count-submit",  # key='freeze-count-submit
    )  # )
    assert submitted["status"] == "pending_approval"  # assert submitted['status

    availability = client.get(  # availability = client.ge
        f"/api/v1/inventory/{product_id}/availability",  # f'/api/v1/inventory/{pro
        headers=_operator_headers(warehouse_environment),  # headers=_operator_header
    )  # )
    assert availability.status_code == 200  # assert availability.stat
    assert availability.json()["available_quantity"] == 0  # assert availability.json
    assert availability.json()["frozen_quantity"] >= 1  # assert availability.json

    blocked = client.post(  # blocked = client.post(
        f"/api/v1/outbounds/{outbound_id}/allocate",  # f'/api/v1/outbounds/{out
        headers=_operator_headers(warehouse_environment, "freeze-allocate"),  # headers=_operator_header
    )  # )
    assert blocked.status_code == 409  # assert blocked.status_co
    assert blocked.json()["code"] == "INVENTORY_INSUFFICIENT"  # assert blocked.json()['c

    approval_id = submitted["approval_summary"]["approval_task_id"]  # approval_id = submitted[
    approved = client.post(  # approved = client.post(
        f"/api/v1/approvals/{approval_id}/approve",  # f'/api/v1/approvals/{app
        headers=_manager_headers(warehouse_environment, "freeze-approve"),  # headers=_manager_headers
        json={},  # json={},
    )  # )
    assert approved.status_code == 200  # assert approved.status_c

    released = client.get(  # released = client.get(
        f"/api/v1/inventory/{product_id}/availability",  # f'/api/v1/inventory/{pro
        headers=_operator_headers(warehouse_environment),  # headers=_operator_header
    )  # )
    assert released.json()["frozen_quantity"] == 0  # assert released.json()['
    assert released.json()["available_quantity"] > 0  # assert released.json()['

    allocated = client.post(  # allocated = client.post(
        f"/api/v1/outbounds/{outbound_id}/allocate",  # f'/api/v1/outbounds/{out
        headers=_operator_headers(warehouse_environment, "freeze-allocate-after"),  # headers=_operator_header
    )  # )
    assert allocated.status_code == 200  # assert allocated.status_
    assert allocated.json()["status"] == "allocated"  # assert allocated.json()[

