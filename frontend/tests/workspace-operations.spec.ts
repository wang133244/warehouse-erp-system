import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import router from '../src/router'
import WorkspaceView from '../src/views/WorkspaceView.vue'
import { useAppStore } from '../src/stores/app'
import { setAccessToken } from '../src/api/client'
import {
  allocateOutbound,
  completeOutbound,
  confirmInbound,
  confirmPickingTask,
  getInbound,
  getOutbound,
  listInbounds,
  listOutbounds,
  listPickingTasks
} from '../src/api/operations'
import { listLocations, listProducts, listWarehouses } from '../src/api/catalog'

vi.mock('../src/api/catalog', () => ({
  listProducts: vi.fn(),
  listLocations: vi.fn(),
  listWarehouses: vi.fn(),
  listImports: vi.fn()
}))

vi.mock('../src/api/operations', () => ({
  listInbounds: vi.fn(),
  getInbound: vi.fn(),
  createInbound: vi.fn(),
  confirmInbound: vi.fn(),
  listOutbounds: vi.fn(),
  getOutbound: vi.fn(),
  createOutbound: vi.fn(),
  allocateOutbound: vi.fn(),
  completeOutbound: vi.fn(),
  listPickingTasks: vi.fn(),
  confirmPickingTask: vi.fn()
}))

const products = [
  {
    product_id: 3,
    sku_code: 'SKU-003',
    source_product_code: 'P-003',
    brand: 'Mega',
    product_name: '测试商品',
    category: '分类',
    size: '标准',
    function_feature: '通用',
    color: '蓝色',
    pallet_spec: '120x100',
    pallet_capacity: 10
  }
]
const locations = [
  {
    location_id: 7,
    warehouse_id: 1,
    location_code: 'A-01-01-01',
    zone_code: 'A',
    aisle_code: '01',
    rack_code: '01',
    position_code: '01'
  }
]

async function mountPage(path: string) {
  await router.push(path)
  await router.isReady()
  const wrapper = mount(WorkspaceView, { global: { plugins: [ElementPlus, router] } })
  await flushPromises()
  return wrapper
}

describe('工作台行操作', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const store = useAppStore()
    store.token = 'jwt-token'
    store.currentUser = {
      user_id: 1,
      username: 'admin',
      display_name: '系统管理员',
      roles: ['admin']
    }
    setAccessToken('jwt-token')
    vi.mocked(listProducts).mockResolvedValue({ total: 1, items: products })
    vi.mocked(listLocations).mockResolvedValue({ total: 1, items: locations })
    vi.mocked(listWarehouses).mockResolvedValue({
      total: 1,
      items: [{ warehouse_id: 1, warehouse_code: 'WH-001', warehouse_name: '主仓库' }]
    })
  })

  it('confirms a draft inbound order from its row action', async () => {
    vi.mocked(listInbounds).mockResolvedValue({
      items: [
        {
          inbound_order_id: 9,
          order_no: 'IN-009',
          status: 'draft',
          note: null,
          created_at: '2026-09-09T10:00:00Z'
        }
      ]
    })
    vi.mocked(getInbound).mockResolvedValue({
      inbound_order_id: 9,
      order_no: 'IN-009',
      status: 'draft',
      note: null,
      created_at: '2026-09-09T10:00:00Z',
      items: [{ product_id: 3, location_id: 7, quantity: 5 }]
    })
    vi.mocked(confirmInbound).mockResolvedValue({ inbound_order_id: 9, status: 'confirmed' })

    const wrapper = await mountPage('/inbounds')
    const rowAction = wrapper.find('[data-testid="row-action"]')
    expect(rowAction.text()).toContain('确认收货')
    await rowAction.trigger('click')
    await flushPromises()

    expect(confirmInbound).toHaveBeenCalledWith(9)
  })

  it('allocates a draft outbound order from its row action', async () => {
    vi.mocked(listOutbounds).mockResolvedValue({
      items: [
        {
          outbound_order_id: 12,
          order_no: 'OUT-012',
          status: 'draft',
          customer_id: 8,
          note: null,
          created_at: '2026-09-09T10:00:00Z'
        }
      ]
    })
    vi.mocked(getOutbound).mockResolvedValue({
      outbound_order_id: 12,
      order_no: 'OUT-012',
      status: 'draft',
      customer_id: 8,
      note: null,
      created_at: '2026-09-09T10:00:00Z',
      items: [{ product_id: 3, quantity: 4, allocated_quantity: 0, outbound_item_id: 1, picked_quantity: 0 }]
    })
    vi.mocked(allocateOutbound).mockResolvedValue({ outbound_order_id: 12, status: 'allocated' })

    const wrapper = await mountPage('/outbounds')
    const rowAction = wrapper.find('[data-testid="row-action"]')
    expect(rowAction.text()).toContain('分配库存')
    await rowAction.trigger('click')
    await flushPromises()

    expect(allocateOutbound).toHaveBeenCalledWith(12)
  })

  it('completes an allocated outbound order after picking', async () => {
    vi.mocked(listOutbounds).mockResolvedValue({
      items: [
        {
          outbound_order_id: 12,
          order_no: 'OUT-012',
          status: 'allocated',
          customer_id: 8,
          note: null,
          created_at: '2026-09-09T10:00:00Z'
        }
      ]
    })
    vi.mocked(getOutbound).mockResolvedValue({
      outbound_order_id: 12,
      order_no: 'OUT-012',
      status: 'allocated',
      customer_id: 8,
      note: null,
      created_at: '2026-09-09T10:00:00Z',
      items: [{ product_id: 3, quantity: 4, allocated_quantity: 4, outbound_item_id: 1, picked_quantity: 4 }]
    })
    vi.mocked(completeOutbound).mockResolvedValue({ outbound_order_id: 12, status: 'completed' })

    const wrapper = await mountPage('/outbounds')
    const rowAction = wrapper.find('[data-testid="row-action"]')
    expect(rowAction.text()).toContain('完成出库')
    await rowAction.trigger('click')
    await flushPromises()

    expect(completeOutbound).toHaveBeenCalledWith(12)
  })

  it('confirms an allocated picking task from its row action', async () => {
    vi.mocked(listPickingTasks).mockResolvedValue({
      items: [
        {
          picking_task_id: 15,
          task_no: 'PK-015',
          outbound_order_id: 12,
          product_id: 3,
          location_id: 7,
          quantity: 4,
          status: 'allocated'
        }
      ]
    })
    vi.mocked(confirmPickingTask).mockResolvedValue({ picking_task_id: 15, status: 'picked' })

    const wrapper = await mountPage('/picking')
    const rowAction = wrapper.find('[data-testid="row-action"]')
    expect(rowAction.text()).toContain('确认拣货')
    await rowAction.trigger('click')
    await flushPromises()

    expect(confirmPickingTask).toHaveBeenCalledWith(15)
  })
})
