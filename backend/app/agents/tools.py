"""助手可调用与禁止调用的工具名。禁止 SQL 和无人确认的入出库。"""

# 查询、制表、三种草稿、提交审批。没有「直接改库存」。
WHITELIST_TOOLS = {  # 图节点真正允许调用的工具名
    "query_inventory",  # 查库存余额
    "query_stock_ledger",  # 查库存流水
    "query_inbound_order",  # 查入库单
    "query_outbound_order",  # 查出库单
    "query_picking_efficiency",  # 查拣货效率
    "query_alerts",  # 查预警
    "query_approvals",  # 查审批
    "query_dashboard",  # 查看板
    "query_abc_report",  # ABC 报表
    "query_turnover_report",  # 周转报表
    "query_daily_report",  # 日报
    "query_weekly_report",  # 周报
    "format_table",  # 把结果格式化成 Markdown 表
    "create_inbound_draft",  # 生成入库草稿（不落库存）
    "create_outbound_draft",  # 生成出库草稿
    "create_counting_draft",  # 生成盘点草稿
    "submit_for_approval",  # 提交审批，仍需人确认
}  # 白名单结束

# 即使模型编出这些名字也必须拒绝。
FORBIDDEN_TOOLS = {  # 显式禁止：SQL 与无人确认改库存
    "execute_raw_sql",  # 禁止任意 SQL
    "execute_sql",  # 禁止另一别名
    "update_stock_balance",  # 禁止直接改余额
    "delete_stock_ledger",  # 禁止删流水
    "confirm_inbound_without_user",  # 禁止无人确认入库
    "complete_outbound_without_user",  # 禁止无人确认出库
}  # 禁止名单结束


def assert_whitelist(name: str) -> str:  # 校验工具名，通过则原样返回
    if name in FORBIDDEN_TOOLS or name not in WHITELIST_TOOLS:  # 在禁止名单或不在白名单
        raise ValueError(f"tool not allowed: {name}")  # 拒绝执行
    return name  # 合法工具名
