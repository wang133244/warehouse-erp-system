/** 工作台与路由 store 集成。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { flushPromises, mount } from '@vue/test-utils' // import { flushPromises, 
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import ElementPlus from 'element-plus' // import ElementPlus from 
import router from '../src/router' // import router from '../s
import WorkspaceView from '../src/views/WorkspaceView.vue' // import WorkspaceView fro
import { useAppStore } from '../src/stores/app' // import { useAppStore } f
import { setAccessToken } from '../src/models/client' // import { setAccessToken 

const jsonResponse = (body: unknown, status = 200) => // const jsonResponse = (bo
  new Response(JSON.stringify(body), { // new Response(JSON.string
    status, // status,
    headers: { 'content-type': 'application/json' } // headers: { 'content-type
  }) // })

async function mountWorkspace(path: string) { // async function mountWork
  await router.push(path) // await router.push(path)
  await router.isReady() // await router.isReady()
  return mount(WorkspaceView, { // return mount(WorkspaceVi
    global: { // global: {
      plugins: [ElementPlus, router] // plugins: [ElementPlus, r
    } // }
  }) // })
} // }

describe('工作台真实数据接入', () => { // describe('工作台真实数据接入', ()
  let fetchMock: ReturnType<typeof vi.fn> // let fetchMock: ReturnTyp

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
    fetchMock = vi.fn().mockImplementation(() => jsonResponse({ total: 0, items: [] })) // fetchMock = vi.fn().mock
    vi.stubGlobal('fetch', fetchMock) // vi.stubGlobal('fetch', f
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.unstubAllGlobals() // vi.unstubAllGlobals()
  }) // })

  it('renders dashboard metrics from the backend summary', async () => { // it('renders dashboard me
    fetchMock.mockImplementation(() => // fetchMock.mockImplementa
      jsonResponse({ // jsonResponse({
        stock_quantity: 1200, // stock_quantity: 1200,
        reserved_quantity: 200, // reserved_quantity: 200,
        available_quantity: 1000, // available_quantity: 1000
        inbound_draft: 3, // inbound_draft: 3,
        outbound_pending: 4 // outbound_pending: 4
      }) // })
    ) // )

    const wrapper = await mountWorkspace('/dashboard') // const wrapper = await mo
    await flushPromises() // await flushPromises()

    const text = wrapper.text() // const text = wrapper.tex
    expect(text).toContain('1200') // expect(text).toContain('
    expect(text).toContain('200') // expect(text).toContain('
    expect(text).toContain('1000') // expect(text).toContain('
    expect(text).toContain('3') // expect(text).toContain('
    expect(text).toContain('4') // expect(text).toContain('
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/dashboard/summary', expect.anything())
  }) // })

  it('renders product rows, total count, and server-side keyword search', async () => { // it('renders product rows
    fetchMock.mockImplementation(() => // fetchMock.mockImplementa
      jsonResponse({ // jsonResponse({
        total: 1, // total: 1,
        items: [ // items: [
          { // {
            product_id: 1, // product_id: 1,
            sku_code: 'SKU-001', // sku_code: 'SKU-001',
            source_product_code: 'P-001', // source_product_code: 'P-
            brand: 'Mega Star', // brand: 'Mega Star',
            product_name: '测试商品', // product_name: '测试商品',
            category: '测试分类', // category: '测试分类',
            size: '标准', // size: '标准',
            function_feature: '通用', // function_feature: '通用',
            color: '蓝色', // color: '蓝色',
            pallet_spec: '120x100', // pallet_spec: '120x100',
            pallet_capacity: 12 // pallet_capacity: 12
          } // }
        ] // ]
      }) // })
    ) // )

    const wrapper = await mountWorkspace('/products') // const wrapper = await mo
    await flushPromises() // await flushPromises()

    expect(wrapper.text()).toContain('SKU-001') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('测试商品') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('共 1 条') // expect(wrapper.text()).t
    expect(fetchMock).toHaveBeenCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/products?offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )

    const keywordInput = wrapper.find('input') // const keywordInput = wra
    expect(keywordInput.attributes('disabled')).toBeUndefined() // expect(keywordInput.attr
    await keywordInput.setValue('SKU-001') // await keywordInput.setVa
    const searchButton = wrapper.findAll('button').find((button) => button.text() === '查询') // const searchButton = wra
    expect(searchButton).toBeDefined() // expect(searchButton).toB
    await searchButton!.trigger('click') // await searchButton!.trig
    await flushPromises() // await flushPromises()

    expect(fetchMock).toHaveBeenLastCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/products?keyword=SKU-001&offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )
  }) // })

  it('shows a connected empty state when the backend returns no inbound orders', async () => { // it('shows a connected em
    const wrapper = await mountWorkspace('/inbounds') // const wrapper = await mo
    await flushPromises() // await flushPromises()

    expect(wrapper.text()).toContain('共 0 条') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('FastAPI 已接入') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('当前没有符合条件的数据') // expect(wrapper.text()).t
    expect(wrapper.text()).not.toContain('后端接口尚未接入') // expect(wrapper.text()).n
  }) // })

  it('shows every warehouse zone in the location map, including C and D', async () => { // it('shows every warehous
    fetchMock.mockImplementation((url: string) => { // fetchMock.mockImplementa
      if (String(url).includes('/api/v1/locations/map')) { // if (String(url).includes
        return jsonResponse({ // return jsonResponse({
          total: 4, // total: 4,
          items: [ // items: [
            { warehouse_id: 1, warehouse_code: 'MEGA', zone_code: 'A', location_count: 3, location_codes: ['AF01A', 'AF01B', 'AF01C'] }, // { warehouse_id: 1, wareh
            { warehouse_id: 1, warehouse_code: 'MEGA', zone_code: 'B', location_count: 2, location_codes: ['BF01A', 'BF01B'] }, // { warehouse_id: 1, wareh
            { warehouse_id: 1, warehouse_code: 'MEGA', zone_code: 'C', location_count: 2, location_codes: ['CF01A', 'CF01B'] }, // { warehouse_id: 1, wareh
            { warehouse_id: 1, warehouse_code: 'MEGA', zone_code: 'D', location_count: 2, location_codes: ['DF01A', 'DF01B'] } // { warehouse_id: 1, wareh
          ] // ]
        }) // })
      } // }
      return jsonResponse({ total: 0, items: [] }) // return jsonResponse({ to
    }) // })

    const wrapper = await mountWorkspace('/locations') // const wrapper = await mo
    await flushPromises() // await flushPromises()
    const mapButton = wrapper.findAll('button').find((button) => button.text() === '库位信息') // const mapButton = wrappe
    expect(mapButton).toBeDefined() // expect(mapButton).toBeDe
    await mapButton!.trigger('click') // await mapButton!.trigger
    await flushPromises() // await flushPromises()

    expect(wrapper.text()).toContain('MEGA / C') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('MEGA / D') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('CF01A') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('CF01B') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('DF01A') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('DF01B') // expect(wrapper.text()).t
    expect(wrapper.find('.map-scroll').exists()).toBe(true) // expect(wrapper.find('.ma
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/locations/map', expect.anything())
  }) // })

  it('sends keyword queries for locations, inventory, and inbound drafts', async () => { // it('sends keyword querie
    fetchMock.mockImplementation((url: string) => { // fetchMock.mockImplementa
      const href = String(url) // const href = String(url)
      if (href.includes('/api/v1/products')) { // if (href.includes('/api/
        return jsonResponse({ // return jsonResponse({
          total: 1, // total: 1,
          items: [{ // items: [{
            product_id: 1, sku_code: 'SKU-001', source_product_code: 'P-001', brand: 'Mega', product_name: '测试商品', // product_id: 1, sku_code:
            category: '测试', size: '标准', function_feature: '通用', color: '蓝', pallet_spec: '120x100', pallet_capacity: 12 // category: '测试', size: '标
          }] // }]
        }) // })
      } // }
      if (href.includes('/api/v1/locations') && !href.includes('/map')) { // if (href.includes('/api/
        return jsonResponse({ // return jsonResponse({
          total: 1, // total: 1,
          items: [{ location_id: 1, warehouse_id: 1, location_code: 'A-01', zone_code: 'A', aisle_code: '01', rack_code: '01', position_code: '01', is_active: true }] // items: [{ location_id: 1
        }) // })
      } // }
      if (href.includes('/api/v1/warehouses')) { // if (href.includes('/api/
        return jsonResponse({ total: 1, items: [{ warehouse_id: 1, warehouse_code: 'WH-001', warehouse_name: '主仓' }] }) // return jsonResponse({ to
      } // }
      if (href.includes('/api/v1/inventory/balances')) { // if (href.includes('/api/
        return jsonResponse({ // return jsonResponse({
          total: 1, // total: 1,
          items: [{ // items: [{
            balance_id: 1, product_id: 1, location_id: 1, quantity: 8, reserved_quantity: 0, frozen_quantity: 0, // balance_id: 1, product_i
            available_quantity: 8, sku_code: 'SKU-001', source_product_code: 'P-001', location_code: 'A-01' // available_quantity: 8, s
          }] // }]
        }) // })
      } // }
      if (/\/api\/v1\/inbounds\/\d+/.test(href)) { // if (/\/api\/v1\/inbounds
        return jsonResponse({ inbound_order_id: 9, order_no: 'IN-009', status: 'draft', note: null, items: [{ product_id: 1, location_id: 1, quantity: 2 }] }) // return jsonResponse({ in
      } // }
      if (href.includes('/api/v1/inbounds')) { // if (href.includes('/api/
        return jsonResponse({ total: 1, items: [{ inbound_order_id: 9, order_no: 'IN-009', status: 'draft', note: null, created_at: '2026-09-09T10:00:00Z' }] }) // return jsonResponse({ to
      } // }
      return jsonResponse({ total: 0, items: [] }) // return jsonResponse({ to
    }) // })

    const locations = await mountWorkspace('/locations') // const locations = await 
    await flushPromises() // await flushPromises()
    await locations.find('input').setValue('A-01') // await locations.find('in
    await locations.findAll('button').find((button) => button.text() === '查询')!.trigger('click') // await locations.findAll(
    await flushPromises() // await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/locations?keyword=A-01&offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )

    const inventory = await mountWorkspace('/inventory') // const inventory = await 
    await flushPromises() // await flushPromises()
    await inventory.find('input').setValue('SKU-001') // await inventory.find('in
    await inventory.findAll('button').find((button) => button.text() === '查询')!.trigger('click') // await inventory.findAll(
    await flushPromises() // await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/inventory/balances?keyword=SKU-001&offset=0&limit=20',
      expect.anything() // expect.anything()
    ) // )

    const inbounds = await mountWorkspace('/inbounds') // const inbounds = await m
    await flushPromises() // await flushPromises()
    await inbounds.find('input').setValue('IN-009') // await inbounds.find('inp
    await inbounds.findAll('button').find((button) => button.text() === '查询')!.trigger('click') // await inbounds.findAll('
    await flushPromises() // await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith( // expect(fetchMock).toHave
      'http://127.0.0.1:8000/api/v1/inbounds?keyword=IN-009&status=draft',
      expect.anything() // expect.anything()
    ) // )
  }) // })

  it('shows inbound or outbound direction on stock ledger rows', async () => { // it('shows inbound or out
    fetchMock.mockImplementation((url: string) => { // fetchMock.mockImplementa
      if (String(url).includes('/api/v1/inventory/ledgers')) { // if (String(url).includes
        return jsonResponse({ // return jsonResponse({
          items: [{ // items: [{
            ledger_id: 11, product_id: 1, location_id: 1, transaction_type: 'inbound', quantity_delta: 4, // ledger_id: 11, product_i
            before_quantity: 0, after_quantity: 4, source_type: 'inbound_order', source_id: 9, created_at: '2026-09-09T10:00:00Z' // before_quantity: 0, afte
          }] // }]
        }) // })
      } // }
      if (String(url).includes('/api/v1/products')) { // if (String(url).includes
        return jsonResponse({ // return jsonResponse({
          total: 1, // total: 1,
          items: [{ // items: [{
            product_id: 1, sku_code: 'SKU-001', source_product_code: 'P-001', brand: 'Mega', product_name: '测试商品', // product_id: 1, sku_code:
            category: '测试', size: '标准', function_feature: '通用', color: '蓝', pallet_spec: '120x100', pallet_capacity: 12 // category: '测试', size: '标
          }] // }]
        }) // })
      } // }
      if (String(url).includes('/api/v1/locations')) { // if (String(url).includes
        return jsonResponse({ // return jsonResponse({
          total: 1, // total: 1,
          items: [{ location_id: 1, warehouse_id: 1, location_code: 'A-01', zone_code: 'A', aisle_code: '01', rack_code: '01', position_code: '01', is_active: true }] // items: [{ location_id: 1
        }) // })
      } // }
      return jsonResponse({ total: 0, items: [] }) // return jsonResponse({ to
    }) // })

    const wrapper = await mountWorkspace('/inventory-ledger') // const wrapper = await mo
    await flushPromises() // await flushPromises()
    expect(wrapper.text()).toContain('入库') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('变动方向') // expect(wrapper.text()).t
  }) // })
}) // })
