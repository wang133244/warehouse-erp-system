# 智能 ERP 仓管系统前端运行与联调文档

> 更新日期：2026-09-16  
> **最终开发说明**以 [`docs/开发文档.md`](../docs/开发文档.md) 为准。下文为前端启动摘要。  
> 原完整界面设计文档已归档至 `docs/前端设计文档.md`。

## 1. 技术栈

- Vue 3 + TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- Vitest + Vue Test Utils
- HTTP 层使用原生 `fetch`，未引入 Axios

## 2. 已接入能力

### 认证与路由

- `POST /api/v1/auth/login` 登录
- `GET /api/v1/auth/me` 恢复当前用户
- `POST /api/v1/auth/logout` 退出
- JWT 保存在浏览器 `localStorage`
- 未登录访问业务页自动跳转 `/login`
- 已登录访问 `/login` 自动跳转 `/dashboard`

### 查询页面

| 页面 | 接口 |
|---|---|
| 仓储运营看板 | `GET /api/v1/dashboard/summary`、`GET /api/v1/dashboard/charts` |
| 商品与 SKU | `GET /api/v1/products`、`POST /api/v1/products` |
| 仓库与库位 | `GET /api/v1/warehouses`、`GET /api/v1/locations` |
| 库存查询 | `GET /api/v1/inventory/balances` |
| 库存流水 | `GET /api/v1/inventory/ledgers` |
| 入库单 | `GET /api/v1/inbounds`、`GET /api/v1/inbounds/{id}` |
| 出库单 | `GET /api/v1/outbounds`、`GET /api/v1/outbounds/{id}` |
| 拣货任务 | `GET /api/v1/picking-tasks` |
| 预警中心 | `GET /api/v1/alerts` |
| 数据导入 | `GET /api/v1/imports` |
| 操作审计 | `GET /api/v1/audit-logs` |
| 盘点管理 | `GET /api/v1/stock-counts` |
| 调拨管理 | `GET /api/v1/transfers` |
| 审批中心 | `GET /api/v1/approvals` |
| 收货确认 | `GET /api/v1/receivings` |
| 出库复核 | `GET /api/v1/outbound-reviews` |
| 用户与权限 | `GET /api/v1/users` |
| AI 智能工作台 | `GET /api/v1/agents/sessions` |
| ABC 与周转 | `GET /api/v1/reports/abc`、`GET /api/v1/reports/turnover` |
| 日报 / 周报 / 拣货效率 | `GET /api/v1/reports/daily`、`/weekly`、`/picking-efficiency` |

商品、库位、仓库数据会在需要展示编码的页面做前端映射；前端不直接连接 MySQL。

### 最小写操作闭环

| 操作 | 接口 |
|---|---|
| 新建入库单 | `POST /api/v1/inbounds` |
| 入库单确认收货 | `POST /api/v1/inbounds/{id}/confirm` |
| 新建出库单 | `POST /api/v1/outbounds` |
| 出库单分配库存 | `POST /api/v1/outbounds/{id}/allocate` |
| 拣货任务确认 | `POST /api/v1/picking-tasks/{id}/confirm` |
| 出库单完成 | `POST /api/v1/outbounds/{id}/complete` |
| 新建/保存/提交盘点单 | `POST/PUT /api/v1/stock-counts`、`POST /api/v1/stock-counts/{id}/submit` |
| 新建/保存/提交/执行调拨 | `POST/PUT /api/v1/transfers`、`POST /api/v1/transfers/{id}/submit`、`POST /api/v1/transfers/{id}/execute` |
| 批准/驳回审批 | `POST /api/v1/approvals/{id}/approve`、`POST /api/v1/approvals/{id}/reject` |
| 收货确认 | `POST /api/v1/receivings/{id}/confirm` |
| 出库复核 | `POST /api/v1/outbounds/{id}/review` |
| 智能查询 | `POST /api/v1/agents/sessions/{id}/messages` |

所有写请求由 `frontend/src/models/client.ts` 自动生成并携带 `Idempotency-Key`。接口失败时 `ApiError` 带 `request_id`，可与后端运行日志、`X-Request-ID` 对齐。

## 3. 启动与联调

### 3.1 后端

在项目根目录运行：

```powershell
$py = "C:\Users\wang2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：<http://127.0.0.1:8000/health>  
OpenAPI：<http://127.0.0.1:8000/docs>  
运行日志：后端终端或 `backend/logs/app.log`（详见 [`docs/开发文档.md`](../docs/开发文档.md) 第 12 节）

### 3.2 前端

在 `frontend` 目录运行：

```powershell
npm install
npm run dev
```

访问：<http://127.0.0.1:5173>

默认 API 地址为 `http://127.0.0.1:8000`。生产同域部署时可将 `VITE_API_BASE_URL` 设为空字符串，前端会使用 `window.location.origin`，由 Nginx 把 `/api` 反代到 FastAPI。

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

登录账号为 `admin`。管理员密码保存在本机 `backend/.admin-password`，不要写入源码、文档或提交记录。

## 4. 测试与构建

```powershell
Set-Location .\frontend
npm test -- --run
npm run build
```

当前验证结果以仓库内 `npx vitest run` 为准（日志与 MVC 变更后请重新跑一遍）。

## 5. 安全边界

- 前端只访问 FastAPI，不直接访问 MySQL 或 Redis
- 数据库账号密码、管理员密码、JWT 不写入源码和文档
- 业务状态机、库存计算、并发控制、幂等、审计和运行日志全部由后端负责
- 前端错误信封中的 `request_id` 用于和后端日志对账，不在页面展示完整服务器日志
- 盘点、调拨、审批、收货确认、出库复核、用户管理和智能工作台已接入真实接口
- 智能助手通过 LangGraph 调用白名单工具查询或生成草稿，不允许直接修改库存
- 报表页只读取 `stock_ledger` / `stock_balance` 聚合结果

## 6. 目录结构

```text
frontend/src
  views/         # 页面（View）
  controllers/   # 页面逻辑
  models/        # API 与类型（含 fetch 客户端）
  api/           # 兼容再导出，勿再加逻辑
  components/    # 业务与通用组件
  config/        # 页面字段、导航与角色
  layouts/       # 应用外壳
  router/        # 路由与守卫
  stores/        # Pinia 状态
```

## 7. Docker Compose

在项目根目录：

```powershell
docker compose up --build
```

浏览器访问前端映射端口（默认 `http://127.0.0.1:8080`）。数据库密码、`SECRET_KEY` 通过环境变量传入，不要写入镜像或 compose 文件。Compose 不会执行 `database/schema.sql`。后端容器 `LOG_TO_FILE=false`，用 `docker compose logs backend` 看运行日志。
