# 前端接入 FastAPI 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Vue 3 前端从静态原型接入已验证的 FastAPI + MySQL 后端，形成登录、查询、看板、入库、出库、拣货的最小可用闭环。

**Architecture:** 使用原生 `fetch` 建立统一 API 客户端，由 Pinia 保存 token 和当前用户，路由守卫保护业务页面。`WorkspaceView` 按 `route.path` 分发到轻量 API 模块，并把后端返回的 ID 转换为用户可读编码；写操作统一携带 `Authorization` 和 `Idempotency-Key`。

**Tech Stack:** Vue 3、TypeScript、Pinia、Vue Router、Element Plus、Vitest、FastAPI。

**Spec:** 用户已批准“正式接起来”的方向；后端契约以 `backend/app/api/v1/*` 和 `docs/后端开发文档.md` 为准。

## Global Constraints

- 前端不得直连 MySQL，只能访问 FastAPI。
- 除 `/health`、`/auth/login`、`/dashboard/summary` 外，接口默认需要 Bearer token。
- 所有写接口必须生成唯一 `Idempotency-Key`。
- 不得把数据库密码、管理员密码或 JWT token 写入源码、测试快照或文档。
- 不执行 `database/schema.sql`。
- 查询页优先接入：看板、商品、库位、库存、流水、入库、出库、拣货、导入、审计、预警。

---

### Task 1: API 基础层与认证闭环

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Modify: `frontend/src/stores/app.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/layouts/AppShell.vue`
- Test: `frontend/tests/api-client.spec.ts`
- Test: `frontend/tests/auth-store.spec.ts`
- Test: `frontend/tests/router-guard.spec.ts`

**Interfaces:**
- `request<T>(path, options)`：自动拼接 `VITE_API_BASE_URL`、注入 token、解析错误 envelope。
- `login(username, password)`、`fetchCurrentUser()`、`logout()`。
- Pinia store：`token`、`currentUser`、`login()`、`logout()`、`restoreSession()`。

- [ ] 写失败测试：客户端带 token、写请求带幂等键、错误 message 可读。
- [ ] 写失败测试：登录成功保存 token 与用户，登出清理状态。
- [ ] 写失败测试：未登录访问业务页跳转 `/login`，已登录访问 `/login` 跳转 `/dashboard`。
- [ ] 实现最小代码并让测试通过。
- [ ] 将登录页、顶栏用户、退出登录接入真实 API。

### Task 2: 查询 API 与数据转换

**Files:**
- Create: `frontend/src/api/catalog.ts`
- Create: `frontend/src/api/inventory.ts`
- Create: `frontend/src/api/operations.ts`
- Create: `frontend/src/utils/format.ts`
- Test: `frontend/tests/api-modules.spec.ts`

**Interfaces:**
- `listProducts`、`listWarehouses`、`listLocations`、`listImports`。
- `getDashboardSummary`、`listBalances`、`listLedgers`、`listAlerts`。
- `listInbounds`、`getInbound`、`createInbound`、`confirmInbound`。
- `listOutbounds`、`getOutbound`、`createOutbound`、`allocateOutbound`、`completeOutbound`。
- `listPickingTasks`、`confirmPickingTask`。

- [ ] 写失败测试：每个模块调用正确路径和参数。
- [ ] 写失败测试：写方法自动携带 `Idempotency-Key`。
- [ ] 实现类型和最小请求封装。

### Task 3: 工作台真实查询

**Files:**
- Modify: `frontend/src/views/WorkspaceView.vue`
- Modify: `frontend/src/components/business/FilterPanel.vue`
- Modify: `frontend/src/config/pages.ts`
- Test: `frontend/tests/workspace-integration.spec.ts`

**Interfaces:**
- `WorkspaceView` 暴露数据加载、筛选、分页、行操作处理。
- `FilterPanel` 支持 `v-model:keyword`、查询、重置。

- [ ] 写失败测试：看板显示后端 summary 数字。
- [ ] 写失败测试：商品页显示真实 SKU 和总数。
- [ ] 写失败测试：筛选输入可编辑并触发查询。
- [ ] 实现按路径分发 API 调用、ID 到编码映射、分页和错误提示。

### Task 4: 最小写操作闭环

**Files:**
- Modify: `frontend/src/components/business/OperationDialog.vue`
- Modify: `frontend/src/views/WorkspaceView.vue`
- Test: `frontend/tests/operation-dialog.spec.ts`

**Interfaces:**
- 入库表单：`order_no`、`product_id`、`location_id`、`quantity`、`note`。
- 出库表单：`order_no`、`customer_id`、`product_id`、`quantity`、`note`。
- 行操作：入库草稿确认、出库草稿分配、出库已分配完成、拣货任务确认。

- [ ] 写失败测试：入库/出库表单可编辑并提交 payload。
- [ ] 写失败测试：行状态按钮触发对应 API。
- [ ] 实现表单、提交、成功/失败提示、成功后刷新。

### Task 5: 全量验证与联调文档

**Files:**
- Modify: `frontend/README.md`
- Modify: `docs/后端开发文档.md`

- [ ] 运行 `npm test -- --run`。
- [ ] 运行 `npm run build`。
- [ ] 启动 FastAPI 与 Vite，验证登录、看板、核心表格、写操作。
- [ ] 更新启动与联调说明。
