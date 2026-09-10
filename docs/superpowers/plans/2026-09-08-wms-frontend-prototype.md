# 智能 ERP 仓管系统前端界面原型实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建可运行、可浏览全部仓储业务页面的 Vue 3 前端原型，为 FastAPI、MySQL、Redis 与 LangGraph 后续联调保留清晰边界。

**Architecture:** Vue 3 单页应用以全局后台框架、配置化页面定义和统一空状态为核心。所有列表展示 Mega Star 对应的真实字段表头，但不填充任何业务记录；写操作仅展示表单和“后端接口尚未接入”提示。

**Tech Stack:** Vue 3、TypeScript、Vite、Element Plus、Vue Router、Pinia、Vitest、Vue Test Utils。

**Spec:** `frontend/README.md`

## Global Constraints

- 不创建 `src/mocks`，不使用假数据、JSON、LocalStorage 或内存数组模拟业务事实。
- 不连接 MySQL、Redis、FastAPI；不执行 SQL。
- 使用真实业务字段、流程按钮、表单和空状态设计页面。
- 不伪造登录、库存变化、单据状态、审批结果或 AI 回答。
- 所有提交行为统一提示后端/AI 服务尚未接入。

### Task 1: 工程、路由与全局布局

**Files:** `frontend/package.json`、`frontend/src/main.ts`、`frontend/src/App.vue`、`frontend/src/router/index.ts`、`frontend/src/layouts/AppShell.vue`、全局样式。

- [ ] 先写应用壳、菜单和库存路由的失败测试。
- [ ] 初始化 Vite、Vue Router、Pinia、Element Plus 和测试配置。
- [ ] 实现顶部栏、侧边栏、面包屑、响应式菜单及统一未接入弹窗。
- [ ] 运行测试，确认应用壳和路由通过。

### Task 2: 查询与主数据页面

**Files:** `frontend/src/views/` 下的看板、商品、库位、库存和库存流水页面，以及筛选、统计卡、空状态组件。

- [ ] 先写“库存页面含系统 SKU、实际库存数量和暂无库存数据”的失败测试。
- [ ] 实现表头、筛选区、统计卡、图表占位和详情按钮。
- [ ] 数据区统一显示空状态；查询不制造记录。
- [ ] 运行测试，确认字段和无数据边界通过。

### Task 3: 作业、管理、登录与 AI 页面

**Files:** 入库、出库、拣货、复核、盘点、调拨、预警、审批、导入、审计、登录和 AI 页面。

- [ ] 先写“创建入库、登录、AI 提问仅显示未接入提示”的失败测试。
- [ ] 实现真实业务表单和操作按钮，以及统一受限提示。
- [ ] 创建未来 FastAPI 的 TypeScript 请求契约，不发送网络请求。
- [ ] 运行完整测试和生产构建。

### Task 4: 本地运行巡检

- [ ] 启动 Vite 并访问看板、库存、入库、出库、盘点、审批和 AI 页面。
- [ ] 确认不存在虚构业务记录，且按钮不会伪造业务成功。
- [ ] 在 README 记录运行方式、原型边界和联调前提。
