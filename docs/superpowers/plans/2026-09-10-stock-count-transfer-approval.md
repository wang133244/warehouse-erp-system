# 盘点、调拨与风险分级审批 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 FastAPI + MySQL + Vue 3 系统中交付可追溯、可审批、并发安全的盘点、调拨与审批中心闭环。

**Architecture:** 后端新增盘点、调拨、审批三个明确边界的模块；它们只编排业务状态，库存变更仍集中在 `inventory_service` 的事务与行锁原语中。审批任务引用真实业务单，不复制业务明细。前端将 `/counting`、`/transfer`、`/approvals` 从通用工作台中拆出为专用页面和对话框，通过 API 获取并刷新真实状态。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy 2、Alembic、MySQL 8、pytest、Vue 3、TypeScript、Pinia、Vue Router、Element Plus、Vitest、Vue Test Utils。

**Spec:** `docs/superpowers/specs/2026-09-10-stock-count-transfer-approval-design.md`

## Global Constraints

- 不执行 `database/schema.sql`；该文件含破坏性 `DROP TABLE`，数据库结构只可通过追加 Alembic 迁移变更。
- 全部写接口必须使用 JWT、`Idempotency-Key`、审计记录；同一用户、同一请求键必须返回首次保存的状态码和响应体。
- 任一库存变更都必须在同一事务内锁定库存行，同时落 `stock_ledger`、`audit_log`；出现异常时完整回滚。
- 盘点实盘数是非负整数；调拨数量是正整数；源/目标库位不能相同。
- 无差异盘点不改库存、不写流水；差异盘点只在审批通过时写 `count_gain` / `count_loss`。
- 同仓调拨提交后转 `executable`；跨仓调拨提交后转 `pending_approval`；两者均须人工显式执行后才改库存。
- 当前 `product` 和 `warehouse_location` 没有启停用字段；本阶段只验证记录存在，不扩展基础资料模型。
- 不打印、提交或写入数据库密码、JWT、管理员密码、token、`backend/.env`、`backend/.admin-password`。
- Git 目前会报 `BUG (fork bomb)`；每个提交步骤仍先运行命令，若故障未恢复则记录未提交事实，不能伪称提交成功。

## File Structure

| 文件 | 动作 | 职责 |
| --- | --- | --- |
| `backend/app/db/models/operations.py` | 修改 | 新增五个业务实体与 ORM 约束。 |
| `backend/app/db/models/__init__.py` | 修改 | 导出新实体，保证 Alembic/测试元数据注册。 |
| `backend/alembic/versions/0002_stock_count_transfer_approval.py` | 新建 | 从 `0001_add_backend_core` 起追加五张表和索引。 |
| `backend/app/services/inventory_service.py` | 修改 | 共享幂等、审计、行锁盘点调整和调拨原语。 |
| `backend/app/dependencies.py` | 修改 | 角色集合和仓库范围授权。 |
| `backend/app/schemas/{stock_counts,transfers,approvals}.py` | 新建 | 请求、校验和响应模型。 |
| `backend/app/services/{stock_count_service,transfer_service,approval_service}.py` | 新建 | 三个业务状态机。 |
| `backend/app/api/v1/{stock_counts,transfers,approvals}.py` | 新建 | REST 路由。 |
| `backend/app/main.py` | 修改 | 注册三个路由。 |
| `backend/tests/test_database_models.py` | 修改 | ORM 元数据与约束测试。 |
| `backend/tests/test_migration_safety.py` | 修改 | `0002` 追加迁移安全性测试。 |
| `backend/tests/test_warehouse_extensions_api.py` | 新建 | 盘点、调拨、审批、权限、幂等、审计 API 测试。 |
| `frontend/src/api/warehouse-extensions.ts` | 新建 | 类型化 API 客户端。 |
| `frontend/src/router/index.ts`、`frontend/src/layouts/AppShell.vue` | 修改 | 专用路由和内容插槽。 |
| `frontend/src/views/{StockCountView,TransferView,ApprovalView}.vue` | 新建 | 三个真实业务页面。 |
| `frontend/src/components/business/{StockCountDialog,TransferDialog,ApprovalDialog}.vue` | 新建 | 录入、编辑和审批对话框。 |
| `frontend/tests/warehouse-extensions-api.spec.ts` | 新建 | API URL、JWT、幂等请求头测试。 |
| `frontend/tests/warehouse-extensions-views.spec.ts` | 新建 | 页面角色、状态与动作测试。 |
| `docs/后端开发文档.md` | 修改 | 表、接口、迁移、状态机与验收记录。 |

## Interfaces

```python
@dataclass(frozen=True)
class ServiceResult:
    body: dict[str, Any]
    status_code: int
    replayed: bool = False


def replay_result(db: Session, user_id: int, key: str) -> ServiceResult | None: ...
def ensure_warehouse_scope(db: Session, user_id: int, roles: set[str], warehouse_ids: set[int]) -> None: ...
def apply_count_adjustment(db: Session, *, product_id: int, location_id: int, target_quantity: int, source_id: int, item_id: int, key: str, user_id: int) -> None: ...
def execute_transfer_line(db: Session, *, product_id: int, source_location_id: int, target_location_id: int, quantity: int, source_id: int, item_id: int, key: str, user_id: int) -> None: ...
```

```ts
export function listStockCounts(params?: PageQuery): Promise<PageResult<StockCountOrder>>
export function createStockCount(payload: StockCountUpsert, idempotencyKey?: string): Promise<StockCountOrder>
export function saveStockCount(id: number, payload: StockCountUpsert, idempotencyKey?: string): Promise<StockCountOrder>
export function submitStockCount(id: number, idempotencyKey?: string): Promise<StockCountOrder>
export function listTransfers(params?: PageQuery): Promise<PageResult<TransferOrder>>
export function createTransfer(payload: TransferUpsert, idempotencyKey?: string): Promise<TransferOrder>
export function saveTransfer(id: number, payload: TransferUpsert, idempotencyKey?: string): Promise<TransferOrder>
export function submitTransfer(id: number, idempotencyKey?: string): Promise<TransferOrder>
export function executeTransfer(id: number, idempotencyKey?: string): Promise<TransferOrder>
export function listApprovals(params?: ApprovalQuery): Promise<PageResult<ApprovalTask>>
export function approveApproval(id: number, comment?: string, idempotencyKey?: string): Promise<ApprovalTask>
export function rejectApproval(id: number, comment: string, idempotencyKey?: string): Promise<ApprovalTask>
```

### Task 1: Add extension ORM models and the additive migration

**Files:**
- Modify: `backend/app/db/models/operations.py`
- Modify: `backend/app/db/models/__init__.py`
- Create: `backend/alembic/versions/0002_stock_count_transfer_approval.py`
- Modify: `backend/tests/test_database_models.py`
- Modify: `backend/tests/test_migration_safety.py`

**Produces:** `StockCountOrder`、`StockCountItem`、`TransferOrder`、`TransferItem`、`ApprovalTask` 和 revision `0002_stock_count_transfer_approval`。

- [ ] **Step 1: Write failing metadata/migration tests.**

```python
from backend.app.db.models import ApprovalTask, StockCountItem, StockCountOrder, TransferItem, TransferOrder


def test_backend_models_include_warehouse_extensions():
    expected = {"stock_count_order", "stock_count_item", "transfer_order", "transfer_item", "approval_task"}
    assert expected.issubset(Base.metadata.tables)
    assert StockCountOrder.__tablename__ == "stock_count_order"
    assert StockCountItem.__tablename__ == "stock_count_item"
    assert TransferOrder.__tablename__ == "transfer_order"
    assert TransferItem.__tablename__ == "transfer_item"
    assert ApprovalTask.__tablename__ == "approval_task"
    assert any(c.name == "uq_approval_business" for c in ApprovalTask.__table__.constraints)


def test_extension_migration_is_additive_and_depends_on_core():
    source = (Path(__file__).parents[1] / "alembic/versions/0002_stock_count_transfer_approval.py").read_text(encoding="utf-8").lower()
    assert 'down_revision = "0001_add_backend_core"' in source
    assert "create_table" in source
    assert "drop_table" not in source
    assert "drop_column" not in source
```

- [ ] **Step 2: Run the focused tests and verify red.**

Run: `cd backend; pytest tests/test_database_models.py tests/test_migration_safety.py -q`  
Expected: FAIL because the extension models and `0002` do not exist.

- [ ] **Step 3: Add models and exact constraints.**

Add fields from the confirmed spec: order number/status/creator/submit/complete timestamps for count orders; book/count/variance for count items; scope/submit/execute fields for transfer orders; product/source/target/quantity for transfer items; requester/decision/comment fields for approval tasks. Add:

```python
UniqueConstraint("stock_count_order_id", "product_id", "location_id", name="uq_stock_count_item_line")
UniqueConstraint("transfer_order_id", "product_id", "source_location_id", "target_location_id", name="uq_transfer_item_line")
UniqueConstraint("business_type", "business_id", name="uq_approval_business")
CheckConstraint("counted_quantity >= 0", name="ck_stock_count_item_counted_nonnegative")
CheckConstraint("quantity > 0", name="ck_transfer_item_quantity_positive")
CheckConstraint("source_location_id <> target_location_id", name="ck_transfer_item_locations_different")
```

Export all five entities through `backend/app/db/models/__init__.py`.

- [ ] **Step 4: Implement guarded `0002` migration.**

```python
revision = "0002_stock_count_transfer_approval"
down_revision = "0001_add_backend_core"


def upgrade() -> None:
    _create_table_if_missing("stock_count_order", ...)
    _create_table_if_missing("stock_count_item", ...)
    _create_table_if_missing("transfer_order", ...)
    _create_table_if_missing("transfer_item", ...)
    _create_table_if_missing("approval_task", ...)
```

Reuse `0001`’s `_has_table` / `_create_table_if_missing` helper and MySQL unsigned foreign-key type. Create named indexes: `ix_stock_count_order_status_created_at`, `ix_transfer_order_status_created_at`, `ix_transfer_order_scope_status`, `ix_approval_task_status_created_at`, `ix_approval_task_requested_status`. `downgrade()` raises `NotImplementedError`, matching the non-destructive rollback policy.

- [ ] **Step 5: Re-run the focused tests.**

Run: `cd backend; pytest tests/test_database_models.py tests/test_migration_safety.py -q`  
Expected: PASS.

- [ ] **Step 6: Commit this task.**

```powershell
git add backend/app/db/models/operations.py backend/app/db/models/__init__.py backend/alembic/versions/0002_stock_count_transfer_approval.py backend/tests/test_database_models.py backend/tests/test_migration_safety.py
git commit -m "feat: add stock count transfer approval schema"
```

### Task 2: Add shared idempotency, warehouse authorization, audit and inventory primitives

**Files:**
- Modify: `backend/app/services/inventory_service.py`
- Modify: `backend/app/dependencies.py`
- Create: `backend/tests/test_warehouse_extensions_api.py`

**Consumes:** Task 1 models; existing `Role`、`UserRole`、`UserWarehouseScope`、`StockBalance`、`StockLedger`、`AuditLog`。

**Produces:** `ServiceResult`、稳定重放、仓库范围校验、盘点调整和双向调拨库存原语。

- [ ] **Step 1: Write failing shared behavior tests.**

```python
def test_replayed_create_returns_original_created_status(client):
    first = client.post("/api/v1/stock-counts", headers=headers("count-create-key"), json={"items": []})
    replay = client.post("/api/v1/stock-counts", headers=headers("count-create-key"), json={"items": []})
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()


def test_warehouse_scope_rejects_operator_outside_scope(client):
    response = client.post("/api/v1/stock-counts", headers=operator_headers("out-of-scope"), json={
        "items": [{"product_id": 1, "location_id": 3, "counted_quantity": 4}],
    })
    assert response.status_code == 403


def test_transfer_insufficient_stock_rolls_back_every_line(client):
    before_balances, before_ledgers = balances(), ledgers()
    response = client.post("/api/v1/transfers/1/execute", headers=operator_headers("transfer-execute"))
    assert response.status_code == 409
    assert balances() == before_balances
    assert ledgers() == before_ledgers
```

The fixture must create an `admin`, an `warehouse_operator`, two different `warehouse_manager` users, two warehouses, locations 1/2 in warehouse 1 and location 3 in warehouse 2, one product, stock balances, user roles, and scopes. Obtain every token through `/api/v1/auth/login`; never hard-code a token.

- [ ] **Step 2: Run focused tests and verify red.**

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -q`  
Expected: FAIL with `404` extension routes and missing shared symbols.

- [ ] **Step 3: Make new writes replay original response status and body.**

```python
@dataclass(frozen=True)
class ServiceResult:
    body: dict[str, Any]
    status_code: int
    replayed: bool = False


def replay_result(db: Session, user_id: int, key: str) -> ServiceResult | None:
    row = db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.user_id == user_id,
        IdempotencyRecord.idempotency_key == key,
    ))
    if row is None or row.response_body is None:
        return None
    return ServiceResult(row.response_body, row.response_status or 200, True)
```

Extend `record_idempotent_response` with `method: str = "POST"`; preserve the current `existing_idempotent_response` wrapper so inbounds/outbounds remain unchanged. New services return `ServiceResult`; new routes assign `response.status_code = result.status_code` for both first and replayed results.

- [ ] **Step 4: Add role/scope helpers.**

```python
def get_current_user_roles(db: Session, user_id: int) -> set[str]:
    return set(get_user_roles(db, user_id))


def ensure_warehouse_scope(db: Session, user_id: int, roles: set[str], warehouse_ids: set[int]) -> None:
    if "admin" in roles:
        return
    granted = set(db.scalars(select(UserWarehouseScope.warehouse_id).where(UserWarehouseScope.user_id == user_id)))
    if not warehouse_ids.issubset(granted):
        raise AppError("WAREHOUSE_SCOPE_FORBIDDEN", "没有目标仓库的操作权限", 403)
```

Use `require_roles` in route dependencies for role-category checks. Pass resolved role sets into services so each service checks every involved warehouse before a write. `admin` bypasses scope; `warehouse_operator` creates/edits/submits/executes; `warehouse_manager` approves; only `admin` has both abilities.

- [ ] **Step 5: Add locked inventory primitives without committing inside them.**

```python
def apply_count_adjustment(db: Session, *, product_id: int, location_id: int, target_quantity: int,
                           source_id: int, item_id: int, key: str, user_id: int) -> None:
    balance = _locked_balance(db, product_id, location_id, create=True)
    before = balance.quantity
    delta = target_quantity - before
    if delta == 0:
        return
    balance.quantity = target_quantity
    db.add(StockLedger(
        product_id=product_id, location_id=location_id,
        transaction_type="count_gain" if delta > 0 else "count_loss", quantity_delta=delta,
        before_quantity=before, after_quantity=target_quantity,
        source_type="stock_count_order", source_id=source_id,
        idempotency_key=f"{key}:stock-count-item-{item_id}:apply", operator_id=user_id,
    ))
    write_audit(db, user_id=user_id, action="stock_count_apply", entity_type="stock_balance",
                entity_id=balance.balance_id, quantity_before=before, quantity_after=target_quantity)
```

Implement `execute_transfer_line` by locking the source and target in sorted `(product_id, location_id)` order. Reject `source.quantity - source.reserved_quantity < quantity` with `INVENTORY_INSUFFICIENT`/409. Reduce source and increase target, create `transfer_out` and `transfer_in` ledger rows with unique `:transfer-item-{id}:out` / `:in` suffixes, and write audits. The caller owns one encompassing commit so a multi-line failure rolls back all balance, ledger, audit, and status updates.

- [ ] **Step 6: Re-run the shared test file.**

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -q`  
Expected: some business-route tests remain red; shared scope/idempotency/inventory tests pass.

- [ ] **Step 7: Commit shared infrastructure.**

```powershell
git add backend/app/services/inventory_service.py backend/app/dependencies.py backend/tests/test_warehouse_extensions_api.py
git commit -m "feat: add warehouse operation infrastructure"
```

### Task 3: Implement stock-count schemas, service, and routes

**Files:**
- Create: `backend/app/schemas/stock_counts.py`
- Create: `backend/app/services/stock_count_service.py`
- Create: `backend/app/api/v1/stock_counts.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_warehouse_extensions_api.py`

**Consumes:** Task 1 entities and Task 2 helpers.

**Produces:** `GET/POST /stock-counts`、`GET/PUT /stock-counts/{count_id}`、`POST /stock-counts/{count_id}/submit`。

- [ ] **Step 1: Write failing stock-count lifecycle tests.**

```python
def test_zero_variance_count_completes_without_ledger_or_approval(client):
    created = client.post("/api/v1/stock-counts", headers=operator_headers("count-create"), json={
        "note": "cycle", "items": [{"product_id": 1, "location_id": 1, "counted_quantity": 10}],
    })
    count_id = created.json()["stock_count_order_id"]
    submitted = client.post(f"/api/v1/stock-counts/{count_id}/submit", headers=operator_headers("count-submit"))
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "completed"
    assert count_approval_tasks(count_id) == 0
    assert count_ledgers(count_id) == 0


def test_count_variance_waits_then_approval_applies_ledger(client):
    count_id = create_count(client, counted_quantity=7)
    assert client.post(f"/api/v1/stock-counts/{count_id}/submit", headers=operator_headers("count-submit")).json()["status"] == "pending_approval"
    assert quantity(1, 1) == 10
    approved = client.post(f"/api/v1/approvals/{approval_id_for_count(count_id)}/approve", headers=manager_headers("count-approve"), json={})
    assert approved.status_code == 200
    assert quantity(1, 1) == 7
    assert latest_ledger().transaction_type == "count_loss"


def test_count_rejects_negative_and_duplicate_lines(client):
    negative = client.post("/api/v1/stock-counts", headers=operator_headers("negative"), json={"items": [{"product_id": 1, "location_id": 1, "counted_quantity": -1}]})
    duplicate = client.post("/api/v1/stock-counts", headers=operator_headers("duplicate"), json={"items": [{"product_id": 1, "location_id": 1, "counted_quantity": 1}, {"product_id": 1, "location_id": 1, "counted_quantity": 2}]})
    assert negative.status_code == duplicate.status_code == 422
```

- [ ] **Step 2: Run count-only tests and verify red.**

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -k "count" -q`  
Expected: FAIL because schemas/router/service do not exist.

- [ ] **Step 3: Define request/response schemas.**

```python
class StockCountItemInput(BaseModel):
    product_id: int = Field(gt=0)
    location_id: int = Field(gt=0)
    counted_quantity: int = Field(ge=0)

class StockCountUpsert(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    items: list[StockCountItemInput] = Field(default_factory=list)
```

Use `model_validator` to reject duplicate product/location pairs. Responses expose order identifiers/status/timestamps, item `book_quantity`/`counted_quantity`/`variance_quantity`, and approval summary when present.

- [ ] **Step 4: Implement create/update behavior.**

Creation generates `SC-YYYYMMDD-######`, writes audit and 201 idempotency response. An empty request stays `draft`; a request with item(s) becomes `counting`. `PUT` may replace only `draft`/`counting` item lines, belongs to the creator or admin, re-checks scope, and never accepts book/variance from the client.

- [ ] **Step 5: Implement submit/application behavior.**

At submit reject empty items with `COUNT_ITEMS_REQUIRED`/422; lock each current balance, write server-derived book and variance quantities, then set `completed` with no ledger if every variance is zero. Otherwise create exactly one `ApprovalTask(business_type="stock_count", ...)`, set `pending_approval`, and do not mutate inventory. The later approval service will call a public `approve_stock_count` function that re-locks, calls `apply_count_adjustment` per differing item, sets `applied`, and writes audit. Rejection sets `rejected` only.

- [ ] **Step 6: Add endpoints and application registration.**

```python
router = APIRouter(prefix="/stock-counts", tags=["盘点"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create(payload: StockCountUpsert, response: Response,
           current_user=Depends(require_roles("admin", "warehouse_operator")), ...):
    result = create_stock_count(...)
    response.status_code = result.status_code
    return result.body
```

Lists accept `page`, `page_size`, `status`, `order_no` and return `{items,total,page,page_size}`. Register the router in `create_app()`.

- [ ] **Step 7: Run tests and commit.**

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -k "count" -q; pytest tests/test_operations_api.py tests/test_errors.py -q`  
Expected: PASS.

```powershell
git add backend/app/schemas/stock_counts.py backend/app/services/stock_count_service.py backend/app/api/v1/stock_counts.py backend/app/main.py backend/tests/test_warehouse_extensions_api.py
git commit -m "feat: add stock count workflow"
```

### Task 4: Implement transfer schemas, service, and routes

**Files:**
- Create: `backend/app/schemas/transfers.py`
- Create: `backend/app/services/transfer_service.py`
- Create: `backend/app/api/v1/transfers.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_warehouse_extensions_api.py`

**Consumes:** Task 1 entities and Task 2 transfer primitive.

**Produces:** `GET/POST /transfers`、`GET/PUT /transfers/{transfer_id}`、`POST /transfers/{transfer_id}/submit`、`POST /transfers/{transfer_id}/execute`。

- [ ] **Step 1: Write failing transfer state-machine tests.**

```python
def test_same_warehouse_transfer_becomes_executable_then_writes_two_ledgers(client):
    transfer_id = create_transfer(client, source_location_id=1, target_location_id=2, quantity=3)
    submitted = client.post(f"/api/v1/transfers/{transfer_id}/submit", headers=operator_headers("same-submit"))
    assert submitted.json()["status"] == "executable"
    executed = client.post(f"/api/v1/transfers/{transfer_id}/execute", headers=operator_headers("same-execute"))
    assert executed.status_code == 200
    assert executed.json()["status"] == "completed"
    assert sorted(ledger_types_for(transfer_id)) == ["transfer_in", "transfer_out"]


def test_cross_warehouse_transfer_requires_approval_then_execution(client):
    transfer_id = create_transfer(client, source_location_id=1, target_location_id=3, quantity=2)
    submitted = client.post(f"/api/v1/transfers/{transfer_id}/submit", headers=operator_headers("cross-submit"))
    assert submitted.json()["status"] == "pending_approval"
    assert client.post(f"/api/v1/transfers/{transfer_id}/execute", headers=operator_headers("early-exec")).status_code == 409
    approved = client.post(f"/api/v1/approvals/{approval_id_for_transfer(transfer_id)}/approve", headers=manager_headers("cross-approve"), json={})
    assert approved.json()["business_status"] == "executable"


def test_transfer_rejects_mixed_scope_same_location_and_insufficient_stock(client):
    assert create_invalid_same_location(client).status_code == 422
    assert create_mixed_scope(client).status_code == 422
    assert execute_insufficient_transfer(client).status_code == 409
```

For insufficient stock, assert original balance, ledger count, audit count and transfer status are unchanged. Assert repeated `execute` gets 409 and cannot write a second pair of ledgers.

- [ ] **Step 2: Run transfer tests and verify red.**

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -k "transfer" -q`  
Expected: FAIL because the transfer module is absent.

- [ ] **Step 3: Add transfer schemas.**

```python
class TransferItemInput(BaseModel):
    product_id: int = Field(gt=0)
    source_location_id: int = Field(gt=0)
    target_location_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

    @model_validator(mode="after")
    def locations_differ(self):
        if self.source_location_id == self.target_location_id:
            raise ValueError("源库位和目标库位不能相同")
        return self
```

Reject duplicate `(product_id, source_location_id, target_location_id)` rows. Return `transfer_scope`, submit/execute user/time fields and complete item rows.

- [ ] **Step 4: Implement draft create/update and scope classification.**

Generate `TR-YYYYMMDD-######`; writes start as `draft`. Validate every product and location exists, verify warehouse scope for all source/target warehouse IDs, and limit updates to creator/admin while status is `draft`. At submit determine each line’s warehouse pair. All equal warehouses means `intra_warehouse`; all different means `cross_warehouse`; mixing those types raises `TRANSFER_SCOPE_MIXED`/422 and does not update status.

- [ ] **Step 5: Implement submit and atomic execution.**

```python
def submit_transfer(...):
    items = list_transfer_items(db, transfer_id)
    require_nonempty(items)
    scope = classify_transfer_scope(db, items)
    order.transfer_scope = scope
    order.submitted_by = user_id
    order.submitted_at = datetime.now(UTC)
    if scope == "intra_warehouse":
        order.status = "executable"
    else:
        order.status = "pending_approval"
        db.add(ApprovalTask(business_type="transfer", business_id=order.transfer_order_id,
                            status="pending", requested_by=user_id))
```

`execute_transfer` accepts only `executable`, locks all affected rows through `execute_transfer_line`, writes a top-level `transfer_execute` audit, marks `completed`, records its idempotent response, and commits once after every item succeeds. It does not create or decide approvals.

- [ ] **Step 6: Add routes, register them, rerun and commit.**

Use the same JWT, role, scope, idempotency and list pagination conventions as Task 3. Register `transfers.router` in `main.py`.

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -k "transfer" -q; pytest tests/test_operations_api.py -q`  
Expected: PASS.

```powershell
git add backend/app/schemas/transfers.py backend/app/services/transfer_service.py backend/app/api/v1/transfers.py backend/app/main.py backend/tests/test_warehouse_extensions_api.py
git commit -m "feat: add transfer workflow"
```

### Task 5: Implement approval schemas, service, and routes

**Files:**
- Create: `backend/app/schemas/approvals.py`
- Create: `backend/app/services/approval_service.py`
- Create: `backend/app/api/v1/approvals.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_warehouse_extensions_api.py`

**Consumes:** Task 3 public count approval/rejection functions, Task 4 transfer state transitions, and Task 2 authorization.

**Produces:** `GET /approvals`、`GET /approvals/{approval_id}`、`POST /approvals/{approval_id}/approve`、`POST /approvals/{approval_id}/reject`。

- [ ] **Step 1: Write failing approval tests.**

```python
def test_reject_requires_comment_and_does_not_change_inventory(client):
    empty = client.post(f"/api/v1/approvals/{approval_id}/reject", headers=manager_headers("empty-reject"), json={"comment": ""})
    assert empty.status_code == 422
    rejected = client.post(f"/api/v1/approvals/{approval_id}/reject", headers=manager_headers("reject"), json={"comment": "现场记录不完整"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert quantity(1, 1) == 10


def test_operator_cannot_approve_and_creator_cannot_self_approve(client):
    assert client.post(f"/api/v1/approvals/{approval_id}/approve", headers=operator_headers("operator-approve"), json={}).status_code == 403
    assert client.post(f"/api/v1/approvals/{approval_id}/approve", headers=creator_manager_headers("self-approve"), json={}).status_code == 403


def test_pending_approval_list_contains_business_summary(client):
    response = client.get("/api/v1/approvals?status=pending&business_type=stock_count", headers=manager_headers())
    assert response.status_code == 200
    assert response.json()["items"][0]["business_summary"]["order_no"].startswith("SC-")
```

- [ ] **Step 2: Run approval tests and verify red.**

Run: `cd backend; pytest tests/test_warehouse_extensions_api.py -k "approval" -q`  
Expected: FAIL because approval service/router are absent.

- [ ] **Step 3: Define decision schema.**

```python
class ApprovalDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def normalize_comment(self):
        self.comment = self.comment.strip() if self.comment else None
        return self
```

The reject service explicitly requires normalized `comment`; approve accepts it as optional. Add response serializers for task fields plus `business_summary` (type, order number, current business status, requester, requested time, item count).

- [ ] **Step 4: Implement authorization and decisions.**

Only `admin` and `warehouse_manager` may decide `pending` tasks. Fetch the business record, derive all involved warehouses, enforce scope, and reject `requested_by == user_id` with 403. **创建人/申请人不得审批自己的盘点差异或跨仓调拨；违反时返回 `403`。** For `stock_count`, delegate approval/rejection to Task 3 services. For `transfer`, approval changes task to `approved` and transfer to `executable` without calling inventory; rejection changes both to `rejected` without inventory. Every decision uses the supplied idempotency key and writes audit.

- [ ] **Step 5: Add routes, rerun the full backend suite, and commit.**

```python
@router.post("/{approval_id}/reject")
def reject(approval_id: int, payload: ApprovalDecision, response: Response,
           current_user=Depends(require_roles("admin", "warehouse_manager")), ...):
    result = reject_task(db, approval_id, current_user.user_id, roles, payload, idempotency_key)
    response.status_code = result.status_code
    return result.body
```

Run: `cd backend; pytest -q`  
Expected: PASS.

```powershell
git add backend/app/schemas/approvals.py backend/app/services/approval_service.py backend/app/api/v1/approvals.py backend/app/main.py backend/tests/test_warehouse_extensions_api.py
git commit -m "feat: add approval center workflow"
```

### Task 6: Add the typed frontend API module

**Files:**
- Create: `frontend/src/api/warehouse-extensions.ts`
- Create: `frontend/tests/warehouse-extensions-api.spec.ts`

**Consumes:** Backend endpoint and response contracts from Tasks 3–5; existing `request`, `createIdempotencyKey`, and token handling in `frontend/src/api/client.ts`.

**Produces:** Type-safe client calls with correct JWT and idempotency headers; no direct database access.

- [ ] **Step 1: Write failing API module tests.**

```ts
it('posts stock count with JWT and idempotency key', async () => {
  await createStockCount({ note: 'cycle', items: [{ product_id: 1, location_id: 2, counted_quantity: 3 }] })
  const [url, init] = fetchMock.mock.calls.at(-1)!
  expect(url).toBe('http://127.0.0.1:8000/api/v1/stock-counts')
  expect(init).toMatchObject({ method: 'POST' })
  expect(init.headers.Authorization).toBe('Bearer jwt-token')
  expect(init.headers['Idempotency-Key']).toMatch(/^stock-count-/)
})

it('sends a reject comment to the approval endpoint', async () => {
  await rejectApproval(8, '资料不完整')
  expect(fetchMock).toHaveBeenLastCalledWith(
    'http://127.0.0.1:8000/api/v1/approvals/8/reject',
    expect.objectContaining({ method: 'POST', body: JSON.stringify({ comment: '资料不完整' }) })
  )
})
```

Cover list-query encoding for `page`、`page_size`、`status`、`order_no`、`business_type`; cover all six write actions and their idempotency prefixes.

- [ ] **Step 2: Run test and verify red.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-api.spec.ts`  
Expected: FAIL with module-not-found.

- [ ] **Step 3: Implement exported types/functions.**

```ts
export function createStockCount(payload: StockCountUpsert, idempotencyKey?: string) {
  return request<StockCountOrder>('/api/v1/stock-counts', {
    method: 'POST', body: payload,
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('stock-count')
  })
}

export function executeTransfer(id: number, idempotencyKey?: string) {
  return request<TransferOrder>(`/api/v1/transfers/${id}/execute`, {
    method: 'POST', idempotencyKey: idempotencyKey ?? createIdempotencyKey('transfer-execute')
  })
}
```

Define `PageQuery`/`PageResult`, complete count/transfer/task/detail item types and all interface exports listed earlier. Generate a key only if the caller does not supply one; this lets a page retry the identical failed network action with the same key. Return backend data as-is; never synthesize a successful local state transition.

- [ ] **Step 4: Run focused API tests and commit.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-api.spec.ts tests/api-modules.spec.ts`  
Expected: PASS.

```powershell
git add frontend/src/api/warehouse-extensions.ts frontend/tests/warehouse-extensions-api.spec.ts
git commit -m "feat: add warehouse extension api client"
```

### Task 7: Route specialized views through AppShell

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppShell.vue`
- Create: `frontend/src/views/StockCountView.vue`
- Create: `frontend/src/views/TransferView.vue`
- Create: `frontend/src/views/ApprovalView.vue`
- Create: `frontend/tests/warehouse-extensions-views.spec.ts`

**Consumes:** Existing page configuration, menu/breadcrumb shell, Task 6 API types.

**Produces:** `/counting`、`/transfer`、`/approvals` render specialized pages; other existing paths still render `WorkspaceView.vue`.

- [ ] **Step 1: Write failing route/render tests.**

```ts
it.each([
  ['/counting', '盘点管理'],
  ['/transfer', '调拨管理'],
  ['/approvals', '审批中心']
])('renders specialized content at %s', async (path, title) => {
  await router.push(path)
  const wrapper = mount(AppShell, { global: { plugins: [ElementPlus, router, createPinia()] } })
  await flushPromises()
  expect(wrapper.text()).toContain(title)
  expect(wrapper.find('[data-testid="workspace-extension-page"]').exists()).toBe(true)
})
```

- [ ] **Step 2: Run tests and verify red.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-views.spec.ts`  
Expected: FAIL because all authenticated paths currently hard-code `WorkspaceView`.

- [ ] **Step 3: Convert AppShell to routed content.**

Replace `<WorkspaceView />` with `<RouterView />`; preserve the side menu, breadcrumb, login/logout, collapsed state, and active-menu computation. Keep `/login` public. Put the authenticated pages under an `AppShell` parent: explicit children for `counting`、`transfer`、`approvals` and a `WorkspaceView` catch-all child for `/dashboard` and all already-supported generic paths. Preserve root redirect and the existing router guard behavior.

- [ ] **Step 4: Create testable, non-fake page shells.**

Each new view contains `<main data-testid="workspace-extension-page">`, heading/subtitle from matching `pageConfigs`, status filter, loading view, error alert, empty state and table region. Do not add hard-coded records, “API not connected” notices, or buttons that claim success without an HTTP result.

- [ ] **Step 5: Run routing regression tests and commit.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-views.spec.ts tests/router-guard.spec.ts tests/workspace-integration.spec.ts`  
Expected: PASS.

```powershell
git add frontend/src/router/index.ts frontend/src/layouts/AppShell.vue frontend/src/views/StockCountView.vue frontend/src/views/TransferView.vue frontend/src/views/ApprovalView.vue frontend/tests/warehouse-extensions-views.spec.ts
git commit -m "feat: route warehouse extension pages"
```

### Task 8: Implement stock-count and transfer dialogs plus real page actions

**Files:**
- Create: `frontend/src/components/business/StockCountDialog.vue`
- Create: `frontend/src/components/business/TransferDialog.vue`
- Modify: `frontend/src/views/StockCountView.vue`
- Modify: `frontend/src/views/TransferView.vue`
- Modify: `frontend/tests/warehouse-extensions-views.spec.ts`

**Consumes:** Task 6 client, `listProducts`, `listLocations`, and roles from `useAppStore`.

**Produces:** Real record creation/editing/submission/execution interactions with backend refreshes.

- [ ] **Step 1: Write failing action tests.**

```ts
it('submits a counting stock-count order through the API', async () => {
  vi.mocked(listStockCounts).mockResolvedValue(pageOf([{ stock_count_order_id: 4, order_no: 'SC-20260910-000001', status: 'counting', items: [] }]))
  vi.mocked(submitStockCount).mockResolvedValue({ stock_count_order_id: 4, status: 'pending_approval' } as StockCountOrder)
  const wrapper = await mountExtension('/counting', ['warehouse_operator'])
  await wrapper.get('[data-testid="stock-count-submit-4"]').trigger('click')
  await flushPromises()
  expect(submitStockCount).toHaveBeenCalledWith(4)
})

it('executes only an executable transfer', async () => {
  vi.mocked(listTransfers).mockResolvedValue(pageOf([{ transfer_order_id: 5, order_no: 'TR-20260910-000001', status: 'executable', items: [] }]))
  const wrapper = await mountExtension('/transfer', ['warehouse_operator'])
  await wrapper.get('[data-testid="transfer-execute-5"]').trigger('click')
  expect(executeTransfer).toHaveBeenCalledWith(5)
})
```

Assert non-`draft`/`counting` count records cannot edit; non-`draft` transfer records cannot edit; operator sees no approval buttons; API errors show `ApiError.message` and do not optimistically change row status.

- [ ] **Step 2: Run tests and verify red.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-views.spec.ts`  
Expected: FAIL because specialized action controls are absent.

- [ ] **Step 3: Implement StockCountDialog.**

Props: `modelValue`, `initialValue`, `productOptions`, `locationOptions`, `submitting`. Emits: `update:modelValue`, `submit` with `{note,items}`. Allow add/remove rows, product/location selects, and integer `counted_quantity` inputs with `min="0"`. Before emitting, reject no rows and duplicate product/location pairs; book and variance fields are display-only, never editable.

- [ ] **Step 4: Implement TransferDialog.**

Use the same prop/emission style. Each row has product, source location, target location and quantity `min="1"`. Reject no rows, duplicate product/source/target pairs and equal source/target. Show only informational text “同仓提交后可执行；跨仓提交后需要审批”; backend owns final scope classification.

- [ ] **Step 5: Connect pages to real APIs.**

Load real page data on mount and after each successful write. `创建` uses create calls; `编辑` uses save calls; `提交` uses submit calls; `执行调拨` calls `executeTransfer`. Disable the relevant action while pending. Show create/edit/submit/execute only to `admin` / `warehouse_operator`, while retaining backend authorization as the final boundary.

- [ ] **Step 6: Run tests/build and commit.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-views.spec.ts; npm run build`  
Expected: PASS.

```powershell
git add frontend/src/components/business/StockCountDialog.vue frontend/src/components/business/TransferDialog.vue frontend/src/views/StockCountView.vue frontend/src/views/TransferView.vue frontend/tests/warehouse-extensions-views.spec.ts
git commit -m "feat: add count and transfer user interfaces"
```

### Task 9: Implement approval UI, documentation, migration application, and final verification

**Files:**
- Create: `frontend/src/components/business/ApprovalDialog.vue`
- Modify: `frontend/src/views/ApprovalView.vue`
- Modify: `frontend/tests/warehouse-extensions-views.spec.ts`
- Modify: `docs/后端开发文档.md`
- Modify: `backend/tests/test_migration_safety.py`

**Consumes:** Task 5 approval endpoints, Task 6 client, Task 7 routed page shell.

**Produces:** Usable approval center, migration/runbook documentation, complete automated verification and a safe authenticated smoke test.

- [ ] **Step 1: Write failing approval-page tests.**

```ts
it('lets a warehouse manager approve a pending task', async () => {
  vi.mocked(listApprovals).mockResolvedValue(pageOf([{ approval_task_id: 8, status: 'pending', business_type: 'transfer', business_summary: { order_no: 'TR-001', status: 'pending_approval' } }]))
  const wrapper = await mountExtension('/approvals', ['warehouse_manager'])
  await wrapper.get('[data-testid="approval-approve-8"]').trigger('click')
  await wrapper.get('[data-testid="approval-dialog-confirm"]').trigger('click')
  expect(approveApproval).toHaveBeenCalledWith(8, undefined)
})

it('blocks empty rejection comments on the client', async () => {
  const wrapper = await mountExtension('/approvals', ['warehouse_manager'])
  await wrapper.get('[data-testid="approval-reject-8"]').trigger('click')
  await wrapper.get('[data-testid="approval-dialog-confirm"]').trigger('click')
  expect(rejectApproval).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('驳回时必须填写审批意见')
})
```

Also assert a `warehouse_operator` sees an access explanation instead of decision buttons and every successful decision reloads list/detail from the server.

- [ ] **Step 2: Run tests and verify red.**

Run: `cd frontend; npm test -- --run tests/warehouse-extensions-views.spec.ts`  
Expected: FAIL because the dialog and decision controls are absent.

- [ ] **Step 3: Implement ApprovalDialog and wire ApprovalView.**

`ApprovalDialog.vue` props: `modelValue`, `mode: 'approve' | 'reject'`, `approval`, `submitting`; emits `confirm` with a trimmed `comment | undefined`. Reject mode must block blank comment with exactly “驳回时必须填写审批意见”; approve mode makes comment optional. Render only API-provided business summary fields.

`ApprovalView.vue` loads `listApprovals({status,business_type,page,page_size})`, uses `getApproval` for selected row detail, and allows actions only for `admin` / `warehouse_manager` on `pending` tasks. `approveApproval`/`rejectApproval` errors are displayed; successful actions refetch list and selected detail, never fabricate local state.

- [ ] **Step 4: Add a migration acceptance assertion and update backend documentation.**

```python
def test_extension_migration_declares_all_extension_tables():
    source = (Path(__file__).parents[1] / "alembic/versions/0002_stock_count_transfer_approval.py").read_text(encoding="utf-8")
    for table in ("stock_count_order", "stock_count_item", "transfer_order", "transfer_item", "approval_task"):
        assert f'"{table}"' in source
```

Append “盘点、调拨与审批扩展” to `docs/后端开发文档.md`: five tables, role rules, all API paths, state transitions, idempotency/ledger/audit guarantees, non-destructive migration command and acceptance checklist. Include only:

```powershell
cd backend
alembic upgrade head
pytest -q
```

State that the existing local environment config supplies the database URL and that credentials must never be included in docs or version control.

- [ ] **Step 5: Run all automated checks.**

```powershell
cd backend
pytest -q
cd ..\frontend
npm test -- --run
npm run build
```

Expected: backend tests pass, frontend tests pass, and `vue-tsc -b && vite build` exits 0. Record Vite bundle-size warnings as later performance work, not a functional failure.

- [ ] **Step 6: Apply the append-only migration to the configured local MySQL database.**

Run: `cd backend; alembic upgrade head`  
Expected: database reaches revision `0002_stock_count_transfer_approval`; no `DROP TABLE`, `DROP COLUMN`, or baseline schema script runs. Inspect only the five expected table names through the configured backend connection, never printing the database URL or credentials.

- [ ] **Step 7: Run an authenticated real-environment smoke test.**

Start FastAPI at `127.0.0.1:8000` and Vite at `127.0.0.1:5173` using existing project commands. Verify `GET /health` returns `{"status":"ok"}`. Log in using locally configured credentials without printing them. In a newly created isolated test product/location set only: submit a no-difference count; create/submit/execute a same-warehouse transfer; confirm statuses and ledger records through the UI/API. Do not mutate imported production-like records.

- [ ] **Step 8: Commit final UI and documentation.**

```powershell
git add frontend/src/components/business/ApprovalDialog.vue frontend/src/views/ApprovalView.vue frontend/tests/warehouse-extensions-views.spec.ts backend/tests/test_migration_safety.py docs/后端开发文档.md
git commit -m "feat: complete warehouse extension workflows"
```

## Plan Self-Review

### Spec coverage

| Confirmed requirement | Plan task(s) |
| --- | --- |
| Five additive tables, constraints, indexes, non-destructive migration | 1, 9 |
| JWT、角色、仓库范围及禁止自审（创建人/申请人不得审批自己的单据） | 2, 3, 4, 5 |
| Original response status/body on idempotency replay | 2; exercised by 3–5 and 9 |
| No-difference/variance stock-count state machine | 3 |
| Server book snapshot, re-lock on approval, count ledgers | 2, 3 |
| Same/cross warehouse classification and atomic transfer | 2, 4 |
| Unified approval task and approve/reject rules | 5, 9 |
| Dedicated UI routes, pages, dialogs, and true server refresh | 6, 7, 8, 9 |
| Audit logs, ledger consistency, lock/rollback protection | 2–5 |
| Backend documentation, complete test/build/migration/smoke verification | 9 |

### Placeholder scan

Every task names exact file paths, expected red/green test commands, state restrictions, response semantics, transaction boundaries, and verification criteria. No unresolved implementation decision remains.

### Type consistency

`ServiceResult` is shared by all new write services/routes. The identifiers are consistently `stock_count_order_id`, `transfer_order_id`, and `approval_task_id`. Ledger types/suffixes are consistently `count_gain`/`count_loss` and `transfer_out`/`transfer_in` with unique request-derived keys.

