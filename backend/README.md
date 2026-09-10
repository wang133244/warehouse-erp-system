# 智能 ERP 仓管系统后端

FastAPI + SQLAlchemy 2.x + Alembic 的仓储管理后端。完整的配置、迁移、接口、库存事务和前端联调说明在：

- `C:\Users\wang2\Desktop\智能erp仓管系统\docs\后端开发文档.md`

## 快速启动

```powershell
$py = "C:\Users\wang2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

服务：`/health`；OpenAPI：`/docs`。

本机管理员账号为 `admin`，初始密码存放在 `backend/.admin-password`。该文件只用于本地开发，不要提交或分发。

## 数据安全

绝不能对已经导入数据的 `erp_wms` 直接执行 `database/schema.sql`，它包含 `DROP TABLE`。先用 `backend.scripts.check_database` 做只读检查，确认备份和业务账号后才可用 `backend.scripts.run_migrations --allow-erp-wms` 执行**增量** Alembic 迁移。

```powershell
& $py -m pytest backend/tests -q
& $py -m compileall backend/app backend/scripts
```
