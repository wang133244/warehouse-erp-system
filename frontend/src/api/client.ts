export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

const TOKEN_STORAGE_KEY = 'smart-erp-wms-access-token'

export class ApiError extends Error {
  status: number
  code: string
  requestId?: string

  constructor(message: string, status: number, code = 'HTTP_ERROR', requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

export type QueryValue = string | number | boolean | null | undefined
export type QueryParams = Record<string, QueryValue>
export type JsonBody = unknown

interface RequestOptions {
  method?: string
  body?: JsonBody
  params?: QueryParams
  token?: string | null
  skipAuth?: boolean
  idempotencyKey?: string
}

export function getAccessToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setAccessToken(token: string) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearAccessToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export function createIdempotencyKey(prefix = 'op') {
  const random =
    globalThis.crypto?.randomUUID?.() ??
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
  return `${prefix}-${random}`
}

function buildUrl(path: string, params?: QueryParams) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${API_BASE_URL}${normalizedPath}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }
  return url.toString()
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = options.skipAuth ? null : options.token ?? getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey

  let body: string | undefined
  if (options.body !== undefined) {
    body = JSON.stringify(options.body)
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path, options.params), {
      method: options.method ?? 'GET',
      headers,
      body
    })
  } catch {
    throw new ApiError('无法连接后端服务，请确认 FastAPI 已启动', 0, 'NETWORK_ERROR')
  }

  if (!response.ok) {
    let message = `请求失败（HTTP ${response.status}）`
    let code = 'HTTP_ERROR'
    let requestId: string | undefined
    try {
      const payload = (await response.json()) as {
        message?: string
        code?: string
        request_id?: string
      }
      message = payload.message ?? message
      code = payload.code ?? code
      requestId = payload.request_id
    } catch {
      // Keep the readable HTTP fallback for non-JSON responses.
    }
    throw new ApiError(message, response.status, code, requestId)
  }

  const text = await response.text()
  return (text ? JSON.parse(text) : null) as T
}
