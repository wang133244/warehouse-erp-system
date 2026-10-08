/** 工作台入出库操作。 */
import { beforeEach, describe, expect, it, vi } from 'vitest' // import { beforeEach, des
import { flushPromises, mount } from '@vue/test-utils' // import { flushPromises, 
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import ElementPlus from 'element-plus' // import ElementPlus from 
import router from '../src/router' // import router from '../s
import WorkspaceView from '../src/views/WorkspaceView.vue' // import WorkspaceView fro
import { useAppStore } from '../src/stores/app' // import { useAppStore } f
import { setAccessToken } from '../src/models/client' // import { setAccessToken 
import { // import {
  allocateOutbound, // allocateOutbound,
  completeOutbound, // completeOutbound,
  confirmInbound, // confirmInbound,
  confirmPickingTask, // confirmPickingTask,
  getInbound, // getInbound,
  getOutbound, // getOutbound,
  listInbounds, // listInbounds,
  listOutbounds, // listOutbounds,
  listPickingTasks // listPickingTasks
} from '../src/models/operations' // } from '../src/models/op
import { listLocationMap, listLocations, listProducts, listWarehouses } from '../src/models/catalog' // import { listLocationMap

vi.mock('../src/models/catalog', () => ({ // vi.mock('../src/models/c
  listProducts: vi.fn(), // listProducts: vi.fn(),
  listLocations: vi.fn(), // listLocations: vi.fn(),
  listWarehouses: vi.fn(), // listWarehouses: vi.fn(),
  listImports: vi.fn(), // listImports: vi.fn(),
  listLocationMap: vi.fn(), // listLocationMap: vi.fn()
  createProduct: vi.fn(), // createProduct: vi.fn(),
  createLocation: vi.fn(), // createLocation: vi.fn(),
  updateProduct: vi.fn(), // updateProduct: vi.fn(),
  updateLocation: vi.fn(), // updateLocation: vi.fn(),
  getImport: vi.fn() // getImport: vi.fn()
})) // }))

vi.mock('../src/models/operations', () => ({ // vi.mock('../src/models/o
  listInbounds: vi.fn(), // listInbounds: vi.fn(),
  getInbound: vi.fn(), // getInbound: vi.fn(),
  createInbound: vi.fn(), // createInbound: vi.fn(),
  confirmInbound: vi.fn(), // confirmInbound: vi.fn(),
  listOutbounds: vi.fn(), // listOutbounds: vi.fn(),
  getOutbound: vi.fn(), // getOutbound: vi.fn(),
  createOutbound: vi.fn(), // createOutbound: vi.fn(),
  allocateOutbound: vi.fn(), // allocateOutbound: vi.fn(
  completeOutbound: vi.fn(), // completeOutbound: vi.fn(
  listPickingTasks: vi.fn(), // listPickingTasks: vi.fn(
  confirmPickingTask: vi.fn() // confirmPickingTask: vi.f
})) // }))

const products = [ // const products = [
  { // {
    product_id: 3, // product_id: 3,
    sku_code: 'SKU-003', // sku_code: 'SKU-003',
    source_product_code: 'P-003', // source_product_code: 'P-
    brand: 'Mega', // brand: 'Mega',
    product_name: '测试商品', // product_name: '测试商品',
    category: '分类', // category: '分类',
    size: '标准', // size: '标准',
    function_feature: '通用', // function_feature: '通用',
    color: '蓝色', // color: '蓝色',
    pallet_spec: '120x100', // pallet_spec: '120x100',
    pallet_capacity: 10 // pallet_capacity: 10
  } // }
] // ]
const locations = [ // const locations = [
  { // {
    location_id: 7, // location_id: 7,
    warehouse_id: 1, // warehouse_id: 1,
    location_code: 'A-01-01-01', // location_code: 'A-01-01-
    zone_code: 'A', // zone_code: 'A',
    aisle_code: '01', // aisle_code: '01',
    rack_code: '01', // rack_code: '01',
    position_code: '01' // position_code: '01'
  } // }
] // ]

async function mountPage(path: string) { // async function mountPage
  await router.push(path) // await router.push(path)
  await router.isReady() // await router.isReady()
  const wrapper = mount(WorkspaceView, { global: { plugins: [ElementPlus, router] } }) // const wrapper = mount(Wo
  await flushPromises() // await flushPromises()
  return wrapper // return wrapper
} // }

describe('工作台行操作', () => { // describe('工作台行操作', () =>
  beforeEach(() => { // beforeEach(() => {
    setActivePinia(createPinia()) // setActivePinia(createPin
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { // store.currentUser = {
      user_id: 1, // user_id: 1,
      username: 'admin', // username: 'admin',
      display_name: '系统管理员', // display_name: '系统管理员',
      roles: ['admin'] // roles: ['admin']
    } // }
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    vi.mocked(listProducts).mockResolvedValue({ total: 1, items: products }) // vi.mocked(listProducts).
    vi.mocked(listLocations).mockResolvedValue({ total: 1, items: locations }) // vi.mocked(listLocations)
    vi.mocked(listLocationMap).mockResolvedValue({ // vi.mocked(listLocationMa
      total: 1, // total: 1,
      items: [{ warehouse_id: 1, warehouse_code: 'WH-001', zone_code: 'A', location_count: 1, location_codes: ['A-01-01-01'] }] // items: [{ warehouse_id: 
    }) // })
    vi.mocked(listWarehouses).mockResolvedValue({ // vi.mocked(listWarehouses
      total: 1, // total: 1,
      items: [{ warehouse_id: 1, warehouse_code: 'WH-001', warehouse_name: '主仓库' }] // items: [{ warehouse_id: 
    }) // })
  }) // })

  it('confirms selected inbound drafts from the toolbar', async () => { // it('confirms selected in
    vi.mocked(listInbounds).mockResolvedValue({ // vi.mocked(listInbounds).
      items: [ // items: [
        { // {
          inbound_order_id: 9, // inbound_order_id: 9,
          order_no: 'IN-009', // order_no: 'IN-009',
          status: 'draft', // status: 'draft',
          note: null, // note: null,
          created_at: '2026-09-09T10:00:00Z' // created_at: '2026-09-09T
        } // }
      ] // ]
    }) // })
    vi.mocked(getInbound).mockResolvedValue({ // vi.mocked(getInbound).mo
      inbound_order_id: 9, // inbound_order_id: 9,
      order_no: 'IN-009', // order_no: 'IN-009',
      status: 'draft', // status: 'draft',
      note: null, // note: null,
      created_at: '2026-09-09T10:00:00Z', // created_at: '2026-09-09T
      items: [{ product_id: 3, location_id: 7, quantity: 5 }] // items: [{ product_id: 3,
    }) // })
    vi.mocked(confirmInbound).mockResolvedValue({ inbound_order_id: 9, status: 'confirmed' }) // vi.mocked(confirmInbound

    const wrapper = await mountPage('/inbounds') // const wrapper = await mo
    expect(wrapper.text()).toContain('待入库确认列表') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('IN-009') // expect(wrapper.text()).t
    await wrapper.get('[data-testid="inbound-select-all"]').trigger('click') // await wrapper.get('[data
    const confirmButton = wrapper.findAll('button').find((button) => button.text() === '收货确认') // const confirmButton = wr
    expect(confirmButton).toBeDefined() // expect(confirmButton).to
    await confirmButton!.trigger('click') // await confirmButton!.tri
    await flushPromises() // await flushPromises()

    expect(confirmInbound).toHaveBeenCalledWith(9) // expect(confirmInbound).t
  }) // })

  it('allocates a draft outbound order from its row action', async () => { // it('allocates a draft ou
    vi.mocked(listOutbounds).mockResolvedValue({ // vi.mocked(listOutbounds)
      items: [ // items: [
        { // {
          outbound_order_id: 12, // outbound_order_id: 12,
          order_no: 'OUT-012', // order_no: 'OUT-012',
          status: 'draft', // status: 'draft',
          customer_id: 8, // customer_id: 8,
          note: null, // note: null,
          created_at: '2026-09-09T10:00:00Z' // created_at: '2026-09-09T
        } // }
      ] // ]
    }) // })
    vi.mocked(getOutbound).mockResolvedValue({ // vi.mocked(getOutbound).m
      outbound_order_id: 12, // outbound_order_id: 12,
      order_no: 'OUT-012', // order_no: 'OUT-012',
      status: 'draft', // status: 'draft',
      customer_id: 8, // customer_id: 8,
      note: null, // note: null,
      created_at: '2026-09-09T10:00:00Z', // created_at: '2026-09-09T
      items: [{ product_id: 3, quantity: 4, allocated_quantity: 0, outbound_item_id: 1, picked_quantity: 0 }] // items: [{ product_id: 3,
    }) // })
    vi.mocked(allocateOutbound).mockResolvedValue({ outbound_order_id: 12, status: 'allocated' }) // vi.mocked(allocateOutbou

    const wrapper = await mountPage('/outbounds') // const wrapper = await mo
    const rowAction = wrapper.find('[data-testid="row-action"]') // const rowAction = wrappe
    expect(rowAction.text()).toContain('分配库存') // expect(rowAction.text())
    await rowAction.trigger('click') // await rowAction.trigger(
    await flushPromises() // await flushPromises()

    expect(allocateOutbound).toHaveBeenCalledWith(12) // expect(allocateOutbound)
  }) // })

  it('completes a reviewed outbound order after picking', async () => { // it('completes a reviewed
    vi.mocked(listOutbounds).mockResolvedValue({ // vi.mocked(listOutbounds)
      items: [ // items: [
        { // {
          outbound_order_id: 12, // outbound_order_id: 12,
          order_no: 'OUT-012', // order_no: 'OUT-012',
          status: 'reviewed', // status: 'reviewed',
          customer_id: 8, // customer_id: 8,
          note: null, // note: null,
          created_at: '2026-09-09T10:00:00Z' // created_at: '2026-09-09T
        } // }
      ] // ]
    }) // })
    vi.mocked(getOutbound).mockResolvedValue({ // vi.mocked(getOutbound).m
      outbound_order_id: 12, // outbound_order_id: 12,
      order_no: 'OUT-012', // order_no: 'OUT-012',
      status: 'reviewed', // status: 'reviewed',
      customer_id: 8, // customer_id: 8,
      note: null, // note: null,
      created_at: '2026-09-09T10:00:00Z', // created_at: '2026-09-09T
      items: [{ product_id: 3, quantity: 4, allocated_quantity: 4, outbound_item_id: 1, picked_quantity: 4 }] // items: [{ product_id: 3,
    }) // })
    vi.mocked(completeOutbound).mockResolvedValue({ outbound_order_id: 12, status: 'completed' }) // vi.mocked(completeOutbou

    const wrapper = await mountPage('/outbounds') // const wrapper = await mo
    const rowAction = wrapper.find('[data-testid="row-action"]') // const rowAction = wrappe
    expect(rowAction.text()).toContain('完成出库') // expect(rowAction.text())
    await rowAction.trigger('click') // await rowAction.trigger(
    await flushPromises() // await flushPromises()

    expect(completeOutbound).toHaveBeenCalledWith(12) // expect(completeOutbound)
  }) // })

  it('confirms an allocated picking task from its row action', async () => { // it('confirms an allocate
    vi.mocked(listPickingTasks).mockResolvedValue({ // vi.mocked(listPickingTas
      items: [ // items: [
        { // {
          picking_task_id: 15, // picking_task_id: 15,
          task_no: 'PK-015', // task_no: 'PK-015',
          outbound_order_id: 12, // outbound_order_id: 12,
          product_id: 3, // product_id: 3,
          location_id: 7, // location_id: 7,
          quantity: 4, // quantity: 4,
          status: 'allocated' // status: 'allocated'
        } // }
      ] // ]
    }) // })
    vi.mocked(confirmPickingTask).mockResolvedValue({ picking_task_id: 15, status: 'picked' }) // vi.mocked(confirmPicking

    const wrapper = await mountPage('/picking') // const wrapper = await mo
    const rowAction = wrapper.find('[data-testid="row-action"]') // const rowAction = wrappe
    expect(rowAction.text()).toContain('确认拣货') // expect(rowAction.text())
    await rowAction.trigger('click') // await rowAction.trigger(
    await flushPromises() // await flushPromises()

    expect(confirmPickingTask).toHaveBeenCalledWith(15) // expect(confirmPickingTas
  }) // })
}) // })
