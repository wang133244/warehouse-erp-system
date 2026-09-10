# 智能 ERP 仓管系统前端运行与联调文档

> 更新日期：2026-09-09  
> 当前状态：前端已正式接入 FastAPI 后端，支持真实登录、核心查询和最小业务写操作闭环。  
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
| 仓储运营看板 | `GET /api/v1/dashboard/summary` |
| 商品与 SKU | `GET /api/v1/products` |
| 仓库与库位 | `GET /api/v1/warehouses`、`GET /api/v1/locations` |
| 库存查询 | `GET /api/v1/inventory/balances` |
| 库存流水 | `GET /api/v1/inventory/ledgers` |
| 入库单 | `GET /api/v1/inbounds`、`GET /api/v1/inbounds/{id}` |
| 出库单 | `GET /api/v1/outbounds`、`GET /api/v1/outbounds/{id}` |
| 拣货任务 | `GET /api/v1/picking-tasks` |
| 预警中心 | `GET /api/v1/alerts` |
| 数据导入 | `GET /api/v1/imports` |
| 操作审计 | `GET /api/v1/audit-logs` |

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

所有写请求由 `frontend/src/api/client.ts` 自动生成并携带 `Idempotency-Key`。

## 3. 启动与联调

### 3.1 后端

在项目根目录运行：

```powershell
$py = "C:\Users\wang2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：<http://127.0.0.1:8000/health>  
OpenAPI：<http://127.0.0.1:8000/docs>

### 3.2 前端

在 `frontend` 目录运行：

```powershell
npm install
npm run dev
```

访问：<http://127.0.0.1:5173>

默认 API 地址为 `http://127.0.0.1:8000`。如需覆盖，可复制 `frontend/.env.example` 为 `frontend/.env` 并修改：

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

当前验证结果：

- Vitest：`8` 个测试文件，`22` 个用例全部通过
- 构建：`vue-tsc -b && vite build` 通过
- 构建提示主包超过 500 kB，后续可通过路由级分包优化

## 5. 安全边界

- 前端只访问 FastAPI，不直接访问 MySQL 或 Redis
- 数据库账号密码、管理员密码、JWT 不写入源码和文档
- 业务状态机、库存计算、并发控制、幂等和审计全部由后端负责
- AI 工作台当前仍为待接入状态，不允许 AI 直接修改库存

## 6. 目录结构

```text
frontend/src
  api/         # fetch 客户端与后端 API 模块
  components/  # 业务与通用组件
  composables/ # 组合式工具
  config/      # 页面字段与导航配置
  layouts/     # 应用外壳
  router/      # 路由与守卫
  stores/      # Pinia 状态
  views/       # 登录与工作台页面
```
