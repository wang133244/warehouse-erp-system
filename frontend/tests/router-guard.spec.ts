/** 未登录 / 无权限跳转。 */
import { beforeEach, describe, expect, it } from 'vitest' // import { beforeEach, des
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import router from '../src/router' // import router from '../s
import { useAppStore } from '../src/stores/app' // import { useAppStore } f
import { clearAccessToken, setAccessToken } from '../src/models/client' // import { clearAccessToke

describe('路由守卫', () => { // describe('路由守卫', () => {
  beforeEach(async () => { // beforeEach(async () => {
    setActivePinia(createPinia()) // setActivePinia(createPin
    clearAccessToken() // clearAccessToken()
    await router.push('/login') // await router.push('/logi
    await router.isReady() // await router.isReady()
  }, 20_000) // }, 20_000)

  it('redirects unauthenticated visitors to the login page', async () => { // it('redirects unauthenti
    await router.push('/products') // await router.push('/prod

    expect(router.currentRoute.value.path).toBe('/login') // expect(router.currentRou
  }) // })

  it('sends authenticated users away from the login page', async () => { // it('sends authenticated 
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { // store.currentUser = {
      user_id: 1, // user_id: 1,
      username: 'admin', // username: 'admin',
      display_name: '管理员', // display_name: '管理员',
      roles: ['admin'] // roles: ['admin']
    } // }
    setAccessToken('jwt-token') // setAccessToken('jwt-toke

    await router.push('/products') // await router.push('/prod
    await router.push('/login') // await router.push('/logi

    expect(router.currentRoute.value.path).toBe('/dashboard') // expect(router.currentRou
  }) // })

  it('keeps operators out of system management routes', async () => { // it('keeps operators out 
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { // store.currentUser = {
      user_id: 2, // user_id: 2,
      username: 'clerk', // username: 'clerk',
      display_name: '仓管员', // display_name: '仓管员',
      roles: ['warehouse_operator'] // roles: ['warehouse_opera
    } // }
    setAccessToken('jwt-token') // setAccessToken('jwt-toke

    await router.push('/users') // await router.push('/user

    expect(router.currentRoute.value.path).toBe('/dashboard') // expect(router.currentRou
  }) // })

  it('keeps viewers out of write routes and opens the receiving page', async () => { // it('keeps viewers out of
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { // store.currentUser = {
      user_id: 3, // user_id: 3,
      username: 'viewer', // username: 'viewer',
      display_name: '只读', // display_name: '只读',
      roles: ['viewer'] // roles: ['viewer']
    } // }
    setAccessToken('jwt-token') // setAccessToken('jwt-toke

    await router.push('/inbounds') // await router.push('/inbo
    expect(router.currentRoute.value.path).toBe('/dashboard') // expect(router.currentRou

    store.currentUser = { // store.currentUser = {
      user_id: 2, // user_id: 2,
      username: 'clerk', // username: 'clerk',
      display_name: '仓管员', // display_name: '仓管员',
      roles: ['warehouse_operator'] // roles: ['warehouse_opera
    } // }
    await router.push('/receiving') // await router.push('/rece
    expect(router.currentRoute.value.path).toBe('/receiving') // expect(router.currentRou
  }) // })
}) // })
