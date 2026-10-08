<!-- 登录后壳：侧栏、顶栏搜索/预警、内容区。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入计算属性与引用。
import { computed, ref } from 'vue' // import { computed, r
// 引入路由出口、当前路由与路由实例。
import { RouterView, useRoute, useRouter } from 'vue-router' // import { RouterView,
// 引入顶栏图标。
import { ArrowLeft, Bell, Expand, Fold, Search, Setting } from '@element-plus/icons-vue' // import { ArrowLeft, 
// 非管理员点设置时的提示。
import { ElMessage } from 'element-plus' // import { ElMessage }
// 面包屑、页面配置与按角色可见菜单。
import { getBreadcrumbItems, pageConfigs, visibleMenuGroupsFor } from '../config/pages' // import { getBreadcru
// 全局应用状态（用户、侧栏折叠）。
import { useAppStore } from '../stores/app' // import { useAppStore

// 当前路由、路由实例与 Pinia 应用状态。
const route = useRoute(); const router = useRouter(); const app = useAppStore() // const route = useRou
// 顶栏全局搜索关键字。
const searchKeyword = ref('') // const searchKeyword 
// 未知路径时回落到工作台首页。
const activePath = computed(() => pageConfigs[route.path] ? route.path : '/dashboard') // const activePath = c
// 当前页配置。
const current = computed(() => pageConfigs[activePath.value]) // const current = comp
// 当前路径对应的面包屑。
const breadcrumbs = computed(() => getBreadcrumbItems(route.path)) // const breadcrumbs = 
// 按角色过滤后的侧栏菜单组。
const menuGroups = computed(() => visibleMenuGroupsFor(app.currentUser?.roles ?? [])) // const menuGroups = c
// 侧栏高亮项：优先模块面包屑，总览页落到 /overview。
const activeMenuPath = computed(() => { // const activeMenuPath
  // 跳过首页项，找带 path 的模块级面包屑。
  const moduleBreadcrumb = breadcrumbs.value.find((item, index) => index > 0 && item.path) // const moduleBreadcru
  // 有模块路径用它；总览落到 /overview；否则用当前页路径。
  return moduleBreadcrumb?.path ?? (route.path === '/overview' || current.value.section === '运营总览' ? '/overview' : activePath.value) // return moduleBreadcr
}) // 结束调用
// 点击菜单跳转。
const navigate = (path: string) => router.push(path) // const navigate = (pa
// 顶栏显示名：优先用户名。
const displayName = computed(() => app.currentUser?.username ?? app.currentUser?.display_name ?? '仓库用户') // const displayName = 
// 角色文案，多个用斜杠拼接。
const roleText = computed(() => app.currentUser?.roles.join(' / ') || '已认证') // const roleText = com
// 头像取显示名首字。
const userInitial = computed(() => displayName.value.slice(0, 1)) // const userInitial = 
// 顶栏搜索：跳库存页并带 keyword。
const runGlobalSearch = () => { // const runGlobalSearc
  // 去掉首尾空白。
  const keyword = searchKeyword.value.trim() // const keyword = sear
  // 有关键字则写入查询参数。
  router.push({ path: '/inventory', query: keyword ? { keyword } : {} }) // router.push({ path: 
} // 结束代码块
// 打开预警页。
const openAlerts = () => router.push('/alerts') // const openAlerts = (
// 管理员进用户页，其他人只提示。
const openSettings = () => { // const openSettings =
  // 仅 admin 可维护账号。
  if ((app.currentUser?.roles ?? []).includes('admin')) { // if ((app.currentUser
    // 跳用户管理。
    router.push('/users') // router.push('/users'
    // 结束。
    return // return
  } // 结束代码块
  // 非管理员提示。
  ElMessage.info('账号和权限由系统管理员维护') // ElMessage.info('账号和权
} // 结束代码块
// 退出登录后回登录页。
const logout = async () => { // const logout = async
  // 清 token 与用户态。
  await app.logout() // await app.logout()
  // 跳登录。
  router.push('/login') // router.push('/login'
} // 结束代码块
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 外壳：侧栏折叠时加 collapsed。 -->
  <div class="app-shell" :class="{ collapsed: app.sidebarCollapsed }"> <!-- <div class="app-shel -->
    <!-- 侧栏：品牌、菜单组、底部 FastAPI 状态。 -->
    <aside class="sidebar"><div class="brand"><div class="brand-icon">MS</div><div v-show="!app.sidebarCollapsed" class="brand-copy"><strong>智能 ERP</strong><span>仓储管理系统</span></div></div><nav class="menu"><div v-for="group in menuGroups" :key="group.label" class="menu-group"><button v-for="item in group.items" :key="item.path" class="menu-item" :class="{ active: activeMenuPath === item.path }" :title="item.label" @click="navigate(item.path)"><span class="menu-icon">{{ item.icon }}</span><span v-show="!app.sidebarCollapsed">{{ item.label }}</span></button></div></nav><div class="sidebar-bottom"><div v-show="!app.sidebarCollapsed" class="connection online"><span /> FastAPI 已接入</div></div></aside> <!-- <aside class="sideba -->
    <!-- 主列：顶栏（折叠、面包屑、搜索、预警、设置、用户、退出）与路由出口。 -->
    <section class="main-column"><header class="topbar"><div class="topbar-left"><el-button text class="collapse-button" @click="app.toggleSidebar"><el-icon><component :is="app.sidebarCollapsed ? Expand : Fold" /></el-icon></el-button><nav class="breadcrumb" aria-label="页面路径"><template v-for="(item, index) in breadcrumbs" :key="item.label"><i v-if="index > 0">/</i><RouterLink v-if="item.path" :to="item.path" class="breadcrumb-link">{{ item.label }}</RouterLink><b v-else :aria-current="item.current ? 'page' : undefined">{{ item.label }}</b></template></nav></div><div class="topbar-right"><div class="global-search"><el-icon><Search /></el-icon><input v-model="searchKeyword" data-testid="global-search" placeholder="搜索库存 SKU / 库位" @keyup.enter="runGlobalSearch" /></div><el-button circle text data-testid="topbar-alerts" @click="openAlerts"><el-icon><Bell /></el-icon></el-button><el-button circle text data-testid="topbar-settings" @click="openSettings"><el-icon><Setting /></el-icon></el-button><div class="user"><div class="avatar">{{ userInitial }}</div><div class="user-name"><strong>{{ displayName }}</strong><span>{{ roleText }}</span></div></div><el-button text title="退出登录" @click="logout"><el-icon><ArrowLeft /></el-icon></el-button></div></header><RouterView /></section> <!-- <section class="main -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 在线状态点使用成功绿。 */
.connection.online span { background: var(--success); } /* .connection.online s */
/* 外壳网格、侧栏品牌菜单、顶栏搜索用户与窄屏适配。 */
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 252px minmax(0, 1fr); background: var(--canvas); transition: grid-template-columns .2s ease; }.app-shell.collapsed { grid-template-columns: 72px minmax(0, 1fr); }.sidebar { background: #101c33; color: #bac5d9; min-height: 100vh; display: flex; flex-direction: column; overflow: hidden; }.brand { height: 76px; display: flex; align-items: center; gap: 11px; padding: 0 18px; border-bottom: 1px solid rgba(255,255,255,.08); color: white; white-space: nowrap; }.brand-icon { flex: 0 0 37px; height: 37px; border-radius: 10px; display: grid; place-items: center; background: linear-gradient(135deg,#4b91ff,#205ed8); font-weight: 800; font-size: 12px; letter-spacing: .05em; }.brand-copy { display: grid; gap: 3px; }.brand-copy strong { font-size: 15px; }.brand-copy span { font-size: 11px; color: #7f92b4; }.menu { padding: 14px 10px 25px; overflow-y: auto; flex: 1; }.menu-group { margin-bottom: 19px; }.menu-item { width: 100%; height: 38px; display: flex; align-items: center; gap: 11px; border: 0; padding: 0 11px; background: transparent; color: #bdc9dc; cursor: pointer; font-size: 13px; border-radius: 7px; text-align: left; white-space: nowrap; transition: .18s; }.menu-item:hover { background: #18294a; color: #fff; }.menu-item.active { background: linear-gradient(90deg,#275fcb,#214a9a); color: white; box-shadow: 0 4px 12px rgba(5,25,70,.3); }.menu-icon { flex: 0 0 17px; text-align: center; font-size: 17px; }.collapsed .brand, .collapsed .menu-item { justify-content: center; padding-left: 0; padding-right: 0; }.sidebar-bottom { padding: 14px; border-top: 1px solid rgba(255,255,255,.08); }.connection { display: flex; align-items: center; gap: 7px; font-size: 11px; white-space: nowrap; color: #95a4be; }.connection span { width: 7px; height: 7px; border-radius: 50%; background: var(--warning); }.main-column { min-width: 0; }.topbar { height: 76px; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; background: #fff; border-bottom: 1px solid var(--line); gap: 15px; }.topbar-left, .topbar-right { display: flex; align-items: center; gap: 17px; }.collapse-button { font-size: 19px; color: #566178; }.breadcrumb { color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 9px; white-space: nowrap; }.breadcrumb i { font-style: normal; color: #c2c9d4; }.breadcrumb-link { color: #53617a; text-decoration: none; font-weight: 500; }.breadcrumb-link:hover { color: var(--brand); }.breadcrumb b { color: var(--ink); font-weight: 700; }.global-search { min-width: 235px; height: 34px; border: 1px solid var(--line); border-radius: 7px; color: #a2abb9; display: flex; align-items: center; gap: 7px; padding: 0 10px; font-size: 12px; }.global-search input { border: 0; outline: none; width: 100%; color: var(--ink); background: transparent; font-size: 12px; }.user { display: flex; align-items: center; gap: 8px; }.avatar { width: 33px; height: 33px; border-radius: 50%; display: grid; place-items: center; color: var(--brand); background: #e9f0ff; font-weight: 700; font-size: 13px; }.user-name { display: grid; gap: 1px; font-size: 12px; white-space: nowrap; }.user-name strong { font-size: 12px; }.user-name span { color: var(--muted); font-size: 10px; } /* .app-shell { min-hei */
/* 窄屏强制折叠侧栏并隐藏搜索与用户名。 */
@media (max-width: 900px) { .app-shell { grid-template-columns: 72px minmax(0,1fr); }.brand, .menu-item { justify-content: center; padding-left: 0; padding-right: 0; }.brand-copy, .connection { display: none; }.global-search { display: none; }.topbar { padding: 0 14px; }.breadcrumb { max-width: 52vw; overflow-x: auto; scrollbar-width: none; }.breadcrumb::-webkit-scrollbar { display: none; }.user-name { display: none; } } /* @media (max-width: 9 */
</style> <!-- 结束 style -->
