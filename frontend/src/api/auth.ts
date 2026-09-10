import { request } from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface CurrentUser {
  user_id: number
  username: string
  display_name: string
  roles: string[]
}

export function login(username: string, password: string) {
  return request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: { username, password },
    skipAuth: true
  })
}

export function fetchCurrentUser() {
  return request<CurrentUser>('/api/v1/auth/me')
}

export async function logout() {
  await request<null>('/api/v1/auth/logout', { method: 'POST' })
}
