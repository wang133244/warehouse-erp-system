import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAppStore } from '../src/stores/app'
import { clearAccessToken } from '../src/api/client'

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' }
  })

describe('认证状态', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia(createPinia())
    clearAccessToken()
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearAccessToken()
  })

  it('stores token and current user after login', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ access_token: 'jwt-token', token_type: 'bearer', expires_in: 3600 }))
      .mockResolvedValueOnce(
        jsonResponse({
          user_id: 1,
          username: 'admin',
          display_name: '系统管理员',
          roles: ['admin']
        })
      )

    const store = useAppStore()
    await store.login('admin', 'secret')

    expect(store.token).toBe('jwt-token')
    expect(store.currentUser).toEqual({
      user_id: 1,
      username: 'admin',
      display_name: '系统管理员',
      roles: ['admin']
    })
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://127.0.0.1:8000/api/v1/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ username: 'admin', password: 'secret' })
      })
    )
  })

  it('clears local auth state after logout even if the logout request fails', async () => {
    const store = useAppStore()
    store.token = 'jwt-token'
    store.currentUser = { user_id: 1, username: 'admin', display_name: '管理员', roles: ['admin'] }
    fetchMock.mockResolvedValue(new Response(null, { status: 500 }))

    await store.logout()

    expect(store.token).toBeNull()
    expect(store.currentUser).toBeNull()
  })
})
