# Mega Star 仓库管理系统开发文档

> 版本：1.0  
> 编写日期：2026-09-07  
> 适用项目：智能 ERP 仓管系统  
> 数据集：Mega Star Distribution Centre  
> 技术栈：FastAPI、MVC/分层架构、MySQL、Redis、LangGraph、Vue3

---

## 1. 文档目的

本文档用于指导智能 ERP 仓管系统第一阶段的仓储模块开发。系统以 Mega Star Distribution Centre 数据集作为仓储业务初始化和历史分析数据，围绕商品、仓库、库位、库存、收货和拣货建立可运行的 WMS 业务闭环。

本文档重点解决：数据集如何进入系统、字段如何映射、历史数据如何与实时业务隔离、入库/出库/盘点/调拨如何避免重复记账，以及 MySQL、Redis 和 LangGraph 的职责边界。

本文档以《智能ERP仓管系统需求分析文档.md》为需求依据，但会根据 Mega Star 数据集的实际能力收敛功能范围。数据集中不包含或无法确认的字段，不作为系统已经具备的能力，而通过扩展表和业务流程补足。

## 2. 项目定位与开发边界

### 2.1 项目定位

```text
商品建档 → 仓库与库位维护 → 初始库存导入 → 收货入库
    → 库存增加 → 出库拣货 → 库存扣减
    → 库存查询与流水追溯 → AI 查询、预警和分析
```

系统不是简单的数据集展示页面，也不是让 AI 直接操作数据库的聊天机器人。所有会改变库存或单据状态的动作，都必须经过 FastAPI 业务服务层。

### 2.2 第一阶段范围

| 优先级 | 功能 | 说明 |
|---|---|---|
| P0 | 用户、角色和数据权限 | 保证不同仓库和角色的数据隔离 |
| P0 | 商品/SKU 管理 | 以 Product List 初始化商品主数据 |
| P0 | 仓库、库区、库位管理 | 以 Warehouse Stocks 和位置信息初始化 |
| P0 | 库存查询 | 查询现存量、可用量、锁定量和库存位置 |
| P0 | 收货入库 | 将收货确认转换为正式入库业务 |
| P0 | 出库拣货 | 将出库需求转换为拣货任务并扣减库存 |
| P0 | 库存流水 | 记录每一次库存变更和来源单据 |
| P0 | 幂等、锁和审计 | 防止重复提交、并发超卖和越权操作 |
| P1 | 盘点、库内调拨 | 通过正式库存服务处理库存变化 |
| P1 | 库存预警 | 支持低库存、负库存和异常库存预警 |
| P1 | AI 智能工作台 | 支持自然语言查询、解释和分析 |
| P2 | 批次、有效期、序列号 | 数据集中未确认，作为可选扩展 |
| P2 | 采购、销售、财务和生产 | 不在第一阶段实现完整闭环 |

### 2.3 数据集无法直接提供的能力

以下内容不能从 Mega Star 数据集中直接推断，必须等待企业真实规则或由自定义测试数据补充：采购订单、供应商结算、销售订单、客户信用、批次和有效期、序列号、质量检验、完整财务成本、生产领料、企业审批制度。

## 3. Mega Star 数据集分析

### 3.1 数据分类

| 数据集分类 | 中文名称 | 系统定位 |
|---|---|---|
| Product List | 商品清单 | 商品主数据初始化来源 |
| Warehouse Stocks | 仓库库存 | 初始库存和库存位置初始化来源 |
| Receiving | 收货记录 | 历史收货记录和入库业务样本来源 |
| Picking | 拣货记录 | 历史拣货记录和出库业务样本来源 |

数据文件中可能还包含仓库、库位和操作人员信息。实际导入前必须以 CSV 的真实列名为准，不允许仅依据文件名硬编码字段。

### 3.2 数据集与系统功能映射

| Mega Star 数据 | 对应系统模块 | 导入后用途 | 是否直接修改实时库存 |
|---|---|---|---|
| Product List | 商品/SKU | 初始化商品档案 | 否 |
| Warehouse Stocks | 库存初始化 | 初始化 `stock_balance` | 仅初始化批次允许 |
| Receiving | 历史收货/入库 | 导入历史记录或生成待审核草稿 | 历史导入不重复增加 |
| Picking | 历史拣货/出库 | 导入历史记录或生成待审核草稿 | 历史导入不重复扣减 |
| 操作人员信息 | 用户/员工 | 建立操作人员映射 | 否 |
| 仓库、库位信息 | 仓库基础资料 | 初始化组织结构 | 否 |

### 3.3 时间边界

数据集中的库存、收货和拣货记录视为一个历史业务截面，而不是系统上线后的持续实时数据。导入批次必须记录数据集名称、版本、原始文件、原始行号、业务日期、导入批次号、导入时间和数据状态。无法确认业务日期的记录标记为 `date_unknown`，不得与实时流水自动按时间混合。

## 4. 解决功能重叠的设计原则

### 4.1 一个业务对象只有一个主责模块

| 业务对象 | 唯一主责模块 | 其他模块权限 |
|---|---|---|
| 商品资料 | 商品主数据模块 | 只能引用，不能复制维护 |
| 仓库和库位 | 仓库基础资料模块 | 只能引用，不能在单据中临时创建正式库位 |
| 当前库存 | 库存中心 | 其他模块只能调用库存服务 |
| 库存变化 | 库存流水服务 | 其他模块只能提交变更请求 |
| 收货过程 | 入库模块 | 库存中心只接收确认后的变更 |
| 拣货过程 | 出库模块 | 库存中心只接收确认后的变更 |
| 盘点差异 | 盘点模块 | 不允许直接编辑库存余额 |
| AI 建议 | AI 分析模块 | 只能生成建议、草稿和预警 |
| 审批审计 | 审批审计模块 | 统一记录，不由各模块伪造 |

### 4.2 历史数据与正式业务数据分开

```text
原始数据：保存原文件内容，不参与业务计算
历史业务数据：用于查询和分析，不重复产生库存变化
正式业务数据：经过系统业务流程确认，可以改变库存
```

使用 `record_origin` 区分来源：

```text
dataset_initialization  数据集初始化
dataset_history         数据集历史导入
system_operation        系统实时操作
system_adjustment       系统调整
```

### 4.3 所有库存变化只有一个入口

任何模块不得直接更新 `stock_balance`。统一调用：

```text
InventoryService.apply_transaction()
```

该服务在同一个 MySQL 事务中完成：校验单据状态和权限、校验幂等键、锁定库存行、检查可用库存、更新库存快照、写入库存流水、写入审计日志。事务提交后才删除或刷新 Redis 缓存。

### 4.4 AI 不拥有库存写权限

LangGraph 智能体可以调用只读工具查询库存、收货、拣货和流水，也可以生成补货建议、异常解释和单据草稿，但不得直接调用 ORM、SQL 写命令或库存变更服务。

```text
AI 生成建议 → 用户确认 → 创建业务单据 → 权限/审批校验 → 库存服务执行
```

## 5. 系统总体架构

```text
Vue3 管理端 / AI 工作台
             │ HTTPS
             ▼
FastAPI API 层
  ├── 认证与权限
  ├── 请求校验与幂等
  ├── Controller
  └── Tool Gateway
             │
             ▼
应用 Service 层
  ├── 商品服务       ├── 仓库库位服务
  ├── 入库服务       ├── 出库服务
  ├── 库存服务       ├── 盘点服务
  ├── 调拨服务       └── 审批审计服务
             │
             ├── MySQL：业务事实、库存快照、流水、单据、审计
             ├── Redis：缓存、分布式锁、幂等、任务状态、会话
             └── LangGraph：智能体编排、查询、分析和建议
```

## 6. 后端目录和模块设计

```text
backend/
├── app/
│   ├── main.py
│   ├── core/              # 配置、认证、MySQL、Redis
│   ├── common/            # 枚举、异常、分页、幂等
│   ├── modules/
│   │   ├── master_data/   # 商品、SKU
│   │   ├── warehouse/     # 仓库、库区、库位
│   │   ├── inventory/     # 库存快照、库存流水
│   │   ├── inbound/       # 入库、收货
│   │   ├── outbound/      # 出库、拣货
│   │   ├── counting/      # 盘点
│   │   ├── transfer/      # 调拨
│   │   └── approval/      # 审批、审计
│   ├── integrations/
│   │   └── megastar/      # 读取、映射、校验、导入
│   └── agents/            # LangGraph、工具和策略
└── tests/
```

调用规则固定为：

```text
Controller → Service → Repository/Model
Agent      → Tool Gateway → Service
```

Controller 不直接写数据库，Agent 不直接调用 Repository，业务模块不允许绕过 `InventoryService` 修改库存。

## 7. MySQL 数据库设计

### 7.1 数据分层

| 分层 | 表示例 | 作用 |
|---|---|---|
| 原始层 | `raw_megastar_product`、`raw_megastar_stock` | 保存原始文件，支持追溯和重导 |
| 映射层 | `data_import_batch`、`data_import_record`、`sku_source_mapping` | 保存批次、映射、校验结果 |
| 业务层 | `product`、`stock_balance`、`inbound_order` | 保存正式业务事实 |
| 分析层 | `inventory_snapshot_daily`、`warehouse_kpi_daily` | 保存统计结果，不作为库存事实 |

### 7.2 核心业务表

```text
product
├── id
├── sku_code                 系统唯一 SKU 编码
├── name / description
├── unit / status
└── created_at / updated_at

warehouse
├── id / code / name / status

warehouse_location
├── id / warehouse_id
├── zone_code / location_code
└── status

stock_balance
├── id
├── warehouse_id / location_id / product_id
├── on_hand_quantity         现存量
├── reserved_quantity        锁定量
├── frozen_quantity          冻结量
├── available_quantity       可用量
├── version                  乐观锁版本
└── updated_at

stock_ledger
├── id / ledger_no
├── product_id / warehouse_id / location_id
├── transaction_type         INIT/INBOUND/OUTBOUND/TRANSFER/COUNT/LOSS
├── quantity_delta
├── before_quantity / after_quantity
├── source_type / source_id
├── idempotency_key / operator_id
└── created_at
```

`stock_balance` 建立唯一约束：

```text
UNIQUE(warehouse_id, location_id, product_id)
```

后续启用批次时，再将 `batch_id` 加入唯一键；未启用批次前不伪造批次参与库存计算。

### 7.3 单据表

```text
inbound_order
├── id / order_no
├── source_type             DATASET / MANUAL / PURCHASE
├── status                  DRAFT / CONFIRMED / RECEIVED / CANCELLED
├── warehouse_id / business_date
└── idempotency_key

inbound_order_item
├── id / inbound_order_id / product_id / location_id
└── planned_quantity / received_quantity

outbound_order
├── id / order_no
├── source_type             DATASET / MANUAL / SALES
├── status                  DRAFT / ALLOCATED / PICKING / PICKED / COMPLETED
├── warehouse_id / idempotency_key

outbound_order_item
├── id / outbound_order_id / product_id / location_id
└── planned_quantity / picked_quantity

picking_task
├── id / task_no / outbound_order_id
├── product_id / location_id / assigned_user_id
├── planned_quantity / picked_quantity / status
```

### 7.4 导入和 AI 表

```text
data_import_batch
├── id / batch_no / dataset_name / dataset_version
├── status                  CREATED / VALIDATED / IMPORTED / ROLLED_BACK
├── total_rows / valid_rows / invalid_rows
└── created_at

data_import_record
├── id / batch_id / source_file / source_row_no
├── source_record_key / source_type / target_record_id
├── validation_status / error_message / raw_payload_json

sku_source_mapping
├── product_id / source_name / source_sku_code
├── mapping_status           PENDING / CONFIRMED / REJECTED
├── mapping_method / confidence / reviewed_by / reviewed_at

inventory_alert
├── alert_type / product_id / warehouse_id
├── current_quantity / threshold_quantity / status
└── generated_at

ai_query_record
├── user_id / question / tools_called_json
├── answer_summary / risk_level / created_at
```

AI 预测或补货建议必须使用独立的 `ai_forecast_result`、`ai_replenishment_suggestion` 表，并使用 `forecast_quantity`、`suggested_quantity` 字段，不能与 `available_quantity` 混用。

## 8. Mega Star 数据导入方案

### 8.1 导入流程

```text
上传原始文件 → 创建导入批次 → 保存原始行
    → 字段识别与类型转换 → 主数据匹配
    → 校验重复、空值、数量和日期 → 生成错误报告
    → 管理员确认 → 写入正式表或历史表 → 生成统计
```

导入操作必须支持预览和回滚。校验失败的行不能静默丢弃，必须进入 `data_import_record` 并显示错误原因。

### 8.2 四类文件导入规则

#### Product List 商品清单

- 先根据原始商品编码查找 `sku_source_mapping`；
- 已确认映射的记录更新对应商品资料；
- 未匹配记录创建待审核商品，不自动与同名商品合并；
- 重复导入不得生成重复 SKU；
- 商品资料导入不会写入 `stock_ledger`。

#### Warehouse Stocks 仓库库存

- 只允许作为“系统初始化库存”导入一次；
- 导入前必须指定初始化批次和库存基准日期；
- 相同仓库、库位、SKU 的多行先聚合，并记录聚合规则；
- 初始化成功后写入 `stock_balance` 和 `INIT` 类型库存流水；
- 相同批次再次提交必须幂等返回，不能再次增加库存；
- 已存在实时库存的环境不允许直接覆盖，必须走库存调整或盘点流程。

#### Receiving 收货记录

- 默认导入为历史收货记录；
- 历史记录可进入 `inbound_order`，状态为 `RECEIVED`，但不再次增加库存；
- 如需作为上线后的待处理业务，必须导入为 `DRAFT`，收货员确认后才产生库存流水；
- 每条记录保存原始来源和来源行号；
- 收货数量必须大于等于 0，异常数量进入错误报告。

#### Picking 拣货记录

- 默认导入为历史拣货记录；
- 历史记录用于查询、统计和 AI 分析，不再次扣减当前库存；
- 如需模拟实时出库，必须创建测试出库单并明确标记 `simulation=true`；
- 正式出库必须由出库单、拣货任务和复核确认完成；
- 拣货数量不能超过任务分配数量，也不能超过库存服务返回的可用量。

### 8.3 导入与实时业务的防串规则

```text
来源批次不同，不代表可以重复记账
历史记录导入，不代表重新发生库存变化
相同业务来源只能产生一次库存流水
所有库存流水必须有唯一幂等键
```

建议幂等键格式：

```text
MEGASTAR:{dataset_version}:{source_file}:{source_row_no}:{business_type}
```

正式业务操作使用客户端生成的 `Idempotency-Key`。服务端在 Redis 中短期拦截，并在 MySQL 中使用唯一索引做最终防线。

## 9. 核心业务流程

### 9.1 库存初始化

```text
管理员创建初始化批次
    → 导入 Warehouse Stocks
    → 校验 SKU、仓库、库位
    → 预览差异
    → 确认初始化
    → 写入 stock_balance
    → 写入 INIT 库存流水
    → 刷新库存缓存
```

初始化完成后，系统以 `stock_balance` 为当前库存唯一来源，后续查询不能再次读取原始 CSV 计算库存。

### 9.2 收货入库

```text
创建入库单 → 填写或导入收货明细 → 分配仓库和库位
    → 收货员确认数量 → 校验状态和权限
    → InventoryService 增加库存 → 写入 INBOUND 流水
    → 入库单变为 RECEIVED
```

同一个入库单重复确认时，系统返回原处理结果，不再次增加库存。

### 9.3 出库拣货

```text
创建出库单 → 库存分配 → 锁定可用库存 → 生成拣货任务
    → 拣货员按库位拣货 → 复核确认
    → InventoryService 扣减库存 → 释放锁定量
    → 写入 OUTBOUND 流水 → 出库单变为 COMPLETED
```

锁定库存和实际扣减必须区分：

```text
可用量 = 现存量 - 锁定量 - 冻结量
```

拣货任务创建时增加 `reserved_quantity`，正式出库确认时同时减少 `on_hand_quantity` 和 `reserved_quantity`。

### 9.4 盘点

```text
创建盘点单 → 冻结指定库位或 SKU → 录入实盘数量
    → 系统计算差异 → 主管审核
    → InventoryService 生成 COUNT_ADJUSTMENT 流水
    → 更新库存快照 → 解除冻结
```

盘点员不能直接修改 `stock_balance`。盘点数量只是实盘结果，只有审核通过后才能形成库存调整。

### 9.5 调拨

```text
创建调拨单 → 校验调出库存 → 锁定调出库存 → 调出确认
    → 写 TRANSFER_OUT 流水 → 目标库位收货
    → 写 TRANSFER_IN 流水 → 调拨完成
```

仓库内库位调拨可以在一个事务内完成；跨仓调拨需要支持在途状态，目标仓库尚未收货时不能提前增加可用库存。

## 10. MySQL 与 Redis 联动设计

### 10.1 MySQL 职责

MySQL 保存不可替代的业务事实：用户、角色、权限、商品、仓库、库位、入库单、出库单、拣货任务、`stock_balance`、`stock_ledger`、盘点、调拨、审批、审计和导入批次。

### 10.2 Redis 职责

Redis 只承担高并发和临时状态能力：

```text
erp:stock:balance:{warehouse_id}:{location_id}:{product_id}
erp:stock:lock:{warehouse_id}:{location_id}:{product_id}
erp:idempotency:{user_id}:{idempotency_key}
erp:task:import:{batch_id}
erp:task:agent:{conversation_id}
erp:session:{user_id}
```

Redis 丢失后可以从 MySQL 重建，不得把 Redis 作为库存唯一来源。AI 临时数据使用 `ai:` 前缀，不能覆盖 `erp:stock:` 缓存。

### 10.3 库存写入策略

```text
获取 Redis 分布式锁
    → 开启 MySQL 事务
    → SELECT ... FOR UPDATE 锁库存行
    → 校验可用量和状态
    → 更新 stock_balance
    → 插入 stock_ledger
    → 提交 MySQL 事务
    → 删除或刷新 Redis 缓存
    → 释放 Redis 锁
```

如果 MySQL 事务失败，Redis 不能更新；如果缓存刷新失败，后台任务重建缓存，但不能回滚已经提交的业务流水。

## 11. FastAPI 接口设计

### 11.1 商品、仓库和库存

```text
GET    /api/v1/products
POST   /api/v1/products
GET    /api/v1/warehouses
GET    /api/v1/locations
GET    /api/v1/inventory/balances
GET    /api/v1/inventory/ledgers
GET    /api/v1/inventory/{product_id}/availability
```

### 11.2 入库和出库

```text
POST   /api/v1/inbounds
POST   /api/v1/inbounds/{order_id}/confirm
GET    /api/v1/inbounds/{order_id}
POST   /api/v1/outbounds
POST   /api/v1/outbounds/{order_id}/allocate
POST   /api/v1/picking-tasks/{task_id}/confirm
POST   /api/v1/outbounds/{order_id}/complete
GET    /api/v1/outbounds/{order_id}
```

所有会改变状态或库存的接口必须要求：

```http
Authorization: Bearer <token>
Idempotency-Key: <unique-request-key>
```

### 11.3 数据导入

```text
POST   /api/v1/imports/megastar/preview
POST   /api/v1/imports/megastar/validate
POST   /api/v1/imports/megastar/confirm
GET    /api/v1/imports/{batch_id}
GET    /api/v1/imports/{batch_id}/errors
POST   /api/v1/imports/{batch_id}/rollback
```

导入接口不能接受“覆盖库存”参数。库存初始化和库存调整必须使用明确的业务类型，并保留操作者、审批人和来源批次。

## 12. LangGraph 多智能体设计

### 12.1 智能体职责

第一阶段建议使用以下智能体：

| 智能体 | 责任 | 权限 |
|---|---|---|
| 意图识别智能体 | 判断用户是查库存、查单据还是分析异常 | 只读 |
| 库存查询智能体 | 查询 SKU、仓库、库位和库存流水 | 只读 |
| 入出库分析智能体 | 分析收货、拣货和履约情况 | 只读 |
| 异常分析智能体 | 解释低库存、库存差异、重复记录等 | 只读 |
| 单据草稿智能体 | 生成入库、出库或盘点草稿 | 只能生成草稿 |
| 审核编排智能体 | 判断是否需要人工确认或审批 | 不能代替审批人 |

### 12.2 工具网关

智能体只能调用白名单工具：

```text
query_inventory()
query_stock_ledger()
query_inbound_order()
query_outbound_order()
query_picking_efficiency()
create_inbound_draft()
create_outbound_draft()
create_counting_draft()
submit_for_approval()
```

以下能力禁止提供给 AI：

```text
execute_raw_sql()
update_stock_balance()
delete_stock_ledger()
confirm_inbound_without_user()
complete_outbound_without_user()
```

### 12.3 AI 响应约束

AI 回复库存数据时必须展示查询时间、仓库和库位范围、SKU 编码、数据来源、现存量、锁定量、冻结量和可用量，并明确数据是实时业务数据还是历史数据。

示例：

```text
查询范围：A仓库 / 2026-09-07 14:30
数据来源：MySQL stock_balance
SKU：MS-1001
现存量：100
锁定量：20
冻结量：0
可用量：80
```

## 13. Vue3 前端页面设计

### 13.1 菜单结构

```text
首页看板
├── 商品与 SKU
├── 仓库与库位
├── 库存查询
├── 入库管理
│   ├── 入库单
│   └── 收货确认
├── 出库管理
│   ├── 出库单
│   ├── 拣货任务
│   └── 出库复核
├── 盘点管理
├── 调拨管理
├── 预警中心
├── 审批中心
├── 数据导入
├── 操作审计
└── AI 智能工作台
```

### 13.2 页面边界

- 页面负责展示、输入、表单校验和操作确认；
- 后端负责库存校验、权限、状态机和事务；
- AI 页面只显示查询结果、建议和待确认草稿；
- 导入页面必须明确显示“历史导入”“初始化库存”和“正式业务”三种模式。

## 14. 状态机设计

### 14.1 入库单

```text
DRAFT → CONFIRMED → RECEIVED
  └──────────────→ CANCELLED
```

只有 `RECEIVED` 状态允许产生正式入库流水；`RECEIVED` 不允许再次确认。

### 14.2 出库单

```text
DRAFT → ALLOCATED → PICKING → PICKED → COMPLETED
  └──────────────────────────────────→ CANCELLED
```

只有 `COMPLETED` 状态产生正式出库扣减；取消时必须释放已锁定库存。

### 14.3 导入批次

```text
CREATED → VALIDATED → IMPORTED
             └──────→ FAILED
IMPORTED → ROLLED_BACK
```

已经产生正式业务流水的导入批次不能物理删除，只能通过反向调整或受控回滚流程处理。

## 15. 权限、审批和审计

### 15.1 角色权限

| 角色 | 主要权限 |
|---|---|
| 系统管理员 | 用户、角色、字典、系统参数和数据导入配置 |
| 仓库主管 | 库存查看、入出库审核、盘点审批、调拨审批和异常处理 |
| 仓管员 | 收货、拣货、盘点录入和库存查询 |
| 数据管理员 | 数据集导入、校验、映射和导入回滚申请 |
| AI 使用者 | 查询、分析和生成业务草稿 |
| 审计员 | 查看库存流水、操作日志、审批日志和智能体调用记录 |

### 15.2 必须审批的操作

- 盘盈盘亏；
- 报损和库存减少调整；
- 跨仓调拨；
- 批量导入正式业务；
- AI 生成的批量出库或库存调整草稿；
- 修改已经确认的入库或出库数据。

### 15.3 审计要求

每次关键操作至少记录：

```text
操作者、角色、请求编号、业务单号
操作前状态、操作后状态
操作前数量、操作后数量
数据来源、客户端 IP、操作时间
```

## 16. 开发顺序

### 阶段一：基础设施

1. 创建 FastAPI 项目和配置管理；
2. 接入 MySQL、Redis 和数据库迁移；
3. 实现用户、角色和权限；
4. 建立统一异常、分页、日志和幂等组件。

### 阶段二：Mega Star 数据导入

1. 实现原始文件读取；
2. 建立导入批次和错误记录；
3. 导入商品、仓库和库位；
4. 导入库存初始化；
5. 导入历史 Receiving 和 Picking；
6. 生成导入审核报告。

### 阶段三：库存和收发货闭环

1. 实现库存查询；
2. 实现 `InventoryService`；
3. 实现入库单和收货确认；
4. 实现出库单、库存分配和拣货任务；
5. 实现库存流水和缓存联动；
6. 完成并发、幂等和异常测试。

### 阶段四：仓储扩展

1. 实现盘点；
2. 实现库内调拨；
3. 实现低库存和库存差异预警；
4. 实现仓库 KPI 和拣货效率报表；
5. 接入审批和审计中心。

### 阶段五：智能能力

1. 实现只读库存查询工具；
2. 实现收货、拣货和库存异常分析；
3. 实现 LangGraph 意图识别和工具编排；
4. 实现入库、出库和盘点草稿；
5. 加入人工确认和高风险审批拦截；
6. 记录 AI 工具调用和回答依据。

## 17. 测试要求

### 17.1 数据导入测试

- 相同导入批次重复提交，不得重复创建商品或库存；
- 相同商品名称但编码不同，不得自动合并；
- 缺少 SKU、仓库或库位的库存行必须进入错误报告；
- Receiving 历史导入不得重复增加库存；
- Picking 历史导入不得重复扣减库存；
- 导入批次回滚后，必须能查询回滚原因和操作人。

### 17.2 库存一致性测试

```text
期末库存 = 期初库存 + 入库流水总量 - 出库流水总量
           + 盘盈盘亏流水 + 调拨净变化 - 报损数量
```

必须验证：

- 任何正式库存变更都有对应流水；
- 任何库存流水都有来源单据；
- 不能出现没有流水的库存变化；
- 正常业务不能使可用库存小于 0；
- 并发出库不会超卖；
- Redis 缓存重建后与 MySQL 一致。

### 17.3 AI 权限测试

- AI 只能查询授权仓库的数据；
- AI 不能执行原始 SQL；
- AI 生成出库草稿后不能自动完成出库；
- 高风险库存调整必须进入审批；
- AI 回答必须能追溯到调用的工具和数据范围。

## 18. 验收标准

### 18.1 功能验收

- [ ] Mega Star 四类数据可以完成预览、校验和导入；
- [ ] 商品、仓库、库位和库存可以正常查询；
- [ ] Warehouse Stocks 只允许按初始化批次计入一次库存；
- [ ] 历史 Receiving 和 Picking 不会重复影响实时库存；
- [ ] 收货确认后可以增加库存并生成入库流水；
- [ ] 出库完成后可以扣减库存并生成出库流水；
- [ ] 盘点和调拨通过正式库存服务改变库存；
- [ ] 重复请求不能重复改变库存；
- [ ] Redis 缓存与 MySQL 库存可以自动重建；
- [ ] AI 只能通过工具网关访问业务能力；
- [ ] 高风险动作必须人工确认或审批；
- [ ] 所有库存变化可以通过单据号和流水号追溯。

### 18.2 质量验收

- [ ] 核心库存服务单元测试全部通过；
- [ ] 导入、入库、出库、盘点和调拨具备集成测试；
- [ ] 并发出库测试不出现负库存或重复扣减；
- [ ] 普通查询接口在常规数据量下 1 秒内返回；
- [ ] Redis 命中时库存查询目标响应时间不超过 300ms；
- [ ] 关键写操作具备审计记录和错误日志。

## 19. 结论

Mega Star Distribution Centre 适合作为本系统第一阶段的仓储业务基础数据源，重点覆盖商品、仓库、库位、库存、收货和拣货。它不能直接替代完整企业 ERP，也不能直接提供盘点、调拨、批次、审批和审计等全部企业功能。

本方案通过以下方式解决实现功能重叠：

```text
Product List       → 只负责商品主数据初始化
Warehouse Stocks   → 只负责系统上线时的库存初始化
Receiving          → 历史记录归档或转为待审核入库草稿
Picking            → 历史记录归档或转为待审核拣货草稿
入库、出库、盘点、调拨 → 统一通过 InventoryService 产生库存变化
MySQL              → 保存正式业务事实
Redis              → 提供缓存、锁、幂等和任务状态
LangGraph          → 负责查询、分析、预警和草稿生成
```

最终必须坚持一条底线：

> **数据集可以帮助系统初始化和分析，但只有经过正式业务流程确认的库存流水，才能改变 MySQL 中的实际库存。**
