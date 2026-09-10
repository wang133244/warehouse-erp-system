# 盘点、调拨与风险分级审批设计

**日期：** 2026-09-10  
**范围：** 智能 ERP 仓管系统第一阶段扩展：盘点管理、调拨管理、审批中心。  
**状态：** 已完成设计确认，等待规格文档审核。

## 1. 背景与目标

系统已有商品、库位、库存余额、库存流水、入库、出库、拣货、审计和幂等能力。本次补齐实际仓储作业中的盘点、库内/跨仓调拨及统一审批闭环。

本阶段目标：

1. 让仓管人员可以创建、录入并提交盘点单，以及创建、提交并执行调拨单。
2. 把有库存影响的盘点差异和跨仓调拨纳入风险分级审批；同仓调拨不审批但必须显式执行。
3. 确保任何库存变化均在数据库事务内完成，并留下库存流水、审计日志和可追溯业务单据。
4. 为前端已有的 `/counting`、`/transfer`、`/approvals` 路由提供真实 API，不伪造成功状态。

本阶段不包含真实运营图表/前端分包优化，也不包含 AI 智能工作台；它们属于后续阶段。

## 2. 方案选择

采用已确认的**方案 B：按风险分级审批**。

- 无差异盘点：自动完成，无库存变化，无审批任务。
- 有差异盘点：提交后等待审批；仅审批通过时调整库存。
- 同仓调拨：提交后可执行，无审批；库存变化仍需人工明确执行。
- 跨仓调拨：提交后等待审批；审批通过后变为可执行，仍需人工明确执行。

该方案避免了低风险业务被不必要地阻塞，同时把影响库存账实、跨仓资产归属的动作置于可审计的审批链中。

## 3. 角色与授权

在现有 `user_account`、`role`、`user_role` 基础上使用以下角色编码：

| 角色 | 权限 |
| --- | --- |
| `admin` | 创建、提交、执行、审批、查看全部单据与审批任务。 |
| `warehouse_operator` | 在其仓库授权范围内创建、编辑、提交盘点和调拨；不能审批。 |
| `warehouse_manager` | 在其仓库授权范围内查看单据与审批；可以批准或驳回待审批任务；不承担创建限制的豁免。 |

授权规则：

- 所有业务接口都必须验证 JWT；未认证为 `401`，无权限或超出仓库范围为 `403`。
- `admin` 不受 `user_warehouse_scope` 限制；其余角色涉及的每个库位所属仓库必须在该用户授权范围内。
- 创建人不得审批自己提交的盘点差异或跨仓调拨；这种情况返回 `403`，由其他有审批权用户处理。
- `POST` 写操作均需 `Idempotency-Key` 请求头；相同用户、相同键的重放返回已保存的原响应，不重复修改业务数据。

## 4. 业务状态机

### 4.1 盘点单

```text
draft → counting → submitted
submitted ──差异全为 0──→ completed
submitted ──存在差异──→ pending_approval
pending_approval ──approve──→ applied
pending_approval ──reject──→ rejected
```

- `draft`：新建，允许修改明细；首次保存至少一条含实盘数的明细后转为 `counting`。
- `counting`：允许继续修改明细；提交后不可再编辑。
- `submitted` 仅作为提交处理中的短暂内部状态，不应在最终 API 响应中长期可见。
- `completed`：账实相符，完成但不产生库存调整。
- `pending_approval`：存在至少一项差异，等待审批。
- `applied`：审批通过后已完成库存调整。
- `rejected`：审批驳回；不改变库存，单据不可再次提交。需要重新盘点时新建单据。

盘点提交规则：

1. 每一明细的 `counted_quantity` 必须为整数且不小于 0。
2. 后端在提交事务内重新读取并锁定每个商品/库位的 `stock_balance`，将当时 `quantity` 写入 `book_quantity`；客户端传来的账面数不被信任。
3. `variance_quantity = counted_quantity - book_quantity`。
4. 所有差异为 0 时：状态置为 `completed`，写审计日志；不创建审批任务，不写 `stock_ledger`。
5. 存在任一差异时：状态置为 `pending_approval` 并创建一个审批任务；此时不修改库存、不写库存流水。
6. 审批通过时，服务在一个新事务中再次锁定库存余额，并以当前库存为流水 `before_quantity`；计算目标值为 `counted_quantity`。如果在等待期间库存已变化，仍以实盘目标数为准；流水中保留实际调整差额，审计日志同时记录提交时账面数和审批执行时账面数。
7. 审批通过会为每个有差异的明细生成一条流水：正差异为 `count_gain`，负差异为 `count_loss`。流水幂等键由审批请求键派生为 `request-key:stock-count-item-{id}:apply`，以兼容现有 `stock_ledger.idempotency_key` 的唯一约束。不允许将调整后的库存变为负数；若实盘数已满足非负要求，则目标库存非负。

### 4.2 调拨单

```text
draft → submitted
submitted ──同仓──→ executable → completed
submitted ──跨仓──→ pending_approval
pending_approval ──approve──→ executable → completed
pending_approval ──reject──→ rejected
```

- `draft`：允许修改明细。
- `submitted`：仅提交处理中的短暂内部状态。
- `executable`：满足执行条件，等待人工执行。
- `pending_approval`：跨仓调拨已提交，等待审批。
- `completed`：已执行全部明细。
- `rejected`：审批驳回；不改变库存，不能再次执行或提交。

调拨规则：

1. 每条明细的数量必须为整数且大于 0；源库位与目标库位不得相同。
2. 源、目标库位与商品必须存在。当前基础数据模型没有启停用字段；本阶段不新增该字段，也不做“可用状态”判断。
3. “同仓”以源、目标库位关联的 `warehouse_id` 相同为准；同仓提交后直接进入 `executable`。
4. “跨仓”以两个 `warehouse_id` 不同为准；提交后创建审批任务并进入 `pending_approval`。
5. 调拨单只允许同仓或全跨仓明细，不能混合。若含不同类型明细，创建/提交返回 `422`，用户应拆分为不同调拨单。这使一张单的审批状态与执行语义保持唯一。
6. 执行时按稳定顺序锁定每个涉及的 `stock_balance` 行，避免并发调拨死锁；校验源库位 `quantity - reserved_quantity >= quantity`。
7. 对每个明细，在同一事务中减少源库存、增加目标库存、写两条库存流水、写审计日志，最后改为 `completed`。任一步失败必须回滚整个调拨单。
8. 每条明细生成两条流水：源库位 `transfer_out`（负数）和目标库位 `transfer_in`（正数）。流水的幂等键由请求键派生为 `request-key:transfer-item-{id}:out` 与 `...:in`，以兼容现有 `stock_ledger.idempotency_key` 的唯一约束。

## 5. 审批中心

审批任务只引用业务单据，不复制盘点或调拨明细。业务类型为：

- `stock_count`
- `transfer`

状态机：

```text
pending → approved
pending → rejected
```

审批规则：

- `approve` 和 `reject` 仅接受 `pending` 状态的审批任务。
- 审批意见 `comment`：批准时可选，驳回时必填，去除首尾空格后长度 1–500。
- 批准盘点差异：调用盘点应用服务，在同一事务中调整库存、记录流水和审计，并将审批任务改为 `approved`、盘点单改为 `applied`。
- 批准跨仓调拨：将审批任务改为 `approved`，调拨单改为 `executable`；不调整库存。
- 驳回任一类型：任务改为 `rejected`，业务单改为 `rejected`；只写审计，不调整库存。
- 任一业务单最多对应一个审批任务，数据库唯一约束保证这一点。

## 6. 数据模型与迁移

新建 Alembic 迁移 `0002_stock_count_transfer_approval.py`。迁移仅新增表、索引和约束，严禁执行既有 `database/schema.sql` 中的破坏性建表脚本。

### 6.1 `stock_count_order`

| 字段 | 说明 |
| --- | --- |
| `stock_count_order_id` | 主键。 |
| `order_no` | 唯一单号，格式 `SC-YYYYMMDD-######`。 |
| `status` | 盘点状态。 |
| `created_by` | 创建用户。 |
| `submitted_by` / `submitted_at` | 提交人及提交时间。 |
| `completed_by` / `completed_at` | 无差异完成或审批应用的执行人及时间。 |
| `note` | 可选备注。 |
| `created_at` / `updated_at` | 审计时间。 |

索引：`order_no` 唯一；`status, created_at` 组合索引。

### 6.2 `stock_count_item`

| 字段 | 说明 |
| --- | --- |
| `stock_count_item_id` | 主键。 |
| `stock_count_order_id` | 所属盘点单。 |
| `product_id` / `location_id` | 被盘点的商品与库位。 |
| `book_quantity` | 提交时由后端锁定读取的账面库存；草稿阶段为空。 |
| `counted_quantity` | 实盘库存，非负。 |
| `variance_quantity` | 提交时的实盘减账面差异；草稿阶段为空。 |
| `created_at` / `updated_at` | 时间戳。 |

约束：`(stock_count_order_id, product_id, location_id)` 唯一。

### 6.3 `transfer_order`

| 字段 | 说明 |
| --- | --- |
| `transfer_order_id` | 主键。 |
| `order_no` | 唯一单号，格式 `TR-YYYYMMDD-######`。 |
| `status` | 调拨状态。 |
| `transfer_scope` | `intra_warehouse` 或 `cross_warehouse`，提交时确定后不可修改。 |
| `created_by` | 创建用户。 |
| `submitted_by` / `submitted_at` | 提交记录。 |
| `executed_by` / `executed_at` | 执行记录。 |
| `note` | 可选备注。 |
| `created_at` / `updated_at` | 时间戳。 |

索引：`order_no` 唯一；`status, created_at` 组合索引；`transfer_scope, status` 组合索引。

### 6.4 `transfer_item`

| 字段 | 说明 |
| --- | --- |
| `transfer_item_id` | 主键。 |
| `transfer_order_id` | 所属调拨单。 |
| `product_id` | 商品。 |
| `source_location_id` / `target_location_id` | 源、目标库位。 |
| `quantity` | 正整数。 |
| `created_at` | 时间戳。 |

约束：`(transfer_order_id, product_id, source_location_id, target_location_id)` 唯一。

### 6.5 `approval_task`

| 字段 | 说明 |
| --- | --- |
| `approval_task_id` | 主键。 |
| `business_type` / `business_id` | 被审批业务单的多态引用。 |
| `status` | `pending`、`approved`、`rejected`。 |
| `requested_by` / `requested_at` | 申请人和申请时间。 |
| `decided_by` / `decided_at` | 审批人和审批时间。 |
| `comment` | 审批意见。 |
| `created_at` / `updated_at` | 时间戳。 |

约束：`(business_type, business_id)` 唯一；索引：`status, created_at`、`requested_by, status`。

所有业务单、明细、审批任务均通过外键与现有用户、商品、库位表关联。单据状态和数值校验同时由 Pydantic、服务层和数据库约束（非空、唯一、外键、盘点实盘数非负、调拨数量正数）保障；不依赖前端校验。

## 7. API 契约

所有接口位于 `/api/v1`，使用现有 JSON 响应、异常处理、JWT 依赖和分页约定。列表接口支持 `page`、`page_size`、`status`，以及适用时的 `order_no` / `business_type` 筛选；响应包含 `items`、`total`、`page`、`page_size`。

| 方法 | 路径 | 作用 | 允许角色 |
| --- | --- | --- | --- |
| `GET` | `/stock-counts` | 分页查询盘点单。 | 三类角色 |
| `POST` | `/stock-counts` | 创建草稿盘点单和明细。 | `admin`、`warehouse_operator` |
| `GET` | `/stock-counts/{count_id}` | 查询盘点单和明细。 | 三类角色 |
| `PUT` | `/stock-counts/{count_id}` | 覆盖保存草稿/盘点中的备注和明细。 | `admin`、创建人对应权限的 `warehouse_operator` |
| `POST` | `/stock-counts/{count_id}/submit` | 提交盘点。 | `admin`、创建人对应权限的 `warehouse_operator` |
| `GET` | `/transfers` | 分页查询调拨单。 | 三类角色 |
| `POST` | `/transfers` | 创建草稿调拨单和明细。 | `admin`、`warehouse_operator` |
| `GET` | `/transfers/{transfer_id}` | 查询调拨单和明细。 | 三类角色 |
| `PUT` | `/transfers/{transfer_id}` | 覆盖保存草稿中的备注和明细。 | `admin`、创建人对应权限的 `warehouse_operator` |
| `POST` | `/transfers/{transfer_id}/submit` | 提交调拨并决定是否需审批。 | `admin`、创建人对应权限的 `warehouse_operator` |
| `POST` | `/transfers/{transfer_id}/execute` | 执行处于 `executable` 的调拨。 | `admin`、`warehouse_operator` |
| `GET` | `/approvals` | 分页查询审批任务。 | `admin`、`warehouse_manager` |
| `GET` | `/approvals/{approval_id}` | 查询审批任务及业务摘要。 | `admin`、`warehouse_manager` |
| `POST` | `/approvals/{approval_id}/approve` | 批准待办任务。 | `admin`、`warehouse_manager` |
| `POST` | `/approvals/{approval_id}/reject` | 驳回待办任务。 | `admin`、`warehouse_manager` |

写接口统一要求：

```http
Authorization: Bearer <JWT>
Idempotency-Key: <客户端生成的 UUID>
Content-Type: application/json
```

不含明细的盘点创建请求返回 `draft`；创建请求包含初始明细，或在 `draft` 中首次保存明细时，盘点单转为 `counting`。草稿和盘点中的明细通过 `PUT` 覆盖保存。调拨单始终在 `draft` 中编辑，直至提交。

创建盘点请求示例：

```json
{
  "note": "月末循环盘点",
  "items": [
    {"product_id": 101, "location_id": 12, "counted_quantity": 20}
  ]
}
```

创建调拨请求示例：

```json
{
  "note": "A 区补货",
  "items": [
    {
      "product_id": 101,
      "source_location_id": 12,
      "target_location_id": 23,
      "quantity": 8
    }
  ]
}
```

审批决定请求示例：

```json
{"comment": "盘点记录与现场复核一致"}
```

错误语义：参数或状态不合法为 `422` / `409`，不存在资源为 `404`，认证与授权分别为 `401` / `403`，可用库存不足为 `409`。幂等重放保持第一次响应的状态码和响应体。

## 8. 后端实现边界

新增以下模块，沿用现有路由、schema、service、repository/ORM 模式：

```text
backend/app/api/v1/stock_counts.py
backend/app/api/v1/transfers.py
backend/app/api/v1/approvals.py
backend/app/services/stock_count_service.py
backend/app/services/transfer_service.py
backend/app/services/approval_service.py
backend/app/schemas/stock_counts.py
backend/app/schemas/transfers.py
backend/app/schemas/approvals.py
backend/alembic/versions/0002_stock_count_transfer_approval.py
```

- `inventory_service` 是唯一允许变更 `stock_balance` 与新增 `stock_ledger` 的基础服务；盘点和调拨服务调用其受控的批量/行锁操作，不直接散写库存 SQL。
- `stock_count_service` 只管理盘点状态、账面快照、差异及审批应用入口。
- `transfer_service` 只管理调拨状态、仓库范围判断、执行编排。
- `approval_service` 只管理审批任务、审批人校验和分派给对应业务服务。
- 路由层只做认证、参数解析、权限依赖和 HTTP 响应映射；不承载业务事务。
- `main.py` 注册新增路由；模型模块导入到 Alembic 元数据，保证自动生成与测试建表可识别。

## 9. 前端实现边界

新增而非继续膨胀 `WorkspaceView.vue`：

```text
frontend/src/api/warehouse-extensions.ts
frontend/src/views/StockCountView.vue
frontend/src/views/TransferView.vue
frontend/src/views/ApprovalView.vue
frontend/src/components/business/StockCountDialog.vue
frontend/src/components/business/TransferDialog.vue
frontend/src/components/business/ApprovalDialog.vue
```

页面交互：

- **盘点页**：列表、状态筛选、新建/录入弹窗、详情和提交操作。待审批、已应用、已驳回单据只读。
- **调拨页**：列表、状态筛选、新建弹窗、详情、提交和执行操作。仅 `executable` 状态展示执行按钮。
- **审批页**：待办优先列表、单据摘要/明细详情、批准/驳回弹窗；驳回不填意见时不可提交。
- 前端根据登录用户角色隐藏无权限按钮，但后端仍是最终授权边界。
- API 客户端自动附带 JWT；每次写操作生成一个新的 UUID 作为 `Idempotency-Key`，网络重试复用同一个请求键。
- 成功操作后重新请求详情和列表；失败展示后端错误，不在本地伪造状态迁移。

## 10. 一致性、并发与审计

1. 任何库存变化必须使用数据库事务和 `SELECT ... FOR UPDATE` 锁定相关库存行。
2. 调拨一次执行涉及的余额行按 `(product_id, location_id)` 排序锁定，降低死锁风险。
3. 缺少目标库存行时，在事务内创建零余额行后再次锁定；同一 `(product_id, location_id)` 唯一约束防止重复记录。
4. 盘点审批和调拨执行不可绕过 `stock_ledger`；库存变化与流水写入必须同事务提交。
5. 每个关键动作写 `audit_log`，包括创建、提交、审批通过、审批驳回、库存调整和调拨执行；记录请求 ID、操作者、业务前后状态、库存前后数量及必要业务上下文。
6. 幂等记录与业务状态机共同防重：同一键不会重放写入；不同键的重复调用会因状态已迁移而返回 `409`，不产生第二次库存变化。
7. 不记录或提交数据库密码、JWT、管理员密码、token 或用户敏感信息。

## 11. 测试与验收

### 11.1 后端单元与 API 测试

- 盘点：无差异自动完成；正/负差异进入待审批；驳回不改库存；批准后库存、流水和审计一致；负实盘数被拒绝。
- 调拨：同仓提交转可执行；跨仓提交创建审批；批准跨仓后仅变可执行；执行时双向库存、两条流水、审计和状态原子一致；库存不足回滚。
- 审批：角色授权、自审禁止、重复审批、重复提交、幂等重放。
- 并发：对同一源库存的并发调拨或盘点审批，最终库存不为负且流水总和与余额变更一致。
- 迁移：从现有 `0001` 升级后五张新表、索引和约束可用，回滚仅删除本迁移新增对象。

### 11.2 前端测试与构建

- API 模块使用正确路径、JWT 和幂等头。
- 三个页面按角色和状态正确呈现按钮与只读状态。
- 关键成功/失败流程测试：提交盘点、提交/执行调拨、审批批准和驳回。
- 执行现有前端 Vitest、后端 pytest 和生产构建；最后在已启动的 MySQL、FastAPI、Vite 环境中完成登录后真实冒烟验证。

## 12. 非目标与后续阶段

本实现不更改已有入库、出库、拣货流程的状态机，不做历史数据重算，也不提供 AI 直接执行库存变更。

下一阶段可在本阶段数据基础上实现：

1. 看板真实运营指标、图表数据接口、路由级代码分包与主包体积优化。
2. 仅通过既有业务 API 的 AI 查询、分析与草稿生成；AI 不执行原始 SQL、不直接改库存，所有建议仍走审批与审计链路。




