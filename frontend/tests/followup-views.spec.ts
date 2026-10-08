/** 助手报表用户页与换用户清会话。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { flushPromises, mount } from '@vue/test-utils' // import { flushPromises, 
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import ElementPlus, { ElMessageBox } from 'element-plus' // import ElementPlus, { El
import AppShell from '../src/layouts/AppShell.vue' // import AppShell from '..
import UsersView from '../src/views/UsersView.vue' // import UsersView from '.
import router from '../src/router' // import router from '../s
import { useAppStore } from '../src/stores/app' // import { useAppStore } f
import { ApiError, setAccessToken } from '../src/models/client' // import { ApiError, setAc
import { listLocations, listProducts, listWarehouses } from '../src/models/catalog' // import { listLocations, 
import { confirmInbound, getInbound, listInbounds, listOutboundReviews, reviewOutbound } from '../src/models/operations' // import { confirmInbound,
import { createAgentSession, clearAgentSession, createUser, deleteUser, deleteAgentSession, listAgentSessions, listRoles, listUsers, sendAgentMessage, listAgentMessages, getAbcReport, getTurnoverReport, getDailyReport, getWeeklyReport, getPickingEfficiency, getSystemRuntime } from '../src/models/followup' // import { createAgentSess

vi.mock('../src/models/catalog', () => ({ // vi.mock('../src/models/c
  listProducts: vi.fn(), // listProducts: vi.fn(),
  listLocations: vi.fn(), // listLocations: vi.fn(),
  listLocationMap: vi.fn(), // listLocationMap: vi.fn()
  listWarehouses: vi.fn(), // listWarehouses: vi.fn(),
  listImports: vi.fn(), // listImports: vi.fn(),
  createProduct: vi.fn(), // createProduct: vi.fn(),
  createLocation: vi.fn(), // createLocation: vi.fn(),
  createWarehouse: vi.fn(), // createWarehouse: vi.fn()
  uploadProductCsv: vi.fn(), // uploadProductCsv: vi.fn(
  updateProduct: vi.fn(), // updateProduct: vi.fn(),
  updateLocation: vi.fn() // updateLocation: vi.fn()
})) // }))

vi.mock('../src/models/warehouse-extensions', () => ({ // vi.mock('../src/models/w
  listStockCounts: vi.fn(async () => ({ items: [], total: 0 })), // listStockCounts: vi.fn(a
  createStockCount: vi.fn(), // createStockCount: vi.fn(
  saveStockCount: vi.fn(), // saveStockCount: vi.fn(),
  submitStockCount: vi.fn() // submitStockCount: vi.fn(
})) // }))

vi.mock('../src/models/operations', async () => { // vi.mock('../src/models/o
  const actual = await vi.importActual<typeof import('../src/models/operations')>('../src/models/operations') // const actual = await vi.
  return { // return {
    ...actual, // ...actual,
    listReceivings: vi.fn(), // listReceivings: vi.fn(),
    confirmReceiving: vi.fn(), // confirmReceiving: vi.fn(
    listInbounds: vi.fn(), // listInbounds: vi.fn(),
    getInbound: vi.fn(), // getInbound: vi.fn(),
    confirmInbound: vi.fn(), // confirmInbound: vi.fn(),
    listOutboundReviews: vi.fn(), // listOutboundReviews: vi.
    reviewOutbound: vi.fn(), // reviewOutbound: vi.fn(),
    completeOutbound: vi.fn() // completeOutbound: vi.fn(
  } // }
}) // })

vi.mock('../src/models/followup', () => ({ // vi.mock('../src/models/f
  listUsers: vi.fn(), // listUsers: vi.fn(),
  createUser: vi.fn(), // createUser: vi.fn(),
  updateUser: vi.fn(), // updateUser: vi.fn(),
  deleteUser: vi.fn(), // deleteUser: vi.fn(),
  listRoles: vi.fn(), // listRoles: vi.fn(),
  createAgentSession: vi.fn(), // createAgentSession: vi.f
  clearAgentSession: vi.fn(), // clearAgentSession: vi.fn
  deleteAgentSession: vi.fn(), // deleteAgentSession: vi.f
  listAgentSessions: vi.fn(), // listAgentSessions: vi.fn
  listAgentMessages: vi.fn(), // listAgentMessages: vi.fn
  sendAgentMessage: vi.fn(), // sendAgentMessage: vi.fn(
  getAbcReport: vi.fn(), // getAbcReport: vi.fn(),
  getTurnoverReport: vi.fn(), // getTurnoverReport: vi.fn
  getDailyReport: vi.fn(), // getDailyReport: vi.fn(),
  getWeeklyReport: vi.fn(), // getWeeklyReport: vi.fn()
  getPickingEfficiency: vi.fn(), // getPickingEfficiency: vi
  getSystemRuntime: vi.fn() // getSystemRuntime: vi.fn(
})) // }))

async function mountPage(path: string, roles: string[]) { // async function mountPage
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

describe('后续闭环页面', () => { // describe('后续闭环页面', () =>
  beforeEach(() => { // beforeEach(() => {
    vi.mocked(listProducts).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listProducts).
    vi.mocked(listLocations).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listLocations)
    vi.mocked(listWarehouses).mockResolvedValue({ items: [], total: 0 }) // vi.mocked(listWarehouses
    vi.mocked(listInbounds).mockResolvedValue({ // vi.mocked(listInbounds).
      total: 1, // total: 1,
      items: [{ inbound_order_id: 7, order_no: 'IN-7', status: 'draft', note: null, created_at: '2026-09-09T10:00:00Z' }] // items: [{ inbound_order_
    }) // })
    vi.mocked(getInbound).mockResolvedValue({ // vi.mocked(getInbound).mo
      inbound_order_id: 7, // inbound_order_id: 7,
      order_no: 'IN-7', // order_no: 'IN-7',
      status: 'draft', // status: 'draft',
      note: null, // note: null,
      created_at: '2026-09-09T10:00:00Z', // created_at: '2026-09-09T
      items: [{ product_id: 1, location_id: 1, quantity: 4 }] // items: [{ product_id: 1,
    }) // })
    vi.mocked(confirmInbound).mockResolvedValue({ inbound_order_id: 7, status: 'confirmed' }) // vi.mocked(confirmInbound
    vi.mocked(listOutboundReviews).mockResolvedValue({ // vi.mocked(listOutboundRe
      total: 1, // total: 1,
      items: [{ outbound_order_id: 8, order_no: 'OUT-8', status: 'picked', customer_id: 2, review_comment: null, items: [{ outbound_item_id: 1, product_id: 1, quantity: 3, allocated_quantity: 3, picked_quantity: 3 }] }] // items: [{ outbound_order
    }) // })
    vi.mocked(listUsers).mockResolvedValue({ // vi.mocked(listUsers).moc
      total: 1, // total: 1,
      items: [{ user_id: 1, username: 'admin', display_name: '管理员', is_active: true, roles: ['admin'], warehouse_ids: [] }] // items: [{ user_id: 1, us
    }) // })
    vi.mocked(createUser).mockResolvedValue({ // vi.mocked(createUser).mo
      user_id: 9, // user_id: 9,
      username: 'clerk', // username: 'clerk',
      display_name: '仓管员', // display_name: '仓管员',
      is_active: true, // is_active: true,
      roles: ['warehouse_operator'], // roles: ['warehouse_opera
      warehouse_ids: [1] // warehouse_ids: [1]
    }) // })
    vi.mocked(listRoles).mockResolvedValue({ // vi.mocked(listRoles).moc
      items: [ // items: [
        { role_id: 1, role_code: 'admin', role_name: '系统管理员' }, // { role_id: 1, role_code:
        { role_id: 2, role_code: 'warehouse_operator', role_name: '仓库操作员' } // { role_id: 2, role_code:
      ] // ]
    }) // })
    vi.mocked(listAgentSessions).mockResolvedValue({ items: [] }) // vi.mocked(listAgentSessi
    vi.mocked(listAgentMessages).mockResolvedValue({ items: [] }) // vi.mocked(listAgentMessa
    vi.mocked(createAgentSession).mockResolvedValue({ session_id: 3, title: '新会话', created_at: null }) // vi.mocked(createAgentSes
    vi.mocked(clearAgentSession).mockResolvedValue({ session_id: 4, title: '新会话', created_at: null }) // vi.mocked(clearAgentSess
    vi.mocked(deleteAgentSession).mockResolvedValue({ session_id: 4, deleted: true }) // vi.mocked(deleteAgentSes
    vi.mocked(sendAgentMessage).mockResolvedValue({ // vi.mocked(sendAgentMessa
      message_id: 9, // message_id: 9,
      session_id: 3, // session_id: 3,
      role: 'assistant', // role: 'assistant',
      content: '查询到 SKU-1 的可用库存', // content: '查询到 SKU-1 的可用库
      tool_calls: [{ name: 'query_inventory' }], // tool_calls: [{ name: 'qu
      draft: null // draft: null
    }) // })
    vi.mocked(getAbcReport).mockResolvedValue({ // vi.mocked(getAbcReport).
      basis: 'on_hand', // basis: 'on_hand',
      items: [{ product_id: 1, sku_code: 'SKU-1', product_name: '商品', score: 4, share: 1, class: 'A', basis: 'on_hand' }] // items: [{ product_id: 1,
    }) // })
    vi.mocked(getTurnoverReport).mockResolvedValue({ // vi.mocked(getTurnoverRep
      items: [{ product_id: 1, sku_code: 'SKU-1', product_name: '商品', outbound_quantity: 0, on_hand_quantity: 4, turnover_rate: 0 }] // items: [{ product_id: 1,
    }) // })
    vi.mocked(getDailyReport).mockResolvedValue({ // vi.mocked(getDailyReport
      days: 7, // days: 7,
      items: [{ date: '2026-09-11', inbound_quantity: 5, outbound_quantity: 0 }] // items: [{ date: '2026-09
    }) // })
    vi.mocked(getWeeklyReport).mockResolvedValue({ // vi.mocked(getWeeklyRepor
      weeks: 4, // weeks: 4,
      items: [{ week: '2026-W37', inbound_quantity: 5, outbound_quantity: 0 }] // items: [{ week: '2026-W3
    }) // })
    vi.mocked(getPickingEfficiency).mockResolvedValue({ // vi.mocked(getPickingEffi
      total_tasks: 0, // total_tasks: 0,
      completed_tasks: 0, // completed_tasks: 0,
      completion_rate: 0, // completion_rate: 0,
      average_confirm_seconds: 0 // average_confirm_seconds:
    }) // })
    vi.mocked(getSystemRuntime).mockResolvedValue({ // vi.mocked(getSystemRunti
      cache_backend: 'memory', // cache_backend: 'memory',
      graph_engine: 'langgraph', // graph_engine: 'langgraph
      llm_provider: 'none', // llm_provider: 'none',
      inventory_source: 'mysql' // inventory_source: 'mysql
    }) // })
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.clearAllMocks() // vi.clearAllMocks()
  }) // })

  it('lets operators confirm inbound drafts from the merged inbound list', async () => { // it('lets operators confi
    const wrapper = await mountPage('/inbounds', ['warehouse_operator']) // const wrapper = await mo
    expect(wrapper.text()).toContain('待入库确认列表') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('IN-7') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('历史记录') // expect(wrapper.text()).t
    await wrapper.get('[data-testid="inbound-select-all"]').trigger('click') // await wrapper.get('[data
    const confirmButton = wrapper.findAll('button').find((button) => button.text() === '收货确认') // const confirmButton = wr
    expect(confirmButton).toBeDefined() // expect(confirmButton).to
    await confirmButton!.trigger('click') // await confirmButton!.tri
    await flushPromises() // await flushPromises()
    expect(confirmInbound).toHaveBeenCalledWith(7) // expect(confirmInbound).t
  }) // })

  it('lets operators review picked outbound orders', async () => { // it('lets operators revie
    const wrapper = await mountPage('/outbound-review', ['warehouse_operator']) // const wrapper = await mo
    expect(wrapper.text()).toContain('OUT-8') // expect(wrapper.text()).t
    await wrapper.get('[data-testid="outbound-review-8"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(reviewOutbound).toHaveBeenCalled() // expect(reviewOutbound).t
  }) // })

  it('hides system management from operators', async () => { // it('hides system managem
    const wrapper = await mountPage('/dashboard', ['warehouse_operator']) // const wrapper = await mo
    expect(wrapper.text()).not.toContain('系统管理') // expect(wrapper.text()).n
    expect(wrapper.find('[data-testid="create-user"]').exists()).toBe(false) // expect(wrapper.find('[da
  }) // })

  it('validates new users before calling the API', async () => { // it('validates new users 
    vi.mocked(listUsers).mockResolvedValue({ // vi.mocked(listUsers).moc
      total: 1, // total: 1,
      items: [{ user_id: 1, username: 'admin', display_name: '管理员', is_active: true, roles: ['admin'], warehouse_ids: [] }] // items: [{ user_id: 1, us
    }) // })
    const pinia = createPinia() // const pinia = createPini
    setActivePinia(pinia) // setActivePinia(pinia)
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { user_id: 1, username: 'admin', display_name: '管理员', roles: ['admin'] } // store.currentUser = { us
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    const wrapper = mount(UsersView, { global: { plugins: [ElementPlus, pinia] } }) // const wrapper = mount(Us
    await flushPromises() // await flushPromises()
    await wrapper.get('[data-testid="create-user"]').trigger('click') // await wrapper.get('[data
    await wrapper.get('[data-testid="save-user"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(createUser).not.toHaveBeenCalled() // expect(createUser).not.t
    expect(wrapper.get('[data-testid="user-form-error"]').text()).toContain('账户名') // expect(wrapper.get('[dat
  }) // })

  it('lets admin delete a user', async () => { // it('lets admin delete a 
    vi.mocked(listUsers).mockResolvedValue({ // vi.mocked(listUsers).moc
      total: 1, // total: 1,
      items: [{ user_id: 9, username: 'clerk', display_name: '仓管员', is_active: true, roles: ['warehouse_operator'], warehouse_ids: [1] }] // items: [{ user_id: 9, us
    }) // })
    vi.mocked(deleteUser).mockResolvedValue({ user_id: 9, deleted: true }) // vi.mocked(deleteUser).mo
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never) // vi.spyOn(ElMessageBox, '
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never) // vi.spyOn(ElMessageBox, '
    const pinia = createPinia() // const pinia = createPini
    setActivePinia(pinia) // setActivePinia(pinia)
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { user_id: 1, username: 'admin', display_name: '管理员', roles: ['admin'] } // store.currentUser = { us
    setAccessToken('jwt-token') // setAccessToken('jwt-toke
    const wrapper = mount(UsersView, { global: { plugins: [ElementPlus, pinia] } }) // const wrapper = mount(Us
    await flushPromises() // await flushPromises()
    await wrapper.get('[data-testid="delete-user-9"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(deleteUser).toHaveBeenCalledWith(9) // expect(deleteUser).toHav
  }) // })

  it('renders wechat-style bubbles and markdown tables', async () => { // it('renders wechat-style
    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [{ session_id: 4, title: '制表会话', created_at: null }] // items: [{ session_id: 4,
    }) // })
    vi.mocked(listAgentMessages).mockResolvedValue({ // vi.mocked(listAgentMessa
      items: [ // items: [
        { message_id: 1, session_id: 4, role: 'user', content: '把库存制成表格', tool_calls: [], draft: null }, // { message_id: 1, session
        { // {
          message_id: 2, // message_id: 2,
          session_id: 4, // session_id: 4,
          role: 'assistant', // role: 'assistant',
          content: '库存如下：\n| SKU | 可用 |\n| --- | --- |\n| SKU-1 | 4 |', // content: '库存如下：\n| SKU |
          tool_calls: [{ name: 'format_table' }], // tool_calls: [{ name: 'fo
          draft: null // draft: null
        } // }
      ] // ]
    }) // })
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await flushPromises() // await flushPromises()
    expect(wrapper.find('.wechat-row--mine').exists()).toBe(true) // expect(wrapper.find('.we
    expect(wrapper.find('.wechat-row--theirs').exists()).toBe(true) // expect(wrapper.find('.we
    expect(wrapper.get('[data-testid="chat-table"]').text()).toContain('SKU-1') // expect(wrapper.get('[dat
    expect(wrapper.get('[data-testid="chat-table"]').text()).toContain('4') // expect(wrapper.get('[dat
  }) // })

  it('sends assistant questions through the controlled tool API', async () => { // it('sends assistant ques
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await wrapper.get('[data-testid="new-session"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    const textarea = wrapper.find('textarea') // const textarea = wrapper
    await textarea.setValue('查询 SKU-1 的可用库存') // await textarea.setValue(
    await wrapper.get('[data-testid="send-question"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(sendAgentMessage).toHaveBeenCalledWith(3, '查询 SKU-1 的可用库存') // expect(sendAgentMessage)
    expect(wrapper.text()).toContain('LangGraph 多智能体') // expect(wrapper.text()).t
  }) // })

  it('clears the current conversation without creating another session', async () => { // it('clears the current c
    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [{ session_id: 4, title: '查询 SKU-1 的可用库存', created_at: null }] // items: [{ session_id: 4,
    }) // })
    vi.mocked(listAgentMessages).mockResolvedValue({ // vi.mocked(listAgentMessa
      items: [ // items: [
        { message_id: 1, session_id: 4, role: 'user', content: '查询 SKU-1 的可用库存', tool_calls: [], draft: null }, // { message_id: 1, session
        { message_id: 2, session_id: 4, role: 'assistant', content: '查询到库存', tool_calls: [], draft: null } // { message_id: 2, session
      ] // ]
    }) // })
    vi.mocked(clearAgentSession).mockResolvedValue({ session_id: 4, title: '新会话', created_at: null }) // vi.mocked(clearAgentSess
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await flushPromises() // await flushPromises()
    expect(wrapper.text()).toContain('查询到库存') // expect(wrapper.text()).t
    await wrapper.get('[data-testid="clear-session"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(clearAgentSession).toHaveBeenCalledWith(4) // expect(clearAgentSession
    expect(createAgentSession).not.toHaveBeenCalled() // expect(createAgentSessio
    expect(wrapper.text()).not.toContain('查询到库存') // expect(wrapper.text()).n
    expect(wrapper.text()).toContain('开始提问') // expect(wrapper.text()).t
  }) // })

  it('deletes a session from the list and switches to the remaining one', async () => { // it('deletes a session fr
    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [ // items: [
        { session_id: 4, title: '要删除的会话', created_at: null }, // { session_id: 4, title: 
        { session_id: 5, title: '保留会话', created_at: null } // { session_id: 5, title: 
      ] // ]
    }) // })
    vi.mocked(listAgentMessages).mockImplementation(async (sessionId: number) => ({ // vi.mocked(listAgentMessa
      items: // items:
        sessionId === 4 // sessionId === 4
          ? [{ message_id: 1, session_id: 4, role: 'user', content: '旧问题', tool_calls: [], draft: null }] // ? [{ message_id: 1, sess
          : [{ message_id: 2, session_id: 5, role: 'assistant', content: '保留回复', tool_calls: [], draft: null }] // : [{ message_id: 2, sess
    })) // }))
    vi.mocked(deleteAgentSession).mockResolvedValue({ session_id: 4, deleted: true }) // vi.mocked(deleteAgentSes
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await flushPromises() // await flushPromises()
    expect(wrapper.text()).toContain('要删除的会话') // expect(wrapper.text()).t
    await wrapper.get('[data-testid="delete-session-4"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(deleteAgentSession).toHaveBeenCalledWith(4) // expect(deleteAgentSessio
    expect(wrapper.text()).not.toContain('要删除的会话') // expect(wrapper.text()).n
    expect(wrapper.text()).toContain('保留会话') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('保留回复') // expect(wrapper.text()).t
  }) // })

  it('removes a session from the list even if it was already deleted', async () => { // it('removes a session fr
    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [{ session_id: 4, title: '已删除会话', created_at: null }] // items: [{ session_id: 4,
    }) // })
    vi.mocked(deleteAgentSession).mockRejectedValue(Object.assign(new ApiError('会话不存在', 404, 'NOT_FOUND'), { status: 404, code: 'NOT_FOUND' })) // vi.mocked(deleteAgentSes
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await flushPromises() // await flushPromises()
    await wrapper.get('[data-testid="delete-session-4"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(deleteAgentSession).toHaveBeenCalledTimes(1) // expect(deleteAgentSessio
    expect(wrapper.text()).not.toContain('已删除会话') // expect(wrapper.text()).n
    expect(wrapper.text()).toContain('暂无会话') // expect(wrapper.text()).t
  }) // })

  it('shows DeepSeek in the engine tag when runtime reports it', async () => { // it('shows DeepSeek in th
    vi.mocked(getSystemRuntime).mockResolvedValue({ // vi.mocked(getSystemRunti
      cache_backend: 'memory', // cache_backend: 'memory',
      graph_engine: 'langgraph', // graph_engine: 'langgraph
      llm_provider: 'deepseek', // llm_provider: 'deepseek'
      inventory_source: 'mysql' // inventory_source: 'mysql
    }) // })
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    expect(wrapper.get('[data-testid="graph-engine-tag"]').text()).toContain('DeepSeek') // expect(wrapper.get('[dat
    expect(wrapper.text()).toContain('LangGraph 多智能体') // expect(wrapper.text()).t
  }) // })

  it('loads previous assistant messages when switching sessions', async () => { // it('loads previous assis
    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [{ session_id: 4, title: '历史会话', created_at: null }] // items: [{ session_id: 4,
    }) // })
    vi.mocked(listAgentMessages).mockResolvedValue({ // vi.mocked(listAgentMessa
      items: [ // items: [
        { message_id: 1, session_id: 4, role: 'user', content: '生成入库单草稿 SKU-1 库位 A-01 数量 2', tool_calls: [], draft: null }, // { message_id: 1, session
        { // {
          message_id: 2, // message_id: 2,
          session_id: 4, // session_id: 4,
          role: 'assistant', // role: 'assistant',
          content: '已生成入库单草稿', // content: '已生成入库单草稿',
          tool_calls: [{ name: 'create_inbound_draft' }], // tool_calls: [{ name: 'cr
          draft: { type: 'inbound', items: [{ sku_code: 'SKU-1', location_code: 'A-01', quantity: 2 }] } // draft: { type: 'inbound'
        } // }
      ] // ]
    }) // })
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await flushPromises() // await flushPromises()
    expect(listAgentMessages).toHaveBeenCalledWith(4) // expect(listAgentMessages
    expect(wrapper.text()).toContain('已生成入库单草稿') // expect(wrapper.text()).t
    expect(wrapper.get('[data-testid="apply-draft"]').text()).toContain('带入单据') // expect(wrapper.get('[dat
  }) // })

  it('routes counting drafts to the counting page', async () => { // it('routes counting draf
    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [{ session_id: 4, title: '盘点草稿', created_at: null }] // items: [{ session_id: 4,
    }) // })
    vi.mocked(listAgentMessages).mockResolvedValue({ // vi.mocked(listAgentMessa
      items: [ // items: [
        { // {
          message_id: 2, // message_id: 2,
          session_id: 4, // session_id: 4,
          role: 'assistant', // role: 'assistant',
          content: '已生成盘点草稿', // content: '已生成盘点草稿',
          tool_calls: [{ name: 'create_counting_draft' }], // tool_calls: [{ name: 'cr
          draft: { type: 'counting', items: [{ sku_code: 'SKU-1' }] } // draft: { type: 'counting
        } // }
      ] // ]
    }) // })
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    await flushPromises() // await flushPromises()
    const push = vi.spyOn(router, 'push') // const push = vi.spyOn(ro
    await wrapper.get('[data-testid="apply-draft"]').trigger('click') // await wrapper.get('[data
    await flushPromises() // await flushPromises()
    expect(push).toHaveBeenCalledWith('/counting') // expect(push).toHaveBeenC
  }) // })

  it('reloads assistant sessions when the logged-in user changes', async () => { // it('reloads assistant se
    vi.mocked(listAgentSessions).mockResolvedValueOnce({ // vi.mocked(listAgentSessi
      items: [{ session_id: 4, title: '管理员会话', created_at: null }] // items: [{ session_id: 4,
    }) // })
    vi.mocked(listAgentMessages).mockResolvedValueOnce({ // vi.mocked(listAgentMessa
      items: [{ message_id: 1, session_id: 4, role: 'user', content: '管理员问题', tool_calls: [], draft: null }] // items: [{ message_id: 1,
    }) // })
    const wrapper = await mountPage('/ai-workbench', ['admin']) // const wrapper = await mo
    expect(wrapper.text()).toContain('管理员会话') // expect(wrapper.text()).t
    expect(wrapper.text()).toContain('管理员问题') // expect(wrapper.text()).t

    vi.mocked(listAgentSessions).mockResolvedValue({ // vi.mocked(listAgentSessi
      items: [{ session_id: 8, title: '操作员会话', created_at: null }] // items: [{ session_id: 8,
    }) // })
    vi.mocked(listAgentMessages).mockResolvedValue({ // vi.mocked(listAgentMessa
      items: [{ message_id: 2, session_id: 8, role: 'user', content: '操作员问题', tool_calls: [], draft: null }] // items: [{ message_id: 2,
    }) // })
    useAppStore().currentUser = { // useAppStore().currentUse
      user_id: 2, // user_id: 2,
      username: 'operator', // username: 'operator',
      display_name: '操作员', // display_name: '操作员',
      roles: ['warehouse_operator'] // roles: ['warehouse_opera
    } // }
    await flushPromises() // await flushPromises()
    await flushPromises() // await flushPromises()
    expect(wrapper.text()).toContain('操作员会话') // expect(wrapper.text()).t
    expect(wrapper.text()).not.toContain('管理员会话') // expect(wrapper.text()).n
    expect(wrapper.text()).toContain('操作员问题') // expect(wrapper.text()).t
    expect(wrapper.text()).not.toContain('管理员问题') // expect(wrapper.text()).n
  }) // })

  it('loads ABC and turnover reports', async () => { // it('loads ABC and turnov
    const wrapper = await mountPage('/reports', ['admin']) // const wrapper = await mo
    expect(wrapper.find('[data-testid="reports-page"]').exists()).toBe(true) // expect(wrapper.find('[da
    expect(wrapper.text()).toContain('SKU-1') // expect(wrapper.text()).t
    expect(getAbcReport).toHaveBeenCalled() // expect(getAbcReport).toH
    expect(getTurnoverReport).toHaveBeenCalled() // expect(getTurnoverReport
    expect(getDailyReport).toHaveBeenCalled() // expect(getDailyReport).t
    expect(getPickingEfficiency).toHaveBeenCalled() // expect(getPickingEfficie
  }) // })
}) // })
