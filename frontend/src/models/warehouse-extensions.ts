/** 盘点、调拨、审批 API。 */
import { createIdempotencyKey, request, type QueryParams } from './client' // 引入请求封装与查询类型

export interface PageQuery { // 分页查询参数
  page?: number // 页码
  pageSize?: number // 每页条数
  status?: string // 状态过滤
  orderNo?: string // 单号
  businessType?: string // 业务类型
} // 结束 PageQuery

export interface PageResult<T> { // 分页结果
  items: T[] // 当前页
  total: number // 总条数
  page: number // 当前页码
  page_size: number // 每页大小
} // 结束 PageResult

export interface StockCountItem { // 盘点明细
  stock_count_item_id?: number // 明细主键
  product_id: number // 商品 ID
  location_id: number // 库位 ID
  book_quantity?: number | null // 账面数量
  counted_quantity: number // 实盘数量
  variance_quantity?: number | null // 差异数量
} // 结束 StockCountItem

export interface StockCountUpsert { // 盘点保存载荷
  note?: string | null // 备注
  items: Array<{ product_id: number; location_id: number; counted_quantity: number }> // 实盘明细
} // 结束 StockCountUpsert

export interface StockCountOrder { // 盘点单
  stock_count_order_id: number // 盘点单主键
  order_no: string // 单号
  status: string // 状态
  note?: string | null // 备注
  items?: StockCountItem[] // 明细
  approval_summary?: { approval_task_id: number; status: string } | null // 关联审批
} // 结束 StockCountOrder

export interface TransferItem { // 调拨明细
  transfer_item_id?: number // 明细主键
  product_id: number // 商品 ID
  source_location_id: number // 来源库位
  target_location_id: number // 目标库位
  quantity: number // 调拨数量
} // 结束 TransferItem

export interface TransferUpsert { // 调拨保存载荷
  note?: string | null // 备注
  items: TransferItem[] // 明细
} // 结束 TransferUpsert

export interface TransferOrder { // 调拨单
  transfer_order_id: number // 调拨单主键
  order_no: string // 单号
  status: string // 状态
  transfer_scope?: string | null // 调拨范围
  note?: string | null // 备注
  username?: string | null // 创建人
  items?: TransferItem[] // 明细
  approval_summary?: { approval_task_id: number; status: string } | null // 关联审批
} // 结束 TransferOrder

export interface ApprovalTask { // 审批任务
  approval_task_id: number // 任务主键
  business_type: string // 业务类型
  business_id: number // 业务单 ID
  status: string // 审批状态
  requested_by: number // 申请人 ID
  requested_at?: string | null // 申请时间
  comment?: string | null // 审批意见
  business_status?: string | null // 业务单状态
  business_summary?: { // 业务摘要
    order_no?: string // 单号
    status?: string // 状态
    item_count?: number // 明细条数
  } | null // 摘要可空
} // 结束 ApprovalTask

function pageParams(params: PageQuery = {}): QueryParams { // 前端分页参数转后端 query
  return { // 蛇形字段
    page: params.page, // 页码
    page_size: params.pageSize, // 每页条数
    status: params.status, // 状态
    order_no: params.orderNo, // 单号
    business_type: params.businessType // 业务类型
  } // 结束 return
} // 结束 pageParams

export function listStockCounts(params: PageQuery = {}) { // 盘点单列表
  return request<PageResult<StockCountOrder>>('/api/v1/stock-counts', { params: pageParams(params) }) // GET 盘点
} // 结束 listStockCounts

export function createStockCount(payload: StockCountUpsert, idempotencyKey?: string) { // 新建盘点单
  return request<StockCountOrder>('/api/v1/stock-counts', { // POST 盘点
    method: 'POST', // POST
    body: payload, // 实盘数据
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('stock-count') // 外部或自动幂等键
  }) // 结束 request
} // 结束 createStockCount

export function saveStockCount(id: number, payload: StockCountUpsert, idempotencyKey?: string) { // 保存盘点单
  return request<StockCountOrder>(`/api/v1/stock-counts/${id}`, { // PUT 盘点
    method: 'PUT', // PUT
    body: payload, // 实盘数据
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('stock-count-save') // 幂等键
  }) // 结束 request
} // 结束 saveStockCount

export function submitStockCount(id: number, idempotencyKey?: string) { // 提交盘点审批
  return request<StockCountOrder>(`/api/v1/stock-counts/${id}/submit`, { // POST 提交
    method: 'POST', // POST
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('stock-count-submit') // 幂等键
  }) // 结束 request
} // 结束 submitStockCount

export function listTransfers(params: PageQuery = {}) { // 调拨单列表
  return request<PageResult<TransferOrder>>('/api/v1/transfers', { params: pageParams(params) }) // GET 调拨
} // 结束 listTransfers

export function createTransfer(payload: TransferUpsert, idempotencyKey?: string) { // 新建调拨单
  return request<TransferOrder>('/api/v1/transfers', { // POST 调拨
    method: 'POST', // POST
    body: payload, // 调拨数据
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('transfer') // 幂等键
  }) // 结束 request
} // 结束 createTransfer

export function saveTransfer(id: number, payload: TransferUpsert, idempotencyKey?: string) { // 保存调拨单
  return request<TransferOrder>(`/api/v1/transfers/${id}`, { // PUT 调拨
    method: 'PUT', // PUT
    body: payload, // 调拨数据
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('transfer-save') // 幂等键
  }) // 结束 request
} // 结束 saveTransfer

export function submitTransfer(id: number, idempotencyKey?: string) { // 提交调拨审批
  return request<TransferOrder>(`/api/v1/transfers/${id}/submit`, { // POST 提交
    method: 'POST', // POST
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('transfer-submit') // 幂等键
  }) // 结束 request
} // 结束 submitTransfer

export function executeTransfer(id: number, idempotencyKey?: string) { // 执行调拨过账
  return request<TransferOrder>(`/api/v1/transfers/${id}/execute`, { // POST 执行
    method: 'POST', // POST
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('transfer-execute') // 幂等键
  }) // 结束 request
} // 结束 executeTransfer

export function listApprovals(params: PageQuery = {}) { // 审批任务列表
  return request<PageResult<ApprovalTask>>('/api/v1/approvals', { params: pageParams(params) }) // GET 审批
} // 结束 listApprovals

export function approveApproval(id: number, comment?: string, idempotencyKey?: string) { // 同意审批
  return request<ApprovalTask>(`/api/v1/approvals/${id}/approve`, { // POST 同意
    method: 'POST', // POST
    body: { comment: comment ?? null }, // 审批意见
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('approval-approve') // 幂等键
  }) // 结束 request
} // 结束 approveApproval

export function rejectApproval(id: number, comment: string, idempotencyKey?: string) { // 驳回审批
  return request<ApprovalTask>(`/api/v1/approvals/${id}/reject`, { // POST 驳回
    method: 'POST', // POST
    body: { comment }, // 驳回意见必填
    idempotencyKey: idempotencyKey ?? createIdempotencyKey('approval-reject') // 幂等键
  }) // 结束 request
} // 结束 rejectApproval
