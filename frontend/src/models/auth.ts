/** 登录、登出、当前用户 API。 */
import { request } from './client' // 引入统一 HTTP 请求封装

export interface TokenResponse { // 登录成功返回的令牌结构
  access_token: string // 访问令牌字符串
  token_type: string // 令牌类型，通常为 Bearer
  expires_in: number // 过期秒数
} // 结束 TokenResponse

export interface CurrentUser { // 当前登录用户信息
  user_id: number // 用户主键
  username: string // 登录账号
  display_name: string // 显示名称
  roles: string[] // 角色编码列表
} // 结束 CurrentUser

export function login(username: string, password: string) { // 调用登录接口
  return request<TokenResponse>('/api/v1/auth/login', { // POST 登录并解析令牌
    method: 'POST', // 使用 POST 方法
    body: { username, password }, // 提交账号密码
    skipAuth: true // 登录请求不带旧令牌
  }) // 结束 request 参数
} // 结束 login

export function fetchCurrentUser() { // 拉取当前用户
  return request<CurrentUser>('/api/v1/auth/me') // GET /auth/me
} // 结束 fetchCurrentUser

export async function logout() { // 登出并通知后端
  await request<null>('/api/v1/auth/logout', { method: 'POST' }) // POST 登出
} // 结束 logout
