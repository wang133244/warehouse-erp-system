# 智能 ERP 仓管系统后端

FastAPI + SQLAlchemy 2.x + Alembic 的仓储管理后端。最终开发说明与技术实现：

- [`docs/开发文档.md`](../docs/开发文档.md)（含运行日志第 12 节）
- [`docs/技术文档.md`](../docs/技术文档.md)（含运行日志 §4.3）

早期后端过程稿（已过期，仅作对照）：

- [`docs/后端开发文档.md`](../docs/后端开发文档.md)

## 快速启动

```powershell
$py = "C:\Users\wang2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$env:PYTHONPATH = (Get-Location).Path
& $py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

服务：`/health`；OpenAPI：`/docs`。

运行日志（不入库）：启动终端 + `backend/logs/app.log`。与接口 `X-Request-ID` / 错误 JSON 的 `request_id` 对应。复制 `backend/.env.example` 为 `.env` 后可调：

| 变量 | 默认 | 说明 |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG` 才会记下 `/health` |
| `LOG_DIR` | 空 → `backend/logs` | 日志目录 |
| `LOG_TO_FILE` | `true` | 测试与 Docker 用 `false` |

不要把密码、JWT、数据库口令打进日志。业务「谁改了库存」看系统管理里的操作审计。

本机管理员账号为 `admin`，初始密码存放在 `backend/.admin-password`。该文件只用于本地开发，不要提交或分发。

## 数据安全

绝不能对已经导入数据的 `erp_wms` 直接执行 `database/schema.sql`，它包含 `DROP TABLE`。先用 `backend.scripts.check_database` 做只读检查，确认备份和业务账号后才可用 `backend.scripts.run_migrations --allow-erp-wms` 执行**增量** Alembic 迁移。

```powershell
& $py -m pytest backend/tests -q
& $py -m compileall backend/app backend/scripts
```
