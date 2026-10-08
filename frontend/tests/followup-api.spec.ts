/** 助手用户报表 API 封装。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { setAccessToken } from '../src/models/client' // import { setAccessToken 
import { createLocation, createProduct, getImport, listLocationMap, updateProduct } from '../src/models/catalog' // import { createLocation,
import { // import {
  ackAlert, // ackAlert,
  exportInventoryCsv, // exportInventoryCsv,
  getDashboardCharts // getDashboardCharts
} from '../src/models/inventory' // } from '../src/models/in
import { // import {
  confirmReceiving, // confirmReceiving,
  listOutboundReviews, // listOutboundReviews,
  listReceivings, // listReceivings,
  reviewOutbound // reviewOutbound
} from '../src/models/operations' // } from '../src/models/op
import { clearAgentSession, createAgentSession, createUser, deleteAgentSession, getAbcReport, getDailyReport, listAgentMessages, sendAgentMessage } from '../src/models/followup' // import { clearAgentSessi

const jsonResponse = (body: unknown, status = 200) => // const jsonResponse = (bo
  new Response(JSON.stringify(body), { // new Response(JSON.string
    status, // status,
    headers: { 'content-type': 'application/json' } // headers: { 'content-type
  }) // })

describe('后续闭环 API', () => { // describe('后续闭环 API', () 
  let fetchMock: ReturnType<typeof vi.fn> // let fetchMock: ReturnTyp

  beforeEach(() => { // beforeEach(() => {
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    fetchMock = vi.fn().mockImplementation(() => jsonResponse({ total: 0, items: [] })) // fetchMock = vi.fn().mock
    vi.stubGlobal('fetch', fetchMock) // vi.stubGlobal('fetch', f
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.unstubAllGlobals() // vi.unstubAllGlobals()
  }) // })

  it('calls receiving, review, catalog, user and assistant write endpoints with idempotency keys', async () => { // it('calls receiving, rev
    await listReceivings() // await listReceivings()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/receivings', expect.anything())

    await confirmReceiving(3, { note: '少收', items: [{ inbound_item_id: 1, received_quantity: 4 }] }) // await confirmReceiving(3
    let call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // let call = fetchMock.moc
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/receivings/3/confirm')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^receiving-confirm-/) // expect(call[1].headers['

    await listOutboundReviews() // await listOutboundReview
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/outbound-reviews', expect.anything())

    await reviewOutbound(9, '已核对') // await reviewOutbound(9, 
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/outbounds/9/review')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^outbound-review-/) // expect(call[1].headers['

    await createProduct({ // await createProduct({
      sku_code: 'SKU-NEW', // sku_code: 'SKU-NEW',
      source_product_code: 'SRC', // source_product_code: 'SR
      brand: '品牌', // brand: '品牌',
      product_name: '商品', // product_name: '商品',
      category: '分类', // category: '分类',
      size: '标准', // size: '标准',
      function_feature: '普通', // function_feature: '普通',
      color: '红', // color: '红',
      pallet_spec: '箱', // pallet_spec: '箱',
      pallet_capacity: 8 // pallet_capacity: 8
    }) // })
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/products')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^product-/) // expect(call[1].headers['

    await createLocation({ // await createLocation({
      warehouse_id: 1, // warehouse_id: 1,
      location_code: 'B-01', // location_code: 'B-01',
      zone_code: 'B', // zone_code: 'B',
      aisle_code: '01', // aisle_code: '01',
      rack_code: '01', // rack_code: '01',
      position_code: '01' // position_code: '01'
    }) // })
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/locations')

    await listLocationMap() // await listLocationMap()
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/locations/map', expect.anything())

    await createUser({ // await createUser({
      username: 'clerk', // username: 'clerk',
      password: 'password', // password: 'password',
      display_name: '仓管员', // display_name: '仓管员',
      roles: ['warehouse_operator'], // roles: ['warehouse_opera
      warehouse_ids: [1] // warehouse_ids: [1]
    }) // })
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/users')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^user-/) // expect(call[1].headers['

    await createAgentSession() // await createAgentSession
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/agents/sessions')

    await sendAgentMessage(2, '查询 SKU-1 的可用库存') // await sendAgentMessage(2
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/agents/sessions/2/messages')

    await clearAgentSession(2) // await clearAgentSession(
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/agents/sessions/2/clear')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^agent-clear-/) // expect(call[1].headers['

    await deleteAgentSession(2) // await deleteAgentSession
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/agents/sessions/2')
    expect(call[1]).toMatchObject({ method: 'DELETE' }) // expect(call[1]).toMatchO
    expect(call[1].headers['Idempotency-Key']).toMatch(/^agent-delete-/) // expect(call[1].headers['

    await listAgentMessages(2) // await listAgentMessages(
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/agents/sessions/2/messages',
      expect.objectContaining({ method: 'GET' }) // expect.objectContaining(
    ) // )

    await updateProduct(1, { is_active: false }) // await updateProduct(1, {
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/products/1')
    expect(call[1]).toMatchObject({ method: 'PATCH' }) // expect(call[1]).toMatchO

    await getImport(8) // await getImport(8)
    expect(fetchMock).toHaveBeenLastCalledWith('http://127.0.0.1:8000/api/v1/imports/8', expect.anything())

    await ackAlert(5, '已安排补货') // await ackAlert(5, '已安排补货
    call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // call = fetchMock.mock.ca
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/alerts/5/ack')
  }) // })

  it('requests dashboard charts and inventory export', async () => { // it('requests dashboard c
    Object.assign(URL, { // Object.assign(URL, {
      createObjectURL: vi.fn(() => 'blob:inventory'), // createObjectURL: vi.fn((
      revokeObjectURL: vi.fn() // revokeObjectURL: vi.fn()
    }) // })
    fetchMock.mockImplementation((url: string) => { // fetchMock.mockImplementa
      if (String(url).includes('/exports/')) { // if (String(url).includes
        return Promise.resolve(new Response('sku_code\nSKU-1', { status: 200, headers: { 'content-type': 'text/csv' } })) // return Promise.resolve(n
      } // }
      return Promise.resolve(jsonResponse({ inbound_by_day: [], outbound_by_day: [], stock_by_warehouse: [], low_stock: [] })) // return Promise.resolve(j
    }) // })
    await getDashboardCharts() // await getDashboardCharts
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/dashboard/charts', expect.anything())
    await exportInventoryCsv() // await exportInventoryCsv
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/exports/inventory', expect.anything())
    expect(URL.createObjectURL).toHaveBeenCalled() // expect(URL.createObjectU
  }) // })

  it('requests ABC classification report', async () => { // it('requests ABC classif
    fetchMock.mockImplementation(() => jsonResponse({ items: [], basis: 'on_hand', days: 7 })) // fetchMock.mockImplementa
    await getAbcReport() // await getAbcReport()
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/reports/abc', expect.anything())
    await getDailyReport() // await getDailyReport()
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/reports/daily', expect.anything())
    await getDailyReport(14) // await getDailyReport(14)
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/reports/daily?days=14', expect.anything())
  }) // })
}) // })
