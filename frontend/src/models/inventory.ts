/** 库存、流水、看板、预警、审计 API。 */
import { createIdempotencyKey, downloadCsv, request, type QueryParams } from './client' // 引入请求、CSV 下载与查询类型
import type { PagedResult } from './catalog' // 分页结果类型

export interface DashboardSummary { // 看板汇总数字
  stock_quantity: number // 库存总量
  reserved_quantity: number // 锁定量
  available_quantity: number // 可用量
  inbound_draft: number // 待入库草稿数
  outbound_pending: number // 待出库数
  pending_receiving?: number // 待收货
  pending_review?: number // 待复核
  pending_approvals?: number // 待审批
  low_stock_alerts?: number // 低库存预警数
} // 结束 DashboardSummary

export interface DashboardCharts { // 看板图表数据
  inbound_by_day: { date: string; count: number; quantity: number }[] // 按日入库
  outbound_by_day: { date: string; count: number; quantity: number }[] // 按日出库
  stock_by_warehouse: { warehouse_id: number; warehouse_code: string; warehouse_name: string; quantity: number }[] // 按仓库库存
  low_stock: { balance_id: number; product_id: number; location_id: number; available_quantity: number }[] // 低库存点
} // 结束 DashboardCharts

export interface InventoryBalance { // 库存余额行
  balance_id: number // 余额主键
  product_id: number // 商品 ID
  location_id: number // 库位 ID
  quantity: number // 实际库存
  reserved_quantity: number // 锁定量
  frozen_quantity?: number // 冻结量
  available_quantity: number // 可用量
  sku_code?: string // SKU
  source_product_code?: string // 来源商品编码
  location_code?: string // 库位编码
  updated_at?: string // 最后更新时间
} // 结束 InventoryBalance

export interface StockLedger { // 库存流水
  ledger_id: number // 流水主键
  product_id: number // 商品 ID
  location_id: number // 库位 ID
  transaction_type: string // 业务类型
  quantity_delta: number // 变动数量
  before_quantity: number // 变动前
  after_quantity: number // 变动后
  source_type: string | null // 来源类型
  source_id: number | null // 来源单据 ID
  created_at: string // 发生时间
} // 结束 StockLedger

export interface AuditLog { // 操作审计
  audit_log_id: number // 审计主键
  action: string // 操作类型
  entity_type: string // 业务对象
  entity_id: number // 业务 ID
  user_id: number // 用户 ID
  username?: string | null // 账户名
  created_at: string // 操作时间
} // 结束 AuditLog

export function getDashboardSummary() { // 看板汇总
  return request<DashboardSummary>('/api/v1/dashboard/summary') // GET 汇总
} // 结束 getDashboardSummary

export function getDashboardCharts() { // 看板图表
  return request<DashboardCharts>('/api/v1/dashboard/charts') // GET 图表
} // 结束 getDashboardCharts

export function listBalances(params: { productId?: number; keyword?: string; availableOnly?: boolean; offset?: number; limit?: number } = {}) { // 库存余额列表
  return request<PagedResult<InventoryBalance>>('/api/v1/inventory/balances', { // GET 余额
    params: { // 查询参数映射
      product_id: params.productId, // 商品过滤
      keyword: params.keyword, // 关键字
      available_only: params.availableOnly, // 仅可用
      offset: params.offset, // 偏移
      limit: params.limit // 条数
    } // 结束 params
  }) // 结束 request
} // 结束 listBalances

export function getProductAvailability(productId: number) { // 某商品可用库存
  return request<InventoryBalance>(`/api/v1/inventory/${productId}/availability`) // GET 可用量
} // 结束 getProductAvailability

export function listLedgers(params: { keyword?: string; limit?: number } = {}) { // 库存流水
  return request<{ items: StockLedger[] }>('/api/v1/inventory/ledgers', { // GET 流水
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listLedgers

export function listAlerts(params: { threshold?: number; keyword?: string; offset?: number; limit?: number } = {}) { // 预警列表
  return request<{ // 预警响应结构
    threshold: number // 当前阈值
    total?: number // 总条数
    offset?: number // 偏移
    limit?: number // 条数
    items: Array<InventoryBalance & { status?: string; alert_type?: string; sku_code?: string; location_code?: string }> // 预警行
  }>('/api/v1/alerts', { // GET 预警
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listAlerts

export function ackAlert(balanceId: number, note?: string) { // 确认处理预警
  return request<{ balance_id: number; status: string }>(`/api/v1/alerts/${balanceId}/ack`, { // POST 确认
    method: 'POST', // POST
    body: { note: note ?? null }, // 处理说明
    idempotencyKey: createIdempotencyKey('alert-ack') // 幂等键
  }) // 结束 request
} // 结束 ackAlert

export function exportInventoryCsv() { // 导出库存 CSV
  return downloadCsv('/api/v1/exports/inventory', 'inventory.csv') // 下载库存文件
} // 结束 exportInventoryCsv

export function exportLedgerCsv() { // 导出流水 CSV
  return downloadCsv('/api/v1/exports/ledgers', 'ledgers.csv') // 下载流水文件
} // 结束 exportLedgerCsv

export function exportAuditCsv() { // 导出审计 CSV
  return downloadCsv('/api/v1/exports/audit', 'audit.csv') // 下载审计文件
} // 结束 exportAuditCsv

export function listAuditLogs(params: { keyword?: string; limit?: number } = {}) { // 审计列表
  return request<{ items: AuditLog[] }>('/api/v1/audit-logs', { // GET 审计
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listAuditLogs
