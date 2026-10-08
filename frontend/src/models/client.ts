/** fetch 内核：API 基址、Bearer、Idempotency-Key、ApiError。 */
export function resolveApiBase(raw: string | undefined, origin = typeof window !== 'undefined' ? window.location.origin : ''): string { // 解析 API 基址
  if (raw === '') { // 空字符串表示走当前站点同源
    return origin.replace(/\/+$/, '') // 去掉尾斜杠后的 origin
  } // 结束空字符串分支
  return (raw ?? 'http://127.0.0.1:8000').replace(/\/+$/, '') // 未配置则默认本地 8000
} // 结束 resolveApiBase

export const API_BASE_URL = resolveApiBase(import.meta.env.VITE_API_BASE_URL as string | undefined) // 构建期环境变量解析出的基址

const TOKEN_STORAGE_KEY = 'smart-erp-wms-access-token' // localStorage 中的令牌键

export class ApiError extends Error { // HTTP/业务错误
  status: number // HTTP 状态码，网络失败为 0
  code: string // 后端错误码
  requestId?: string // 请求追踪 ID

  constructor(message: string, status: number, code = 'HTTP_ERROR', requestId?: string) { // 构造错误
    super(message) // 调用 Error 基类
    this.name = 'ApiError' // 固定错误名
    this.status = status // 保存状态码
    this.code = code // 保存错误码
    this.requestId = requestId // 保存追踪 ID
  } // 结束 constructor
} // 结束 ApiError

export type QueryValue = string | number | boolean | null | undefined // 查询参数允许的值
export type QueryParams = Record<string, QueryValue> // 查询参数字典
export type JsonBody = unknown // JSON 请求体

interface RequestOptions { // request/requestText 的选项
  method?: string // HTTP 方法
  body?: JsonBody // JSON 体
  formData?: FormData // 表单体，优先于 JSON
  params?: QueryParams // URL 查询参数
  token?: string | null // 显式令牌
  skipAuth?: boolean // 跳过自动带令牌
  idempotencyKey?: string // 幂等键
} // 结束 RequestOptions

export function getAccessToken(): string | null { // 读取本地令牌
  return window.localStorage.getItem(TOKEN_STORAGE_KEY) // 从 localStorage 取
} // 结束 getAccessToken

export function setAccessToken(token: string) { // 写入本地令牌
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token) // 持久化
} // 结束 setAccessToken

export function clearAccessToken() { // 删除本地令牌
  window.localStorage.removeItem(TOKEN_STORAGE_KEY) // 移除键
} // 结束 clearAccessToken

export function createIdempotencyKey(prefix = 'op') { // 生成幂等键
  const random = // 优先 UUID，否则时间戳+随机串
    globalThis.crypto?.randomUUID?.() ?? // 浏览器 UUID
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}` // 降级随机串
  return `${prefix}-${random}` // 前缀加随机部分
} // 结束 createIdempotencyKey

function buildUrl(path: string, params?: QueryParams) { // 拼完整请求 URL
  const normalizedPath = path.startsWith('/') ? path : `/${path}` // 保证路径以 / 开头
  const base = API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000') // 基址回退
  const url = new URL(`${base}${normalizedPath}`) // 拼成 URL 对象
  if (params) { // 有查询参数
    for (const [key, value] of Object.entries(params)) { // 逐项写入
      if (value !== undefined && value !== null && value !== '') { // 跳过空值
        url.searchParams.set(key, String(value)) // 写入 query
      } // 结束空值判断
    } // 结束 for
  } // 结束 params 分支
  return url.toString() // 返回字符串 URL
} // 结束 buildUrl

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> { // JSON 请求
  const headers: Record<string, string> = { Accept: 'application/json' } // 默认 Accept
  const token = options.skipAuth ? null : options.token ?? getAccessToken() // 决定是否带令牌
  if (token) headers.Authorization = `Bearer ${token}` // 写入 Bearer
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey // 写入幂等键

  let body: BodyInit | undefined // 最终请求体
  if (options.formData) { // 有 FormData
    body = options.formData // 直接用表单
  } else if (options.body !== undefined) { // 有 JSON 体
    body = JSON.stringify(options.body) // 序列化
    headers['Content-Type'] = 'application/json' // JSON Content-Type
  } // 结束请求体分支

  let response: Response // fetch 响应
  try { // 发起网络请求
    response = await fetch(buildUrl(path, options.params), { // 调用 fetch
      method: options.method ?? 'GET', // 默认 GET
      headers, // 请求头
      body // 请求体
    }) // 结束 fetch
  } catch { // 网络层失败
    throw new ApiError('无法连接后端服务，请确认 FastAPI 已启动', 0, 'NETWORK_ERROR') // 包装为 ApiError
  } // 结束 catch

  if (!response.ok) { // HTTP 非 2xx
    let message = `请求失败（HTTP ${response.status}）` // 默认文案
    let code = 'HTTP_ERROR' // 默认错误码
    let requestId: string | undefined // 追踪 ID
    try { // 尝试解析 JSON 错误体
      const payload = (await response.json()) as { // 后端错误结构
        message?: string // 错误消息
        code?: string // 错误码
        request_id?: string // 追踪 ID
      } // 结束 payload 类型
      message = payload.message ?? message // 优先后端消息
      code = payload.code ?? code // 优先后端错误码
      requestId = payload.request_id // 取出追踪 ID
    } catch { // 非 JSON 响应
      // Keep the readable HTTP fallback for non-JSON responses.
    } // 结束 JSON 解析 catch
    throw new ApiError(message, response.status, code, requestId) // 抛出业务错误
  } // 结束非 ok 分支

  const text = await response.text() // 先读文本，兼容空 body
  return (text ? JSON.parse(text) : null) as T // 有内容则解析 JSON
} // 结束 request

export async function requestText(path: string, options: RequestOptions = {}): Promise<string> { // 拉纯文本/CSV
  const headers: Record<string, string> = { Accept: 'text/csv,application/json' } // 接受 CSV 或 JSON
  const token = options.skipAuth ? null : options.token ?? getAccessToken() // 决定令牌
  if (token) headers.Authorization = `Bearer ${token}` // 写入 Bearer
  let response: Response // fetch 响应
  try { // 发起请求
    response = await fetch(buildUrl(path, options.params), { // 调用 fetch
      method: options.method ?? 'GET', // 默认 GET
      headers // 请求头
    }) // 结束 fetch
  } catch { // 网络失败
    throw new ApiError('无法连接后端服务，请确认 FastAPI 已启动', 0, 'NETWORK_ERROR') // 包装错误
  } // 结束 catch
  if (!response.ok) { // HTTP 非 2xx
    throw new ApiError(`请求失败（HTTP ${response.status}）`, response.status) // 抛出错误
  } // 结束非 ok
  return response.text() // 返回文本
} // 结束 requestText

export async function downloadCsv(path: string, filename: string) { // 下载 CSV 文件
  const content = await requestText(path) // 拉取 CSV 文本
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' }) // 做成 Blob
  const url = URL.createObjectURL(blob) // 创建临时 URL
  const link = document.createElement('a') // 创建隐藏下载链接
  link.href = url // 指向 Blob
  link.download = filename // 指定文件名
  link.click() // 触发下载
  URL.revokeObjectURL(url) // 释放临时 URL
} // 结束 downloadCsv
