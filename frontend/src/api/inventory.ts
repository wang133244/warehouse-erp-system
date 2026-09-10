import { request, type QueryParams } from './client'
import type { PagedResult } from './catalog'

export interface DashboardSummary {
  stock_quantity: number
  reserved_quantity: number
  available_quantity: number
  inbound_draft: number
  outbound_pending: number
}

export interface InventoryBalance {
  balance_id: number
  product_id: number
  location_id: number
  quantity: number
  reserved_quantity: number
  available_quantity: number
}

export interface StockLedger {
  ledger_id: number
  product_id: number
  location_id: number
  transaction_type: string
  quantity_delta: number
  before_quantity: number
  after_quantity: number
  source_type: string | null
  source_id: number | null
  created_at: string
}

export interface AuditLog {
  audit_log_id: number
  action: string
  entity_type: string
  entity_id: number
  user_id: number
  created_at: string
}

export function getDashboardSummary() {
  return request<DashboardSummary>('/api/v1/dashboard/summary')
}

export function listBalances(params: { productId?: number; offset?: number; limit?: number } = {}) {
  return request<PagedResult<InventoryBalance>>('/api/v1/inventory/balances', {
    params: {
      product_id: params.productId,
      offset: params.offset,
      limit: params.limit
    }
  })
}

export function getProductAvailability(productId: number) {
  return request<InventoryBalance>(`/api/v1/inventory/${productId}/availability`)
}

export function listLedgers(params: { limit?: number } = {}) {
  return request<{ items: StockLedger[] }>('/api/v1/inventory/ledgers', {
    params: params as QueryParams
  })
}

export function listAlerts(params: { threshold?: number } = {}) {
  return request<{ threshold: number; items: InventoryBalance[] }>('/api/v1/alerts', {
    params: params as QueryParams
  })
}

export function listAuditLogs(params: { limit?: number } = {}) {
  return request<{ items: AuditLog[] }>('/api/v1/audit-logs', {
    params: params as QueryParams
  })
}
