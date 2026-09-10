# 智能 ERP 仓管系统后端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏已经导入的 `erp_wms` 数据的前提下，新增一个可启动、可鉴权、可查询真实库存并支持入库/出库库存闭环的 FastAPI 后端，并配套可执行的后端开发文档。

**Architecture:** 使用 FastAPI + SQLAlchemy 2.x + Alembic + MySQL 8，采用 API、Service、Repository、Model 分层。所有库存写操作统一进入 `InventoryService`，在 MySQL 事务中使用行锁、幂等记录、库存流水和审计日志；Redis 先作为可选扩展，不让缓存成为库存事实来源。

**Tech Stack:** Python 3.12、FastAPI、Pydantic Settings、SQLAlchemy 2.x、Alembic、PyMySQL、JWT、密码哈希、pytest、httpx、MySQL 8、可选 Redis。

**Spec:** `docs/后端开发文档.md`

## Global Constraints

- 不执行现有 `database/schema.sql`，因为它包含删除已有表的语句。
- 所有数据库结构变化必须通过 Alembic 增量迁移完成。
- 前端不直接访问 MySQL，只访问 `/api/v1`。
- 历史 `inbound_record` 和 `outbound_record` 不得重复改变 `stock_balance`。
- 所有正式库存变化必须同时写入 `stock_ledger`。
- 所有写接口必须要求 Bearer JWT 和 `Idempotency-Key`。
- 出库必须使用 MySQL 行锁校验可用库存，禁止并发超卖。
- 数据库密码不得写入源码、文档或提交的 `.env` 文件。
- AI 功能本轮只保留扩展边界，不允许 AI 直接修改库存或执行原始 SQL。
- 每个新增行为必须先写失败测试并确认失败，再写最小实现。

---

### Task 1: 后端设计文档和工程骨架

**Files:**
- Create: `docs/后端开发文档.md`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/README.md`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces `create_app() -> FastAPI` and `GET /health`.
- Produces configuration object `Settings` loaded from environment variables.
- Produces pytest test entry point.

- [ ] Step 1: 写 `test_health.py`，断言应用提供 `/health` 并返回 `{"status": "ok"}`。
- [ ] Step 2: 运行 `pytest backend/tests/test_health.py -q`，确认因为 `backend.app.main` 不存在而失败。
- [ ] Step 3: 创建最小 FastAPI 应用、配置、依赖和项目元数据。
- [ ] Step 4: 再次运行健康检查测试，确认通过。
- [ ] Step 5: 补充开发文档中的环境变量、启动命令和当前范围。

### Task 2: 数据库连接、ORM 基础模型和增量迁移

**Files:**
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/models/catalog.py`
- Create: `backend/app/db/models/inventory.py`
- Create: `backend/app/db/models/operations.py`
- Create: `backend/app/db/models/security.py`
- Create: `backend/app/db/models/audit.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_add_backend_core.py`
- Create: `backend/tests/test_database_config.py`
- Modify: `docs/后端开发文档.md`

**Interfaces:**
- Produces `get_session()` and `get_db()`.
- Produces SQLAlchemy mappings for existing tables and new backend tables.
- Produces Alembic migration that is additive and safe for the imported database.

New or changed database structures:

```text
user_account
role
user_role
user_warehouse_scope
inbound_order
inbound_item
outbound_order
outbound_item
picking_task
audit_log
idempotency_record
```

Additive change to `stock_balance`:

```text
reserved_quantity INT UNSIGNED NOT NULL DEFAULT 0
```

- [ ] Step 1: 写配置测试，验证没有密码时不会把默认 root 密码写死到配置对象中，并验证数据库 URL 可由环境变量覆盖。
- [ ] Step 2: 运行测试，确认配置模块尚不存在而失败。
- [ ] Step 3: 实现配置、SQLAlchemy engine/session、基础模型和迁移。
- [ ] Step 4: 运行配置测试和 Alembic 静态检查。
- [ ] Step 5: 使用临时测试数据库执行迁移；不得对生产 `erp_wms` 执行 destructive migration。

### Task 3: 认证、密码哈希和 RBAC

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/v1/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/scripts/seed_roles.py`
- Create: `backend/scripts/create_admin.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/test_permissions.py`

**Interfaces:**
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `get_current_user()` dependency
- `require_roles(*roles)` dependency
- `hash_password()` / `verify_password()` / `create_access_token()`

- [ ] Step 1: 写登录成功、密码错误、无 token 和角色拒绝测试。
- [ ] Step 2: 运行认证测试，确认接口和安全函数不存在而失败。
- [ ] Step 3: 实现用户查询、密码哈希、JWT、依赖注入和角色校验。
- [ ] Step 4: 运行认证测试，确认全部通过。
- [ ] Step 5: 加入初始角色和管理员创建脚本，不把管理员密码写进源码。

### Task 4: 商品、仓库、库位和导入批次查询接口

**Files:**
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/catalog.py`
- Create: `backend/app/schemas/imports.py`
- Create: `backend/app/repositories/catalog_repository.py`
- Create: `backend/app/repositories/import_repository.py`
- Create: `backend/app/api/v1/products.py`
- Create: `backend/app/api/v1/warehouses.py`
- Create: `backend/app/api/v1/imports.py`
- Create: `backend/tests/test_catalog_api.py`
- Create: `backend/tests/test_import_api.py`

**Interfaces:**
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/warehouses`
- `GET /api/v1/locations`
- `GET /api/v1/imports`
- `GET /api/v1/imports/{batch_id}`

- [ ] Step 1: 写分页、筛选、详情和不存在资源的失败测试。
- [ ] Step 2: 运行测试，确认路由尚不存在而失败。
- [ ] Step 3: 实现查询 repository、Pydantic response schema 和路由。
- [ ] Step 4: 运行测试，确认真实查询结果结构正确。
- [ ] Step 5: 将接口参数、响应和错误码写入后端开发文档。

### Task 5: 库存查询、汇总和流水接口

**Files:**
- Create: `backend/app/schemas/inventory.py`
- Create: `backend/app/repositories/inventory_repository.py`
- Create: `backend/app/services/inventory_query_service.py`
- Create: `backend/app/api/v1/inventory.py`
- Create: `backend/app/api/v1/dashboard.py`
- Create: `backend/tests/test_inventory_query.py`
- Create: `backend/tests/test_dashboard_api.py`

**Interfaces:**
- `GET /api/v1/inventory/balances`
- `GET /api/v1/inventory/{product_id}/availability`
- `GET /api/v1/inventory/ledgers`
- `GET /api/v1/dashboard/summary`

- [ ] Step 1: 写库存分页、可用量计算、流水筛选和看板汇总测试。
- [ ] Step 2: 运行测试确认失败。
- [ ] Step 3: 实现 `available_quantity = quantity - reserved_quantity` 查询逻辑。
- [ ] Step 4: 运行库存测试确认通过。
- [ ] Step 5: 检查查询不会把历史收发记录重复累加到当前库存。

### Task 6: 统一幂等、审计和库存事务服务

**Files:**
- Create: `backend/app/schemas/audit.py`
- Create: `backend/app/services/idempotency_service.py`
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/services/inventory_service.py`
- Create: `backend/app/api/v1/audit_logs.py`
- Create: `backend/tests/test_idempotency.py`
- Create: `backend/tests/test_inventory_service.py`
- Create: `backend/tests/test_audit_service.py`

**Interfaces:**
- `InventoryService.apply_inbound(...)`
- `InventoryService.reserve_outbound(...)`
- `InventoryService.complete_outbound(...)`
- `IdempotencyService.get_or_create(...)`
- `AuditService.record(...)`
- `GET /api/v1/audit-logs`

- [ ] Step 1: 写重复幂等键、库存不足、库存流水和审计记录测试。
- [ ] Step 2: 运行测试确认失败。
- [ ] Step 3: 实现同一事务内的行锁、数量校验、库存更新、流水和审计。
- [ ] Step 4: 运行服务测试确认通过。
- [ ] Step 5: 增加并发集成测试；如果本机无可用测试数据库，明确标记需要配置 `TEST_DATABASE_URL`，不能伪称已验证。

### Task 7: 入库单和收货确认

**Files:**
- Create: `backend/app/schemas/inbounds.py`
- Create: `backend/app/repositories/inbound_repository.py`
- Create: `backend/app/services/inbound_service.py`
- Create: `backend/app/api/v1/inbounds.py`
- Create: `backend/tests/test_inbound_api.py`

**Interfaces:**
- `GET /api/v1/inbounds`
- `POST /api/v1/inbounds`
- `GET /api/v1/inbounds/{inbound_id}`
- `POST /api/v1/inbounds/{inbound_id}/confirm`

- [ ] Step 1: 写草稿创建、确认增加库存、重复确认和状态错误测试。
- [ ] Step 2: 运行测试确认失败。
- [ ] Step 3: 实现入库单、明细和确认流程，调用 `InventoryService.apply_inbound()`。
- [ ] Step 4: 运行测试确认库存只增加一次并且有 ledger/audit。
- [ ] Step 5: 在文档中补充入库状态机和请求示例。

### Task 8: 出库、库存分配和拣货确认

**Files:**
- Create: `backend/app/schemas/outbounds.py`
- Create: `backend/app/repositories/outbound_repository.py`
- Create: `backend/app/services/outbound_service.py`
- Create: `backend/app/api/v1/outbounds.py`
- Create: `backend/app/api/v1/picking_tasks.py`
- Create: `backend/tests/test_outbound_api.py`
- Create: `backend/tests/test_outbound_concurrency.py`

**Interfaces:**
- `GET /api/v1/outbounds`
- `POST /api/v1/outbounds`
- `GET /api/v1/outbounds/{outbound_id}`
- `POST /api/v1/outbounds/{outbound_id}/allocate`
- `GET /api/v1/picking-tasks`
- `POST /api/v1/picking-tasks/{task_id}/confirm`
- `POST /api/v1/outbounds/{outbound_id}/complete`

- [ ] Step 1: 写库存不足、成功分配、重复分配、拣货确认和完成扣减测试。
- [ ] Step 2: 运行测试确认失败。
- [ ] Step 3: 实现 reserved quantity、库存行锁、任务状态机和出库服务。
- [ ] Step 4: 运行测试确认出库不会超卖，完成只扣减一次。
- [ ] Step 5: 对 MySQL 集成测试执行并发验证，并记录实际测试数据库配置。

### Task 9: 预警、错误处理、CORS 和前端联调契约

**Files:**
- Create: `backend/app/schemas/alerts.py`
- Create: `backend/app/api/v1/alerts.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/app/core/middleware.py`
- Create: `backend/tests/test_errors.py`
- Create: `backend/tests/test_alerts_api.py`
- Modify: `frontend/README.md` only if the final endpoint contract changes
- Modify: `docs/后端开发文档.md`

**Interfaces:**
- `GET /api/v1/alerts`
- Unified error envelope:

```json
{
  "code": "INVENTORY_INSUFFICIENT",
  "message": "可用库存不足",
  "request_id": "...",
  "details": {}
}
```

- [ ] Step 1: 写统一错误、权限错误、库存不足和低库存预警测试。
- [ ] Step 2: 运行测试确认失败。
- [ ] Step 3: 实现异常处理器、request id、中间件、CORS 和预警查询。
- [ ] Step 4: 运行测试确认错误响应稳定。
- [ ] Step 5: 对照前端预留 API 契约更新文档。

### Task 10: 操作脚本、完整文档和验证

**Files:**
- Create: `backend/scripts/check_database.py`
- Create: `backend/scripts/run_migrations.py`
- Create: `backend/scripts/smoke_test.py`
- Modify: `backend/README.md`
- Modify: `docs/后端开发文档.md`
- Modify: `database/README.md` to additive-migration warning
- Create: `backend/tests/test_openapi.py`

**Interfaces:**
- `python -m scripts.check_database`
- `python -m scripts.run_migrations`
- `python -m scripts.smoke_test`

- [ ] Step 1: 写 OpenAPI 路由完整性测试和脚本行为测试。
- [ ] Step 2: 运行测试确认脚本或接口清单不完整而失败。
- [ ] Step 3: 完成脚本、文档、启动示例和 API 清单。
- [ ] Step 4: 运行完整测试、类型检查、Alembic 检查和应用启动验证。
- [ ] Step 5: 使用最新命令输出逐项核对验收标准；对无法验证的真实数据库项明确说明，不作无证据的完成声明。

---

## Verification Commands

```powershell
cd backend
python -m pytest -q
python -m compileall app scripts
python -m alembic check
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果配置了测试数据库，还要运行：

```powershell
$env:TEST_DATABASE_URL = 'mysql+pymysql://<app-user>:<password>@127.0.0.1:3306/erp_wms_test'
python -m pytest -q -m integration
```

## Out of Scope for This Delivery

- LangGraph/LLM 实际调用；
- AI 直接执行库存操作；
- 完整采购、销售、财务和生产模块；
- 批次、有效期、序列号；
- 在没有明确业务规则时擅自实现复杂审批流；
- 重新导入或重建当前已经存在的 Mega Star 数据。
