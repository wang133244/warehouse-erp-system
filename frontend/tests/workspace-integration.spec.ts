import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import router from '../src/router'
import WorkspaceView from '../src/views/WorkspaceView.vue'
import { useAppStore } from '../src/stores/app'
import { setAccessToken } from '../src/api/client'

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' }
  })

async function mountWorkspace(path: string) {
  await router.push(path)
  await router.isReady()
  return mount(WorkspaceView, {
    global: {
      plugins: [ElementPlus, router]
    }
  })
}

describe('工作台真实数据接入', () => {
  let fetchMock: ReturnType<typeof vi.fn>

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
    fetchMock = vi.fn().mockImplementation(() => jsonResponse({ total: 0, items: [] }))
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders dashboard metrics from the backend summary', async () => {
    fetchMock.mockImplementation(() =>
      jsonResponse({
        stock_quantity: 1200,
        reserved_quantity: 200,
        available_quantity: 1000,
        inbound_draft: 3,
        outbound_pending: 4
      })
    )

    const wrapper = await mountWorkspace('/dashboard')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('1200')
    expect(text).toContain('200')
    expect(text).toContain('1000')
    expect(text).toContain('3')
    expect(text).toContain('4')
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/dashboard/summary', expect.anything())
  })

  it('renders product rows, total count, and server-side keyword search', async () => {
    fetchMock.mockImplementation(() =>
      jsonResponse({
        total: 1,
        items: [
          {
            product_id: 1,
            sku_code: 'SKU-001',
            source_product_code: 'P-001',
            brand: 'Mega Star',
            product_name: '测试商品',
            category: '测试分类',
            size: '标准',
            function_feature: '通用',
            color: '蓝色',
            pallet_spec: '120x100',
            pallet_capacity: 12
          }
        ]
      })
    )

    const wrapper = await mountWorkspace('/products')
    await flushPromises()

    expect(wrapper.text()).toContain('SKU-001')
    expect(wrapper.text()).toContain('测试商品')
    expect(wrapper.text()).toContain('共 1 条')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/v1/products?offset=0&limit=20',
      expect.anything()
    )

    const keywordInput = wrapper.find('input')
    expect(keywordInput.attributes('disabled')).toBeUndefined()
    await keywordInput.setValue('SKU-001')
    const searchButton = wrapper.findAll('button').find((button) => button.text() === '查询')
    expect(searchButton).toBeDefined()
    await searchButton!.trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/products?keyword=SKU-001&offset=0&limit=20',
      expect.anything()
    )
  })

  it('shows a connected empty state when the backend returns no inbound orders', async () => {
    const wrapper = await mountWorkspace('/inbounds')
    await flushPromises()

    expect(wrapper.text()).toContain('共 0 条')
    expect(wrapper.text()).toContain('FastAPI 已接入')
    expect(wrapper.text()).toContain('当前没有符合条件的数据')
    expect(wrapper.text()).not.toContain('后端接口尚未接入')
  })
})
