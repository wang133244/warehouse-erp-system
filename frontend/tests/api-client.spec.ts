import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearAccessToken, request, setAccessToken } from '../src/api/client'

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' }
  })

describe('API client', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    clearAccessToken()
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearAccessToken()
  })

  it('injects the bearer token and serializes query parameters', async () => {
    setAccessToken('jwt-token')
    fetchMock.mockResolvedValue(jsonResponse({ total: 0, items: [] }))

    await request('/api/v1/products', { params: { keyword: 'mega star', limit: 20, offset: 0 } })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://127.0.0.1:8000/api/v1/products?keyword=mega+star&limit=20&offset=0'
    )
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      headers: {
        Authorization: 'Bearer jwt-token'
      }
    })
  })

  it('sends JSON bodies with an idempotency key for write operations', async () => {
    setAccessToken('jwt-token')
    fetchMock.mockResolvedValue(jsonResponse({ inbound_order_id: 1 }, 201))

    await request('/api/v1/inbounds', {
      method: 'POST',
      body: { order_no: 'IN-001', items: [] },
      idempotencyKey: 'idem-001'
    })

    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ order_no: 'IN-001', items: [] }),
      headers: {
        Authorization: 'Bearer jwt-token',
        'Content-Type': 'application/json',
        'Idempotency-Key': 'idem-001'
      }
    })
  })

  it('converts the backend error envelope into a readable ApiError', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          code: 'UNAUTHORIZED',
          message: '身份认证失败',
          request_id: 'req-001',
          details: {}
        },
        401
      )
    )

    await expect(request('/api/v1/auth/me')).rejects.toMatchObject({
      name: 'ApiError',
      message: '身份认证失败',
      code: 'UNAUTHORIZED',
      status: 401,
      requestId: 'req-001'
    })
  })
})
