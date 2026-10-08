/** API 基址、错误码、鉴权头。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { clearAccessToken, request, resolveApiBase, setAccessToken } from '../src/models/client' // import { clearAccessToke

const jsonResponse = (body: unknown, status = 200) => // const jsonResponse = (bo
  new Response(JSON.stringify(body), { // new Response(JSON.string
    status, // status,
    headers: { 'content-type': 'application/json' } // headers: { 'content-type
  }) // })

describe('API client', () => { // describe('API client', (
  let fetchMock: ReturnType<typeof vi.fn> // let fetchMock: ReturnTyp

  beforeEach(() => { // beforeEach(() => {
    clearAccessToken() // clearAccessToken()
    fetchMock = vi.fn() // fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock) // vi.stubGlobal('fetch', f
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.unstubAllGlobals() // vi.unstubAllGlobals()
    clearAccessToken() // clearAccessToken()
  }) // })

  it('injects the bearer token and serializes query parameters', async () => { // it('injects the bearer t
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    fetchMock.mockResolvedValue(jsonResponse({ total: 0, items: [] })) // fetchMock.mockResolvedVa

    await request('/api/v1/products', { params: { keyword: 'mega star', limit: 20, offset: 0 } }) // await request('/api/v1/p

    expect(fetchMock.mock.calls[0][0]).toBe( // expect(fetchMock.mock.ca
      'http://127.0.0.1:8000/api/v1/products?keyword=mega+star&limit=20&offset=0'
    ) // )
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ // expect(fetchMock.mock.ca
      headers: { // headers: {
        Authorization: 'Bearer jwt-token' // Authorization: 'Bearer j
      } // }
    }) // })
  }) // })

  it('sends JSON bodies with an idempotency key for write operations', async () => { // it('sends JSON bodies wi
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    fetchMock.mockResolvedValue(jsonResponse({ inbound_order_id: 1 }, 201)) // fetchMock.mockResolvedVa

    await request('/api/v1/inbounds', { // await request('/api/v1/i
      method: 'POST', // method: 'POST',
      body: { order_no: 'IN-001', items: [] }, // body: { order_no: 'IN-00
      idempotencyKey: 'idem-001' // idempotencyKey: 'idem-00
    }) // })

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ // expect(fetchMock.mock.ca
      method: 'POST', // method: 'POST',
      body: JSON.stringify({ order_no: 'IN-001', items: [] }), // body: JSON.stringify({ o
      headers: { // headers: {
        Authorization: 'Bearer jwt-token', // Authorization: 'Bearer j
        'Content-Type': 'application/json', // 'Content-Type': 'applica
        'Idempotency-Key': 'idem-001' // 'Idempotency-Key': 'idem
      } // }
    }) // })
  }) // })

  it('converts the backend error envelope into a readable ApiError', async () => { // it('converts the backend
    fetchMock.mockResolvedValue( // fetchMock.mockResolvedVa
      jsonResponse( // jsonResponse(
        { // {
          code: 'UNAUTHORIZED', // code: 'UNAUTHORIZED',
          message: '身份认证失败', // message: '身份认证失败',
          request_id: 'req-001', // request_id: 'req-001',
          details: {} // details: {}
        }, // },
        401 // 401
      ) // )
    ) // )

    await expect(request('/api/v1/auth/me')).rejects.toMatchObject({ // await expect(request('/a
      name: 'ApiError', // name: 'ApiError',
      message: '身份认证失败', // message: '身份认证失败',
      code: 'UNAUTHORIZED', // code: 'UNAUTHORIZED',
      status: 401, // status: 401,
      requestId: 'req-001' // requestId: 'req-001'
    }) // })
  }) // })

  it('uses the current origin when the API base is an empty string', () => { // it('uses the current ori
    expect(resolveApiBase(undefined)).toBe('http://127.0.0.1:8000')
    expect(resolveApiBase('http://127.0.0.1:8000/')).toBe('http://127.0.0.1:8000')
    expect(resolveApiBase('', 'http://frontend.local')).toBe('http://frontend.local')
  }) // })
}) // })
