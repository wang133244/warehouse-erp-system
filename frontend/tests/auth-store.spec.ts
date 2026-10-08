/** 登录态与权限。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest' // import { afterEach, befo
import { createPinia, setActivePinia } from 'pinia' // import { createPinia, se
import { useAppStore } from '../src/stores/app' // import { useAppStore } f
import { clearAccessToken } from '../src/models/client' // import { clearAccessToke

const jsonResponse = (body: unknown, status = 200) => // const jsonResponse = (bo
  new Response(JSON.stringify(body), { // new Response(JSON.string
    status, // status,
    headers: { 'content-type': 'application/json' } // headers: { 'content-type
  }) // })

describe('认证状态', () => { // describe('认证状态', () => {
  let fetchMock: ReturnType<typeof vi.fn> // let fetchMock: ReturnTyp

  beforeEach(() => { // beforeEach(() => {
    setActivePinia(createPinia()) // setActivePinia(createPin
    clearAccessToken() // clearAccessToken()
    fetchMock = vi.fn() // fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock) // vi.stubGlobal('fetch', f
  }) // })

  afterEach(() => { // afterEach(() => {
    vi.unstubAllGlobals() // vi.unstubAllGlobals()
    clearAccessToken() // clearAccessToken()
  }) // })

  it('stores token and current user after login', async () => { // it('stores token and cur
    fetchMock // fetchMock
      .mockResolvedValueOnce(jsonResponse({ access_token: 'jwt-token', token_type: 'bearer', expires_in: 3600 })) // .mockResolvedValueOnce(j
      .mockResolvedValueOnce( // .mockResolvedValueOnce(
        jsonResponse({ // jsonResponse({
          user_id: 1, // user_id: 1,
          username: 'admin', // username: 'admin',
          display_name: '系统管理员', // display_name: '系统管理员',
          roles: ['admin'] // roles: ['admin']
        }) // })
      ) // )

    const store = useAppStore() // const store = useAppStor
    await store.login('admin', 'secret') // await store.login('admin

    expect(store.token).toBe('jwt-token') // expect(store.token).toBe
    expect(store.currentUser).toEqual({ // expect(store.currentUser
      user_id: 1, // user_id: 1,
      username: 'admin', // username: 'admin',
      display_name: '系统管理员', // display_name: '系统管理员',
      roles: ['admin'] // roles: ['admin']
    }) // })
    expect(fetchMock).toHaveBeenNthCalledWith( // expect(fetchMock).toHave
      1, // 1,
      'http://127.0.0.1:8000/api/v1/auth/login',
      expect.objectContaining({ // expect.objectContaining(
        method: 'POST', // method: 'POST',
        body: JSON.stringify({ username: 'admin', password: 'secret' }) // body: JSON.stringify({ u
      }) // })
    ) // )
  }) // })

  it('clears local auth state after logout even if the logout request fails', async () => { // it('clears local auth st
    const store = useAppStore() // const store = useAppStor
    store.token = 'jwt-token' // store.token = 'jwt-token
    store.currentUser = { user_id: 1, username: 'admin', display_name: '管理员', roles: ['admin'] } // store.currentUser = { us
    fetchMock.mockResolvedValue(new Response(null, { status: 500 })) // fetchMock.mockResolvedVa

    await store.logout() // await store.logout()

    expect(store.token).toBeNull() // expect(store.token).toBe
    expect(store.currentUser).toBeNull() // expect(store.currentUser
  }) // })
}) // })
