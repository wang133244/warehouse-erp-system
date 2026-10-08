"""汇总导出全部 ORM 表，避免业务层关心文件拆分。"""

from backend.app.db.models.audit import AuditLog, IdempotencyRecord  # 审计与幂等
from backend.app.db.models.catalog import (  # 主数据
    Customer,  # 客户
    DataImportBatch,  # 导入批次
    Product,  # 商品
    Staff,  # 员工
    Warehouse,  # 仓库
    WarehouseLocation,  # 库位
)  # catalog 导入结束
from backend.app.db.models.followup import AgentMessage, AgentSession, AlertAck  # 助手消息与预警确认
from backend.app.db.models.inventory import (  # 库存事实与历史收发货
    InboundRecord,  # 历史入库记录
    OutboundRecord,  # 历史出库记录
    StockBalance,  # 库存余额
    StockLedger,  # 库存流水
)  # inventory 导入结束
from backend.app.db.models.operations import (  # 作业单据与账号角色
    ApprovalTask,  # 审批任务
    InboundItem,  # 入库明细
    InboundOrder,  # 入库单
    OutboundItem,  # 出库明细
    OutboundOrder,  # 出库单
    PickingTask,  # 拣货任务
    StockCountItem,  # 盘点明细
    StockCountOrder,  # 盘点单
    TransferItem,  # 调拨明细
    TransferOrder,  # 调拨单
)  # operations 单据导入结束
from backend.app.db.models.security import (  # 兼容入口，真实定义在 operations
    Role,  # 角色
    UserAccount,  # 账号
    UserRole,  # 用户角色关联
    UserWarehouseScope,  # 用户仓库范围
)  # security 导入结束

__all__ = [  # 显式公开符号，配合 models 包再导出
    "AgentMessage",  # 助手消息
    "AgentSession",  # 助手会话
    "AlertAck",  # 预警确认
    "ApprovalTask",  # 审批
    "AuditLog",  # 审计日志
    "Customer",  # 客户
    "DataImportBatch",  # 导入批次
    "IdempotencyRecord",  # 幂等
    "InboundItem",  # 入库明细
    "InboundOrder",  # 入库单
    "InboundRecord",  # 历史入库
    "OutboundItem",  # 出库明细
    "OutboundOrder",  # 出库单
    "OutboundRecord",  # 历史出库
    "PickingTask",  # 拣货
    "Product",  # 商品
    "Role",  # 角色
    "Staff",  # 员工
    "StockBalance",  # 余额
    "StockCountItem",  # 盘点明细
    "StockCountOrder",  # 盘点单
    "StockLedger",  # 流水
    "TransferItem",  # 调拨明细
    "TransferOrder",  # 调拨单
    "UserAccount",  # 账号
    "UserRole",  # 用户角色
    "UserWarehouseScope",  # 仓库范围
    "Warehouse",  # 仓库
    "WarehouseLocation",  # 库位
]  # __all__ 结束
