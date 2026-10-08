/** 入库、出库、拣货 API。 */
import { createIdempotencyKey, request, type QueryParams } from './client' // 引入请求封装与查询类型

export interface InboundItemCreate { // 入库明细创建
  product_id: number // 商品 ID
  location_id: number // 收货库位
  quantity: number // 数量
} // 结束 InboundItemCreate

export interface InboundCreate { // 新建入库单载荷
  order_no: string // 入库单号
  note?: string | null // 备注
  items: InboundItemCreate[] // 明细
} // 结束 InboundCreate

export interface InboundOrder { // 入库单
  inbound_order_id: number // 入库单主键
  order_no: string // 单号
  status: string // 状态
  note: string | null // 备注
  created_at: string // 创建时间
  username?: string | null // 创建人
} // 结束 InboundOrder

export interface OutboundItemCreate { // 出库明细创建
  product_id: number // 商品 ID
  quantity: number // 需求数量
} // 结束 OutboundItemCreate

export interface OutboundItem extends OutboundItemCreate { // 出库明细（含分配）
  outbound_item_id: number // 明细主键
  allocated_quantity: number // 已分配数量
  picked_quantity: number // 已拣数量
} // 结束 OutboundItem

export interface OutboundCreate { // 新建出库单载荷
  order_no: string // 出库单号
  customer_id?: number | null // 客户编号
  note?: string | null // 备注
  items: OutboundItemCreate[] // 明细
} // 结束 OutboundCreate

export interface OutboundOrder { // 出库单
  outbound_order_id: number // 出库单主键
  order_no: string // 单号
  status: string // 状态
  customer_id: number | null // 客户编号
  note: string | null // 备注
  created_at: string // 创建时间
} // 结束 OutboundOrder

export interface PickingTask { // 拣货任务
  picking_task_id: number // 任务主键
  task_no: string // 任务号
  outbound_order_id: number // 出库单 ID
  product_id: number // 商品 ID
  location_id: number // 拣货库位
  quantity: number // 拣货数量
  status: string // 任务状态
} // 结束 PickingTask

export type OperationSubmission = // 工作台新建单据联合类型
  | { type: 'inbound'; payload: InboundCreate } // 入库草稿
  | { type: 'outbound'; payload: OutboundCreate } // 出库草稿

export function listInbounds(params: { keyword?: string; status?: string } = {}) { // 入库单列表
  return request<{ total?: number; items: InboundOrder[] }>('/api/v1/inbounds', { // GET 入库
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listInbounds

export function getInbound(orderId: number) { // 入库单详情
  return request<InboundOrder & { items: InboundItemCreate[] }>(`/api/v1/inbounds/${orderId}`) // 含明细
} // 结束 getInbound

export function createInbound(payload: InboundCreate) { // 新建入库单
  return request<InboundOrder>('/api/v1/inbounds', { // POST 入库
    method: 'POST', // POST
    body: payload, // 入库数据
    idempotencyKey: createIdempotencyKey('inbound') // 幂等键
  }) // 结束 request
} // 结束 createInbound

export function confirmInbound(orderId: number) { // 确认入库过账
  return request<{ inbound_order_id: number; status: string }>(`/api/v1/inbounds/${orderId}/confirm`, { // POST 确认
    method: 'POST', // POST
    idempotencyKey: createIdempotencyKey('inbound-confirm') // 幂等键
  }) // 结束 request
} // 结束 confirmInbound

export function listOutbounds(params: { keyword?: string; status?: string } = {}) { // 出库单列表
  return request<{ total?: number; items: OutboundOrder[] }>('/api/v1/outbounds', { // GET 出库
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listOutbounds

export function getOutbound(orderId: number) { // 出库单详情
  return request<OutboundOrder & { items: OutboundItem[] }>(`/api/v1/outbounds/${orderId}`) // 含明细
} // 结束 getOutbound

export function createOutbound(payload: OutboundCreate) { // 新建出库单
  return request<OutboundOrder>('/api/v1/outbounds', { // POST 出库
    method: 'POST', // POST
    body: payload, // 出库数据
    idempotencyKey: createIdempotencyKey('outbound') // 幂等键
  }) // 结束 request
} // 结束 createOutbound

export function allocateOutbound(orderId: number) { // 分配库存并生成拣货
  return request<{ outbound_order_id: number; status: string }>(`/api/v1/outbounds/${orderId}/allocate`, { // POST 分配
    method: 'POST', // POST
    idempotencyKey: createIdempotencyKey('outbound-allocate') // 幂等键
  }) // 结束 request
} // 结束 allocateOutbound

export function completeOutbound(orderId: number) { // 完成出库扣账
  return request<{ outbound_order_id: number; status: string }>(`/api/v1/outbounds/${orderId}/complete`, { // POST 完成
    method: 'POST', // POST
    idempotencyKey: createIdempotencyKey('outbound-complete') // 幂等键
  }) // 结束 request
} // 结束 completeOutbound

export function listPickingTasks(params: { keyword?: string } = {}) { // 拣货任务列表
  return request<{ items: PickingTask[] }>('/api/v1/picking-tasks', { // GET 拣货
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listPickingTasks

export function confirmPickingTask(taskId: number) { // 确认拣货
  return request<{ picking_task_id: number; status: string }>(`/api/v1/picking-tasks/${taskId}/confirm`, { // POST 确认
    method: 'POST', // POST
    idempotencyKey: createIdempotencyKey('picking-confirm') // 幂等键
  }) // 结束 request
} // 结束 confirmPickingTask

export interface ReceivingItem { // 收货明细
  inbound_item_id: number // 入库明细 ID
  product_id: number // 商品 ID
  location_id: number // 库位 ID
  quantity: number // 应收数量
} // 结束 ReceivingItem

export interface ReceivingOrder { // 待收货入库单
  inbound_order_id: number // 入库单 ID
  order_no: string // 单号
  status: string // 状态
  note: string | null // 备注
  items: ReceivingItem[] // 明细
} // 结束 ReceivingOrder

export interface ReceiveConfirmPayload { // 收货确认载荷
  note?: string | null // 备注
  items: Array<{ inbound_item_id: number; received_quantity: number }> // 实收数量
} // 结束 ReceiveConfirmPayload

export function listReceivings() { // 待收货列表
  return request<{ total: number; items: ReceivingOrder[] }>('/api/v1/receivings') // GET 收货
} // 结束 listReceivings

export function confirmReceiving(orderId: number, payload: ReceiveConfirmPayload) { // 确认实收
  return request<{ inbound_order_id: number; status: string }>(`/api/v1/receivings/${orderId}/confirm`, { // POST 确认
    method: 'POST', // POST
    body: payload, // 实收明细
    idempotencyKey: createIdempotencyKey('receiving-confirm') // 幂等键
  }) // 结束 request
} // 结束 confirmReceiving

export interface OutboundReviewRow { // 出库复核行
  outbound_order_id: number // 出库单 ID
  order_no: string // 单号
  status: string // 状态
  customer_id: number | null // 客户编号
  review_comment: string | null // 复核意见
  items: OutboundItem[] // 明细
} // 结束 OutboundReviewRow

export function listOutboundReviews(params: { keyword?: string } = {}) { // 待复核列表
  return request<{ total: number; items: OutboundReviewRow[] }>('/api/v1/outbound-reviews', { // GET 复核
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listOutboundReviews

export function reviewOutbound(orderId: number, comment?: string) { // 复核出库单
  return request<{ outbound_order_id: number; status: string }>(`/api/v1/outbounds/${orderId}/review`, { // POST 复核
    method: 'POST', // POST
    body: { comment: comment ?? null }, // 复核意见
    idempotencyKey: createIdempotencyKey('outbound-review') // 幂等键
  }) // 结束 request
} // 结束 reviewOutbound
