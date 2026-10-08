/** 记住用户名。 */
import { beforeEach, describe, expect, it, vi } from 'vitest' // import { beforeEach, des
import { flushPromises, mount } from '@vue/test-utils' // import { flushPromises, 
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import ElementPlus from 'element-plus' // import ElementPlus from 
import { createMemoryHistory, createRouter } from 'vue-router' // import { createMemoryHis
import LoginView from '../src/views/LoginView.vue' // import LoginView from '.
import { REMEMBERED_USERNAME_KEY } from '../src/controllers/loginController' // import { REMEMBERED_USER
import { useAppStore } from '../src/stores/app' // import { useAppStore } f

vi.mock('../src/models/auth', () => ({ // vi.mock('../src/models/a
  login: vi.fn(async () => ({ access_token: 'jwt', token_type: 'bearer', expires_in: 3600 })), // login: vi.fn(async () =>
  fetchCurrentUser: vi.fn(async () => ({ // fetchCurrentUser: vi.fn(
    user_id: 1, // user_id: 1,
    username: 'admin', // username: 'admin',
    display_name: '管理员', // display_name: '管理员',
    roles: ['admin'] // roles: ['admin']
  })), // })),
  logout: vi.fn() // logout: vi.fn()
})) // }))

describe('登录记住账号', () => { // describe('登录记住账号', () =>
  beforeEach(() => { // beforeEach(() => {
    window.localStorage.clear() // window.localStorage.clea
  }) // })

  it('restores remembered username into the login form', async () => { // it('restores remembered 
    window.localStorage.setItem(REMEMBERED_USERNAME_KEY, 'clerk') // window.localStorage.setI
    const pinia = createPinia() // const pinia = createPini
    setActivePinia(pinia) // setActivePinia(pinia)
    const router = createRouter({ // const router = createRou
      history: createMemoryHistory(), // history: createMemoryHis
      routes: [ // routes: [
        { path: '/login', component: LoginView }, // { path: '/login', compon
        { path: '/dashboard', component: { template: '<div />' } } // { path: '/dashboard', co
      ] // ]
    }) // })
    await router.push('/login') // await router.push('/logi
    const wrapper = mount(LoginView, { global: { plugins: [ElementPlus, pinia, router] } }) // const wrapper = mount(Lo
    await flushPromises() // await flushPromises()
    const input = wrapper.find('input') // const input = wrapper.fi
    expect((input.element as HTMLInputElement).value).toBe('clerk') // expect((input.element as
  }) // })
}) // })
