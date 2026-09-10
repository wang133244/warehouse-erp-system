import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import router from '../src/router'
import { useAppStore } from '../src/stores/app'
import { clearAccessToken, setAccessToken } from '../src/api/client'

describe('路由守卫', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    clearAccessToken()
    await router.push('/login')
    await router.isReady()
  })

  it('redirects unauthenticated visitors to the login page', async () => {
    await router.push('/products')

    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('sends authenticated users away from the login page', async () => {
    const store = useAppStore()
    store.token = 'jwt-token'
    store.currentUser = {
      user_id: 1,
      username: 'admin',
      display_name: '管理员',
      roles: ['admin']
    }
    setAccessToken('jwt-token')

    await router.push('/products')
    await router.push('/login')

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })
})
