/** 登录态、token、助手草稿 pendingDraft。草稿由业务页 consume。 */
import { defineStore } from 'pinia' // 引入 Pinia 定义仓库
import { clearAccessToken, getAccessToken, setAccessToken } from '../models/client' // 令牌读写
import { fetchCurrentUser, login as loginApi, logout as logoutApi, type CurrentUser } from '../models/auth' // 认证 API 与用户类型

export interface OperationDraft { // 助手带到业务页的单据草稿
  type: 'inbound' | 'outbound' | string // 草稿业务类型
  items?: Array<{ // 草稿明细可选
    sku_code?: string | null // SKU 编码
    location_code?: string | null // 库位编码
    quantity?: number | null // 数量
  }> // 结束 items 元素类型
} // 结束 OperationDraft

export const useAppStore = defineStore('app', { // 定义全局 app 仓库
  state: () => ({ // 初始状态
    sidebarCollapsed: false, // 侧栏是否折叠
    token: getAccessToken(), // 从本地恢复令牌
    currentUser: null as CurrentUser | null, // 当前用户
    pendingDraft: null as OperationDraft | null // 待消费的助手草稿
  }), // 结束 state
  actions: { // 仓库动作
    toggleSidebar() { // 切换侧栏折叠
      this.sidebarCollapsed = !this.sidebarCollapsed // 取反折叠状态
    }, // 结束 toggleSidebar
    setPendingDraft(draft: OperationDraft | null) { // 写入待消费草稿
      this.pendingDraft = draft // 保存草稿
    }, // 结束 setPendingDraft
    consumePendingDraft() { // 取出并清空草稿
      const draft = this.pendingDraft // 先拿到当前草稿
      this.pendingDraft = null // 立即清空，避免重复消费
      return draft // 返回给业务页
    }, // 结束 consumePendingDraft
    async login(username: string, password: string) { // 登录并拉用户
      const tokenResponse = await loginApi(username, password) // 调登录接口
      this.token = tokenResponse.access_token // 写入内存令牌
      setAccessToken(this.token) // 持久化令牌
      await this.fetchCurrentUser() // 拉取当前用户
      return tokenResponse // 返回令牌响应
    }, // 结束 login
    async fetchCurrentUser() { // 拉取 /auth/me
      if (!this.token) return null // 无令牌则不请求
      this.currentUser = await fetchCurrentUser() // 写入当前用户
      return this.currentUser // 返回用户
    }, // 结束 fetchCurrentUser
    async restoreSession() { // 刷新页面后恢复会话
      if (!this.token) return false // 无令牌视为未登录
      try { // 尝试拉用户
        await this.fetchCurrentUser() // 校验令牌并填充用户
        return true // 会话有效
      } catch (error) { // 恢复失败
        if ((error as { status?: number }).status === 401) this.clearAuth() // 401 则清登录态
        return false // 视为无效会话
      } // 结束 catch
    }, // 结束 restoreSession
    async logout() { // 登出
      try { // 通知后端
        if (this.token) await logoutApi() // 有令牌才调登出接口
      } catch { // 后端通知失败也不卡住本地
        // JWT is stateless; a failed server notification must not trap the user locally.
      } finally { // 无论后端成败
        this.clearAuth() // 清本地登录态
      } // 结束 finally
    }, // 结束 logout
    clearAuth() { // 清空登录相关状态
      this.token = null // 清内存令牌
      this.currentUser = null // 清用户
      this.pendingDraft = null // 清草稿
      clearAccessToken() // 清本地存储令牌
    } // 结束 clearAuth
  } // 结束 actions
}) // 结束 defineStore
