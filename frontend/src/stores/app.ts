import { defineStore } from 'pinia'
import { clearAccessToken, getAccessToken, setAccessToken } from '../api/client'
import { fetchCurrentUser, login as loginApi, logout as logoutApi, type CurrentUser } from '../api/auth'

export const useAppStore = defineStore('app', {
  state: () => ({
    sidebarCollapsed: false,
    token: getAccessToken(),
    currentUser: null as CurrentUser | null
  }),
  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    async login(username: string, password: string) {
      const tokenResponse = await loginApi(username, password)
      this.token = tokenResponse.access_token
      setAccessToken(this.token)
      await this.fetchCurrentUser()
      return tokenResponse
    },
    async fetchCurrentUser() {
      if (!this.token) return null
      this.currentUser = await fetchCurrentUser()
      return this.currentUser
    },
    async restoreSession() {
      if (!this.token) return false
      try {
        await this.fetchCurrentUser()
        return true
      } catch (error) {
        if ((error as { status?: number }).status === 401) this.clearAuth()
        return false
      }
    },
    async logout() {
      try {
        if (this.token) await logoutApi()
      } catch {
        // JWT is stateless; a failed server notification must not trap the user locally.
      } finally {
        this.clearAuth()
      }
    },
    clearAuth() {
      this.token = null
      this.currentUser = null
      clearAccessToken()
    }
  }
})
