import { createIdempotencyKey, request } from './client'

export interface InboundItemCreate {
  product_id: number
  location_id: number
  quantity: number
}

export interface InboundCreate {
  order_no: string
  note?: string | null
  items: InboundItemCreate[]
}

export interface InboundOrder {
  inbound_order_id: number
  order_no: string
  status: string
  note: string | null
  created_at: string
}

export interface OutboundItemCreate {
  product_id: number
  quantity: number
}

export interface OutboundItem extends OutboundItemCreate {
  outbound_item_id: number
  allocated_quantity: number
  picked_quantity: number
}

export interface OutboundCreate {
  order_no: string
  customer_id?: number | null
  note?: string | null
  items: OutboundItemCreate[]
}

export interface OutboundOrder {
  outbound_order_id: number
  order_no: string
  status: string
  customer_id: number | null
  note: string | null
  created_at: string
}

export interface PickingTask {
  picking_task_id: number
  task_no: string
  outbound_order_id: number
  product_id: number
  location_id: number
  quantity: number
  status: string
}

export type OperationSubmission =
  | { type: 'inbound'; payload: InboundCreate }
  | { type: 'outbound'; payload: OutboundCreate }

export function listInbounds() {
  return request<{ items: InboundOrder[] }>('/api/v1/inbounds')
}

export function getInbound(orderId: number) {
  return request<InboundOrder & { items: InboundItemCreate[] }>(`/api/v1/inbounds/${orderId}`)
}

export function createInbound(payload: InboundCreate) {
  return request<InboundOrder>('/api/v1/inbounds', {
    method: 'POST',
    body: payload,
    idempotencyKey: createIdempotencyKey('inbound')
  })
}

export function confirmInbound(orderId: number) {
  return request<{ inbound_order_id: number; status: string }>(`/api/v1/inbounds/${orderId}/confirm`, {
    method: 'POST',
    idempotencyKey: createIdempotencyKey('inbound-confirm')
  })
}

export function listOutbounds() {
  return request<{ items: OutboundOrder[] }>('/api/v1/outbounds')
}

export function getOutbound(orderId: number) {
  return request<OutboundOrder & { items: OutboundItem[] }>(`/api/v1/outbounds/${orderId}`)
}

export function createOutbound(payload: OutboundCreate) {
  return request<OutboundOrder>('/api/v1/outbounds', {
    method: 'POST',
    body: payload,
    idempotencyKey: createIdempotencyKey('outbound')
  })
}

export function allocateOutbound(orderId: number) {
  return request<{ outbound_order_id: number; status: string }>(`/api/v1/outbounds/${orderId}/allocate`, {
    method: 'POST',
    idempotencyKey: createIdempotencyKey('outbound-allocate')
  })
}

export function completeOutbound(orderId: number) {
  return request<{ outbound_order_id: number; status: string }>(`/api/v1/outbounds/${orderId}/complete`, {
    method: 'POST',
    idempotencyKey: createIdempotencyKey('outbound-complete')
  })
}

export function listPickingTasks() {
  return request<{ items: PickingTask[] }>('/api/v1/picking-tasks')
}

export function confirmPickingTask(taskId: number) {
  return request<{ picking_task_id: number; status: string }>(`/api/v1/picking-tasks/${taskId}/confirm`, {
    method: 'POST',
    idempotencyKey: createIdempotencyKey('picking-confirm')
  })
}
