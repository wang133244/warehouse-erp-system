/** 路由表与守卫：无 token 去登录，无菜单权限去看板。 */
import { createRouter, createWebHistory } from 'vue-router' // 引入 Vue Router 工厂
import AppShell from '../layouts/AppShell.vue' // 引入登录后外壳布局
import { canAccessPath } from '../config/pages' // 引入前端路径权限判断
import { useAppStore } from '../stores/app' // 引入登录态仓库

const router = createRouter({ // 创建路由实例
  history: createWebHistory(), // 使用 HTML5 History 模式
  routes: [ // 路由表开始
    { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } }, // 公开登录页
    { // 业务壳路由
      path: '/', // 根路径挂载外壳
      component: AppShell, // 使用 AppShell 作为父布局
      children: [ // 子路由列表
        { path: '', redirect: '/dashboard' }, // 空路径重定向到看板
        { path: 'counting', component: () => import('../views/StockCountView.vue') }, // 盘点页
        { path: 'transfer', component: () => import('../views/TransferView.vue') }, // 调拨页
        { path: 'approvals', component: () => import('../views/ApprovalView.vue') }, // 审批页
        { path: 'receiving', component: () => import('../views/ReceivingView.vue') }, // 收货页
        { path: 'outbound-review', component: () => import('../views/OutboundReviewView.vue') }, // 出库复核页
        { path: 'ai-workbench', component: () => import('../views/AssistantView.vue') }, // AI 工作台
        { path: 'reports', component: () => import('../views/ReportsView.vue') }, // 报表页
        { path: 'users', component: () => import('../views/UsersView.vue') }, // 用户管理页
        { path: 'imports/:batchId', component: () => import('../views/ImportDetailView.vue') }, // 导入批次详情
        { path: ':pathMatch(.*)*', component: () => import('../views/WorkspaceView.vue') } // 其余路径走通用工作台
      ] // 结束 children
    } // 结束壳路由
  ] // 结束 routes
}) // 结束 createRouter

export default router // 默认导出路由实例

router.beforeEach(async (to) => { // 全局前置守卫
  const app = useAppStore() // 读取登录态

  if (app.token && !app.currentUser) { // 有令牌但还没有用户信息
    const sessionValid = await app.restoreSession() // 尝试恢复会话
    if (!sessionValid) { // 会话无效
      return { path: '/login', query: { redirect: to.fullPath } } // 带回跳地址去登录
    } // 结束会话无效分支
  } // 结束恢复会话分支

  if (to.meta.public) { // 公开路由（登录页）
    return app.token ? { path: '/dashboard' } : true // 已登录则去看板，否则放行
  } // 结束公开路由判断
  if (!app.token) { // 未登录访问受保护页
    return { path: '/login', query: { redirect: to.fullPath } } // 跳转登录并记录原路径
  } // 结束未登录判断
  // 前端藏菜单不够，后端 RBAC 仍会 403。
  if (!canAccessPath(to.path, app.currentUser?.roles ?? [])) { // 前端菜单权限不足
    return { path: '/dashboard' } // 无权限回看板
  } // 结束权限判断
  return true // 放行
}) // 结束 beforeEach
