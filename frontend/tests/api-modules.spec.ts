import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listImports, listLocations, listProducts, listWarehouses } from '../src/api/catalog'
import {
  getDashboardSummary,
  listAlerts,
  listAuditLogs,
  listBalances,
  listLedgers
} from '../src/api/inventory'
import {
  allocateOutbound,
  completeOutbound,
  confirmInbound,
  confirmPickingTask,
  createInbound,
  createOutbound,
  listInbounds,
  listOutbounds,
  listPickingTasks
} from '../src/api/operations'
import { setAccessToken } from '../src/api/client'

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' }
  })

describe('后端 API 模块', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setAccessToken('jwt-token')
    fetchMock = vi.fn().mockImplementation(() => jsonResponse({ total: 0, items: [] }))
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls catalog endpoints with paging and filters', async () => {
    await listProducts({ keyword: 'mega', offset: 0, limit: 20 })
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/products?keyword=mega&offset=0&limit=20',
      expect.objectContaining({ method: 'GET' })
    )

    await listWarehouses()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/warehouses', expect.anything())

    await listLocations({ warehouseId: 1, offset: 0, limit: 20 })
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/locations?warehouse_id=1&offset=0&limit=20',
      expect.anything()
    )

    await listImports()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/imports', expect.anything())
  })

  it('calls inventory, dashboard, alert, and audit endpoints', async () => {
    await getDashboardSummary()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/dashboard/summary', expect.anything())

    await listBalances({ productId: 3, offset: 0, limit: 20 })
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/inventory/balances?product_id=3&offset=0&limit=20',
      expect.anything()
    )

    await listLedgers({ limit: 100 })
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/inventory/ledgers?limit=100',
      expect.anything()
    )

    await listAlerts({ threshold: 5 })
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/alerts?threshold=5', expect.anything())

    await listAuditLogs({ limit: 100 })
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/audit-logs?limit=100',
      expect.anything()
    )
  })

  it('calls operation list endpoints and write endpoints with idempotency keys', async () => {
    await listInbounds()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/inbounds', expect.anything())

    await listOutbounds()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/outbounds', expect.anything())

    await listPickingTasks()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/picking-tasks', expect.anything())

    const inboundPayload = {
      order_no: 'IN-TEST',
      note: 'test',
      items: [{ product_id: 1, location_id: 2, quantity: 3 }]
    }
    await createInbound(inboundPayload)
    let call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/inbounds')
    expect(call[1]).toMatchObject({ method: 'POST', body: JSON.stringify(inboundPayload) })
    expect(call[1].headers['Idempotency-Key']).toMatch(/^inbound-/)

    await confirmInbound(9)
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/inbounds/9/confirm')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^inbound-confirm-/)

    const outboundPayload = {
      order_no: 'OUT-TEST',
      customer_id: 8,
      note: 'test',
      items: [{ product_id: 1, quantity: 2 }]
    }
    await createOutbound(outboundPayload)
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds')
    expect(call[1]).toMatchObject({ method: 'POST', body: JSON.stringify(outboundPayload) })
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-/)

    await allocateOutbound(9)
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds/9/allocate')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-allocate-/)

    await completeOutbound(9)
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds/9/complete')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-complete-/)

    await confirmPickingTask(11)
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/picking-tasks/11/confirm')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^picking-confirm-/)
  })
})
