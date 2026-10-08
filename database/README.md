# Mega Star 数据导入说明

## 数据安全警告（2026 年 9 月 9 日）

当前 `erp_wms` 已经存在导入数据。**不要在这个库上再次执行 `schema.sql`**：该脚本包含 `DROP TABLE IF EXISTS`，会删除已有业务表和数据。也不要把历史 `inbound_record`、`outbound_record` 重放为当前库存。

后端新增账号、单据、审计和预留库存字段必须使用 `backend/alembic/versions/0001_add_backend_core.py` 的**增量迁移**。操作前先备份并执行只读检查：

```powershell
$py = "C:\Users\wang2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py -m backend.scripts.check_database --database-url "mysql+pymysql://erp_app:<password>@127.0.0.1:3306/erp_wms?charset=utf8mb4" --json
```

只有获得数据库管理员确认后，才可显式带 `--allow-erp-wms` 运行迁移；详见 [`docs/开发文档.md`](../docs/开发文档.md)。

## 文件说明

| 文件 | 作用 |
|---|---|
| `schema.sql` | **仅用于新建空库**的基础表初始化；已有库禁止执行 |
| `megastar_import.sql` | 向已初始化的空库导入清洗数据 |
| `import_report.json` | 本次清洗和导入统计 |
| `../tools/import_megastar_to_mysql.py` | 重新生成导入 SQL 的脚本 |

MySQL 8 可使用本机安装目录中的 `mysql.exe`，不依赖旧的 MySQL 5.5 路径。

## 字段映射和清洗规则

### 商品唯一键

原始数据里的 `Product` 不是全局唯一，同一商品编码可能对应多个品牌。因此系统使用：

```text
source_product_code + brand
```

作为唯一业务键，并生成新的 `sku_code`：

```text
MS-{source_product_code}-{brand}
```

### 数量字段

| 来源字段 | 目标字段 | 含义 |
|---|---|---|
| 商品主数据 `Quantity` | `product.pallet_capacity` | 托盘容量 |
| 仓库库存 `Quantity` | `stock_balance.quantity` | 当前库存数量 |
| 收货记录 `Quantity` | `inbound_record.quantity` | 收货数量 |
| 拣货记录 `Quantity` | `outbound_record.quantity` | 拣货数量 |

商品主数据里的 `Quantity` 不能当作库存、收货或拣货数量使用。

### 历史数据边界

`inbound_record` 和 `outbound_record` 只保存数据集历史记录，不写入 `stock_ledger`，也不修改 `stock_balance`。这样可以避免历史收发货与当前库存重复计算。

## 导入统计

| 表 | 行数 |
|---|---:|
| `warehouse` | 1 |
| `warehouse_location` | 65,856 |
| `product` | 3,128 |
| `staff` | 10 |
| `customer` | 100 |
| `stock_balance` | 57,623 |
| `inbound_record` | 56,211 |
| `outbound_record` | 45,082 |
| 合计 | 228,010 |
