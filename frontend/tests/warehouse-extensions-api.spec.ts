/** 盘点调拨审批 API 封装。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { setAccessToken } from '../src/models/client' // import { setAccessToken 
import { // import {
  approveApproval, // approveApproval,
  createStockCount, // createStockCount,
  executeTransfer, // executeTransfer,
  listApprovals, // listApprovals,
  rejectApproval // rejectApproval
} from '../src/models/warehouse-extensions' // } from '../src/models/wa
import { getSystemRuntime } from '../src/models/followup' // import { getSystemRuntim

const jsonResponse = (body: unknown, status = 200) => // const jsonResponse = (bo
  new Response(JSON.stringify(body), { // new Response(JSON.string
    status, // status,
    headers: { 'content-type': 'application/json' } // headers: { 'content-type
  }) // })

describe('仓作业扩展 API', () => { // describe('仓作业扩展 API', ()
  let fetchMock: ReturnType<typeof vi.fn> // let fetchMock: ReturnTyp

  beforeEach(() => { // beforeEach(() => {
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    fetchMock = vi.fn().mockImplementation(() => jsonResponse({ total: 0, items: [] })) // fetchMock = vi.fn().mock
    vi.stubGlobal('fetch', fetchMock) // vi.stubGlobal('fetch', f
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.unstubAllGlobals() // vi.unstubAllGlobals()
  }) // })

  it('posts stock count with JWT and idempotency key', async () => { // it('posts stock count wi
    await createStockCount({ note: 'cycle', items: [{ product_id: 1, location_id: 2, counted_quantity: 3 }] }) // await createStockCount({
    const call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // const call = fetchMock.m
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/stock-counts')
    expect(call[1]).toMatchObject({ method: 'POST' }) // expect(call[1]).toMatchO
    expect(call[1].headers.Authorization).toBe('Bearer jwt-token') // expect(call[1].headers.A
    expect(call[1].headers['Idempotency-Key']).toMatch(/^stock-count-/) // expect(call[1].headers['
  }) // })

  it('executes a transfer with an idempotency prefix', async () => { // it('executes a transfer 
    await executeTransfer(5) // await executeTransfer(5)
    const call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // const call = fetchMock.m
    expect(call[0]).toBe('http://127.0.0.1:8000/api/v1/transfers/5/execute')
    expect(call[1].headers['Idempotency-Key']).toMatch(/^transfer-execute-/) // expect(call[1].headers['
  }) // })

  it('encodes approval list filters and sends a reject comment', async () => { // it('encodes approval lis
    await listApprovals({ page: 1, pageSize: 20, status: 'pending', businessType: 'stock_count' }) // await listApprovals({ pa
    expect(fetchMock).toHaveBeenCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/approvals?page=1&page_size=20&status=pending&business_type=stock_count',
      expect.anything() // expect.anything()
    ) // )
    await rejectApproval(8, '资料不完整') // await rejectApproval(8, 
    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/approvals/8/reject',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ comment: '资料不完整' }) }) // expect.objectContaining(
    ) // )
    await approveApproval(8) // await approveApproval(8)
    const last = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]! // const last = fetchMock.m
    expect(String(last[0])).toContain('/api/v1/approvals/8/approve') // expect(String(last[0])).
  }) // })

  it('requests system runtime including llm provider', async () => { // it('requests system runt
    fetchMock.mockImplementation(() => // fetchMock.mockImplementa
      jsonResponse({ cache_backend: 'memory', graph_engine: 'langgraph', llm_provider: 'none', inventory_source: 'mysql' }) // jsonResponse({ cache_bac
    ) // )
    const runtime = await getSystemRuntime() // const runtime = await ge
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/system/runtime', expect.anything())
    expect(runtime.llm_provider).toBe('none') // expect(runtime.llm_provi
  }) // })
}) // })
