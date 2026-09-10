import { request, type QueryParams } from './client'

export interface Product {
  product_id: number
  sku_code: string
  source_product_code: string
  brand: string
  product_name: string
  category: string
  size: string
  function_feature: string
  color: string
  pallet_spec: string
  pallet_capacity: number
}

export interface Warehouse {
  warehouse_id: number
  warehouse_code: string
  warehouse_name: string
}

export interface Location {
  location_id: number
  warehouse_id: number
  location_code: string
  zone_code: string
  aisle_code: string
  rack_code: string
  position_code: string
}

export interface ImportBatch {
  batch_id: number
  batch_no: string
  dataset_name: string
  dataset_version: string
  imported_at: string
  total_rows: number
  valid_rows: number
  invalid_rows: number
  status: string
  notes: string | null
}

export interface PagedResult<T> {
  total?: number
  items: T[]
}

export function listProducts(params: { keyword?: string; offset?: number; limit?: number } = {}) {
  return request<PagedResult<Product>>('/api/v1/products', {
    params: params as QueryParams
  })
}

export function getProduct(productId: number) {
  return request<Product>(`/api/v1/products/${productId}`)
}

export function listWarehouses() {
  return request<PagedResult<Warehouse>>('/api/v1/warehouses')
}

export function listLocations(params: { warehouseId?: number; offset?: number; limit?: number } = {}) {
  return request<PagedResult<Location>>('/api/v1/locations', {
    params: {
      warehouse_id: params.warehouseId,
      offset: params.offset,
      limit: params.limit
    }
  })
}

export function listImports() {
  return request<PagedResult<ImportBatch>>('/api/v1/imports')
}
