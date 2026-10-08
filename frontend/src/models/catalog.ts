/** 商品、仓库、库位、CSV 导入、库位地图 API。 */
import { createIdempotencyKey, request, type QueryParams } from './client' // 引入请求封装与查询参数类型

export interface Product { // 商品主数据
  product_id: number // 商品主键
  sku_code: string // 系统 SKU
  source_product_code: string // 来源商品编码
  brand: string // 品牌
  product_name: string // 商品名称
  category: string // 分类
  size: string // 规格尺寸
  function_feature: string // 功能特征
  color: string // 颜色
  pallet_spec: string // 托盘规格
  pallet_capacity: number // 托盘容量
  is_active?: boolean // 是否启用
} // 结束 Product

export interface Warehouse { // 仓库
  warehouse_id: number // 仓库主键
  warehouse_code: string // 仓库编码
  warehouse_name: string // 仓库名称
} // 结束 Warehouse

export interface Location { // 库位
  location_id: number // 库位主键
  warehouse_id: number // 所属仓库
  location_code: string // 库位编码
  zone_code: string // 库区
  aisle_code: string // 巷道
  rack_code: string // 货架
  position_code: string // 储位
  is_active?: boolean // 是否可用
} // 结束 Location

export interface ImportBatch { // CSV 导入批次
  batch_id: number // 批次主键
  batch_no: string // 批次号
  dataset_name: string // 数据集/文件名
  dataset_version: string // 数据版本
  imported_at: string // 导入时间
  total_rows: number // 总行数
  valid_rows: number // 成功行数
  invalid_rows: number // 失败行数
  status: string // 导入状态
  notes: string | null // 备注
} // 结束 ImportBatch

export interface PagedResult<T> { // 通用分页结果
  total?: number // 总条数
  items: T[] // 当前页数据
} // 结束 PagedResult

export function listProducts(params: { keyword?: string; offset?: number; limit?: number } = {}) { // 商品列表
  return request<PagedResult<Product>>('/api/v1/products', { // GET 商品
    params: params as QueryParams // 查询参数
  }) // 结束 request
} // 结束 listProducts

export function getProduct(productId: number) { // 商品详情
  return request<Product>(`/api/v1/products/${productId}`) // 按 ID 查询
} // 结束 getProduct

export function listWarehouses() { // 仓库列表
  return request<PagedResult<Warehouse>>('/api/v1/warehouses') // GET 仓库
} // 结束 listWarehouses

export function createWarehouse(payload: { warehouse_code: string; warehouse_name: string }) { // 新建仓库
  return request<Warehouse>('/api/v1/warehouses', { // POST 仓库
    method: 'POST', // POST
    body: payload, // 编码与名称
    idempotencyKey: createIdempotencyKey('warehouse') // 幂等键
  }) // 结束 request
} // 结束 createWarehouse

export async function uploadProductCsv(file: File) { // 上传商品 CSV
  const content = await file.text() // 读文件文本
  return request<ImportBatch>('/api/v1/imports', { // POST 导入
    method: 'POST', // POST
    body: { filename: file.name, content }, // 文件名与内容
    idempotencyKey: createIdempotencyKey('import-csv') // 幂等键
  }) // 结束 request
} // 结束 uploadProductCsv

export interface LocationMapGroup { // 库位地图分组
  warehouse_id: number // 仓库 ID
  warehouse_code: string // 仓库编码
  zone_code: string // 库区
  location_count: number // 库位数量
  location_codes: string[] // 库位编码列表
} // 结束 LocationMapGroup

export function listLocations(params: { warehouseId?: number; zoneCode?: string; keyword?: string; offset?: number; limit?: number } = {}) { // 库位列表
  return request<PagedResult<Location>>('/api/v1/locations', { // GET 库位
    params: { // 查询参数映射到后端蛇形字段
      warehouse_id: params.warehouseId, // 仓库过滤
      zone_code: params.zoneCode, // 库区过滤
      keyword: params.keyword, // 关键字
      offset: params.offset, // 偏移
      limit: params.limit // 条数
    } // 结束 params
  }) // 结束 request
} // 结束 listLocations

export function listLocationMap() { // 库位地图
  return request<PagedResult<LocationMapGroup>>('/api/v1/locations/map') // GET 地图分组
} // 结束 listLocationMap

export function listImports(params: { keyword?: string } = {}) { // 导入批次列表
  return request<PagedResult<ImportBatch>>('/api/v1/imports', { params: params as QueryParams }) // GET 导入
} // 结束 listImports

export function getImport(batchId: number) { // 导入批次详情
  return request<ImportBatch>(`/api/v1/imports/${batchId}`) // 按批次 ID 查询
} // 结束 getImport

export function createProduct(payload: Omit<Product, 'product_id'>) { // 新建商品
  return request<Product>('/api/v1/products', { // POST 商品
    method: 'POST', // POST
    body: payload, // 商品字段
    idempotencyKey: createIdempotencyKey('product') // 幂等键
  }) // 结束 request
} // 结束 createProduct

export function updateProduct(productId: number, payload: Partial<Omit<Product, 'product_id' | 'sku_code'>> & { is_active?: boolean }) { // 更新商品
  return request<Product>(`/api/v1/products/${productId}`, { // PATCH 商品
    method: 'PATCH', // PATCH
    body: payload, // 可变字段
    idempotencyKey: createIdempotencyKey('product-update') // 幂等键
  }) // 结束 request
} // 结束 updateProduct

export function createLocation(payload: Omit<Location, 'location_id'>) { // 新建库位
  return request<Location>('/api/v1/locations', { // POST 库位
    method: 'POST', // POST
    body: payload, // 库位字段
    idempotencyKey: createIdempotencyKey('location') // 幂等键
  }) // 结束 request
} // 结束 createLocation

export function updateLocation(locationId: number, payload: Partial<Omit<Location, 'location_id' | 'warehouse_id' | 'location_code'>> & { is_active?: boolean }) { // 更新库位
  return request<Location>(`/api/v1/locations/${locationId}`, { // PATCH 库位
    method: 'PATCH', // PATCH
    body: payload, // 可变字段
    idempotencyKey: createIdempotencyKey('location-update') // 幂等键
  }) // 结束 request
} // 结束 updateLocation
