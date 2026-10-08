/** 盘点调拨审批页。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { flushPromises, mount } from '@vue/test-utils' // import { flushPromises, 
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import ElementPlus from 'element-plus' // import ElementPlus from 
import AppShell from '../src/layouts/AppShell.vue' // import AppShell from '..
import router from '../src/router' // import router from '../s
import { useAppStore } from '../src/stores/app' // import { useAppStore } f
import { setAccessToken } from '../src/models/client' // import { setAccessToken 
import { listLocations, listProducts, listWarehouses } from '../src/models/catalog' // import { listLocations, 
import { listBalances } from '../src/models/inventory' // import { listBalances } 
import { executeTransfer, listApprovals, listStockCounts, listTransfers, submitStockCount } from '../src/models/warehouse-extensions' // import { executeTransfer

vi.mock('../src/models/catalog', () => ({ // vi.mock('../src/models/c
  listProducts: vi.fn(), // listProducts: vi.fn(),
  listLocations: vi.fn(), // listLocations: vi.fn(),
  listLocationMap: vi.fn(), // listLocationMap: vi.fn()
  listWarehouses: vi.fn(), // listWarehouses: vi.fn(),
  getProduct: vi.fn() // getProduct: vi.fn()
})) // }))

vi.mock('../src/models/inventory', () => ({ // vi.mock('../src/models/i
  listBalances: vi.fn() // listBalances: vi.fn()
})) // }))

vi.mock('../src/models/warehouse-extensions', () => ({ // vi.mock('../src/models/w
  listStockCounts: vi.fn(), // listStockCounts: vi.fn()
  createStockCount: vi.fn(), // createStockCount: vi.fn(
  saveStockCount: vi.fn(), // saveStockCount: vi.fn(),
  submitStockCount: vi.fn(), // submitStockCount: vi.fn(
  listTransfers: vi.fn(), // listTransfers: vi.fn(),
  createTransfer: vi.fn(), // createTransfer: vi.fn(),
  saveTransfer: vi.fn(), // saveTransfer: vi.fn(),
  submitTransfer: vi.fn(), // submitTransfer: vi.fn(),
  executeTransfer: vi.fn(), // executeTransfer: vi.fn()
  listApprovals: vi.fn(), // listApprovals: vi.fn(),
  approveApproval: vi.fn(), // approveApproval: vi.fn()
  rejectApproval: vi.fn() // rejectApproval: vi.fn()
})) // }))

function pageOf<T>(items: T[]) { // function pageOf<T>(items
  return { items, total: items.length, page: 1, page_size: 20 } // return { items, total: i
} // }

async function mountExtension(path: string, roles: string[]) { // async function mountExte
  const pinia = createPinia() // const pinia = createPini
  setActivePinia(pinia) // setActivePinia(pinia)
  const store = useAppStore() // const store = useAppStor
  store.token = 'jwt-token' // store.token = 'jwt-token
  store.currentUser = { user_id: 1, username: 'tester', display_name: '测试用户', roles } // store.currentUser = { us
  setAccessToken('jwt-token') // setAccessToken('jwt-toke
  await router.push(path) // await router.push(path)
  await router.isReady() // await router.isReady()
  const wrapper = mount(AppShell, { global: { plugins: [ElementPlus, router, pinia] } }) // const wrapper = mount(Ap
  await flushPromises() // await flushPromises()
  await flushPromises() // await flushPromises()
  return wrapper // return wrapper
} // }

describe('仓作业扩展页面', () => { // describe('仓作业扩展页面', () =
  beforeEach(() => { // beforeEach(() => {
    vi.mocked(listProducts).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listProducts).
    vi.mocked(listLocations).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listLocations)
    vi.mocked(listWarehouses).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listWarehouses
    vi.mocked(listBalances).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listBalances).
    vi.mocked(listStockCounts).mockResolvedValue(pageOf([])) // vi.mocked(listStockCount
    vi.mocked(listTransfers).mockResolvedValue(pageOf([])) // vi.mocked(listTransfers)
    vi.mocked(listApprovals).mockResolvedValue(pageOf([])) // vi.mocked(listApprovals)
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.clearAllMocks() // vi.clearAllMocks()
  }) // })

  it.each([ // it.each([
    ['/counting', '盘点管理'], // ['/counting', '盘点管理'],
    ['/transfer', '调拨管理'], // ['/transfer', '调拨管理'],
    ['/approvals', '审批中心'] // ['/approvals', '审批中心']
  ])('renders specialized content at %s', async (path, title) => { // ])('renders specialized 
    const wrapper = await mountExtension(path, ['warehouse_operator']) // const wrapper = await mo
    expect(wrapper.text()).toContain(title) // expect(wrapper.text()).t
    expect(wrapper.find('[data-testid="workspace-extension-page"]').exists()).toBe(true) // expect(wrapper.find('[da
  }) // })

  it('submits a counting stock-count order through the API', async () => { // it('submits a counting s
    vi.mocked(listStockCounts).mockResolvedValue( // vi.mocked(listStockCount
      pageOf([{ stock_count_order_id: 4, order_no: 'SC-20260910-000001', status: 'counting', items: [] }]) // pageOf([{ stock_count_or
    ) // )
    vi.mocked(submitStockCount).mockResolvedValue({ stock_count_order_id: 4, order_no: 'SC-20260910-000001', status: 'pending_approval' }) // vi.mocked(submitStockCou
    const wrapper = await mountExtension('/counting', ['warehouse_operator']) // const wrapper = await mo
    await wrapper.get('[data-testid="stock-count-submit-4"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(submitStockCount).toHaveBeenCalledWith(4) // expect(submitStockCount)
  }) // })

  it('executes only an executable transfer', async () => { // it('executes only an exe
    vi.mocked(listTransfers).mockResolvedValue( // vi.mocked(listTransfers)
      pageOf([{ transfer_order_id: 5, order_no: 'TR-20260910-000001', status: 'executable', items: [] }]) // pageOf([{ transfer_order
    ) // )
    vi.mocked(executeTransfer).mockResolvedValue({ transfer_order_id: 5, order_no: 'TR-20260910-000001', status: 'completed' }) // vi.mocked(executeTransfe
    const wrapper = await mountExtension('/transfer', ['warehouse_operator']) // const wrapper = await mo
    await wrapper.get('[data-testid="transfer-execute-5"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(executeTransfer).toHaveBeenCalledWith(5) // expect(executeTransfer).
  }) // })

  it('loads completed transfers only in history view', async () => { // it('loads completed tran
    vi.mocked(listTransfers).mockResolvedValue(pageOf([])) // vi.mocked(listTransfers)
    const wrapper = await mountExtension('/transfer', ['warehouse_operator']) // const wrapper = await mo
    expect(listTransfers).toHaveBeenCalledWith(expect.objectContaining({ status: 'draft,pending_approval,executable' })) // expect(listTransfers).to
    await wrapper.get('[data-testid="transfer-history"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(listTransfers).toHaveBeenCalledWith(expect.objectContaining({ status: 'completed,rejected' })) // expect(listTransfers).to
  }) // })
}) // })
