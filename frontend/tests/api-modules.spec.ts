/** 各 model 请求路径与幂等头。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { listImports, listLocations, listProducts, listWarehouses } from '../src/models/catalog' // import { listImports, li
import { // import {
  getDashboardSummary, // getDashboardSummary,
  listAlerts, // listAlerts,
  listAuditLogs, // listAuditLogs,
  listBalances, // listBalances,
  listLedgers // listLedgers
} from '../src/models/inventory' // } from '../src/models/in
import { // import {
  allocateOutbound, // allocateOutbound,
  completeOutbound, // completeOutbound,
  confirmInbound, // confirmInbound,
  confirmPickingTask, // confirmPickingTask,
  createInbound, // createInbound,
  createOutbound, // createOutbound,
  listInbounds, // listInbounds,
  listOutbounds, // listOutbounds,
  listPickingTasks // listPickingTasks
} from '../src/models/operations' // } from '../src/models/op
import { setAccessToken } from '../src/models/client' // import { setAccessToken 

const jsonResponse = (body: unknown, status = 200) => // const jsonResponse = (bo
  new Response(JSON.stringify(body), { // new Response(JSON.string
    status, // status,
    headers: { 'content-type': 'application/json' } // headers: { 'content-type
  }) // })

describe('后端 API 模块', () => { // describe('后端 API 模块', ()
  let fetchMock: ReturnType<typeof vi.fn> // let fetchMock: ReturnTyp

  beforeEach(() => { // beforeEach(() => {
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    fetchMock = vi.fn().mockImplementation(() => jsonResponse({ total: 0, items: [] })) // fetchMock = vi.fn().mock
    vi.stubGlobal('fetch', fetchMock) // vi.stubGlobal('fetch', f
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.unstubAllGlobals() // vi.unstubAllGlobals()
  }) // })

  it('calls catalog endpoints with paging and filters', async () => { // it('calls catalog endpoi
    await listProducts({ keyword: 'mega', offset: 0, limit: 20 }) // await listProducts({ key
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/products?keyword=mega&offset=0&limit=20',
      expect.objectContaining({ method: 'GET' }) // expect.objectContaining(
    ) // )

    await listWarehouses() // await listWarehouses()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/warehouses', expect.anything())

    await listLocations({ warehouseId: 1, keyword: 'A-01', offset: 0, limit: 20 }) // await listLocations({ wa
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/locations?warehouse_id=1&keyword=A-01&offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )

    await listImports() // await listImports()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/imports', expect.anything())
  }) // })

  it('calls inventory, dashboard, alert, and audit endpoints', async () => { // it('calls inventory, das
    await getDashboardSummary() // await getDashboardSummar
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/dashboard/summary', expect.anything())

    await listBalances({ productId: 3, keyword: 'SKU-1', offset: 0, limit: 20 }) // await listBalances({ pro
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/inventory/balances?product_id=3&keyword=SKU-1&offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )

    await listLedgers({ keyword: '入库', limit: 100 }) // await listLedgers({ keyw
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/inventory/ledgers?keyword=%E5%85%A5%E5%BA%93&limit=100',
      expect.anything() // expect.anything()
    ) // )

    await listAlerts({ threshold: 5, offset: 0, limit: 20 }) // await listAlerts({ thres
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/alerts?threshold=5&offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )

    await listAuditLogs({ limit: 100 }) // await listAuditLogs({ li
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/audit-logs?limit=100',
      expect.anything() // expect.anything()
    ) // )
  }) // })

  it('calls operation list endpoints and write endpoints with idempotency keys', async () => { // it('calls operation list
    await listInbounds({ keyword: 'IN-1', status: 'draft' }) // await listInbounds({ key
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/inbounds?keyword=IN-1&status=draft',
      expect.anything() // expect.anything()
    ) // )

    await listOutbounds() // await listOutbounds()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/outbounds', expect.anything())

    await listPickingTasks() // await listPickingTasks()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/picking-tasks', expect.anything())

    const inboundPayload = { // const inboundPayload = {
      order_no: 'IN-TEST', // order_no: 'IN-TEST',
      note: 'test', // note: 'test',
      items: [{ product_id: 1, location_id: 2, quantity: 3 }] // items: [{ product_id: 1,
    } // }
    await createInbound(inboundPayload) // await createInbound(inbo
    let call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // let call = fetchMock.moc
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/inbounds')
    expect(call[1]).toMatchObject({ method: 'POST', body: JSON.stringify(inboundPayload) }) // expect(call[1]).toMatchO
    expect(call[1].headers['Idempotency-Key']).toMatch(/^inbound-/) // expect(call[1].headers['

    await confirmInbound(9) // await confirmInbound(9)
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/inbounds/9/confirm')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^inbound-confirm-/) // expect(call[1].headers['

    const outboundPayload = { // const outboundPayload = 
      order_no: 'OUT-TEST', // order_no: 'OUT-TEST',
      customer_id: 8, // customer_id: 8,
      note: 'test', // note: 'test',
      items: [{ product_id: 1, quantity: 2 }] // items: [{ product_id: 1,
    } // }
    await createOutbound(outboundPayload) // await createOutbound(out
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds')
    expect(call[1]).toMatchObject({ method: 'POST', body: JSON.stringify(outboundPayload) }) // expect(call[1]).toMatchO
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-/) // expect(call[1].headers['

    await allocateOutbound(9) // await allocateOutbound(9
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds/9/allocate')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-allocate-/) // expect(call[1].headers['

    await completeOutbound(9) // await completeOutbound(9
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds/9/complete')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-complete-/) // expect(call[1].headers['

    await confirmPickingTask(11) // await confirmPickingTask
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/picking-tasks/11/confirm')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^picking-confirm-/) // expect(call[1].headers['
  }) // })
}) // })
