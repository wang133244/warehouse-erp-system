<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Bell, Expand, Fold, Search, Setting } from '@element-plus/icons-vue'
import { getBreadcrumbItems, menuGroups, pageConfigs } from '../config/pages'
import { useAppStore } from '../stores/app'
import WorkspaceView from '../views/WorkspaceView.vue'

const route = useRoute(); const router = useRouter(); const app = useAppStore()
const activePath = computed(() => pageConfigs[route.path] ? route.path : '/dashboard')
const current = computed(() => pageConfigs[activePath.value])
const breadcrumbs = computed(() => getBreadcrumbItems(route.path))
const activeMenuPath = computed(() => {
  const moduleBreadcrumb = breadcrumbs.value.find((item, index) => index > 0 && item.path)
  return moduleBreadcrumb?.path ?? (route.path === '/overview' || current.value.section === '运营总览' ? '/overview' : activePath.value)
})
const navigate = (path: string) => router.push(path)
const displayName = computed(() => app.currentUser?.display_name ?? app.currentUser?.username ?? '仓库用户')
const roleText = computed(() => app.currentUser?.roles.join(' / ') || '已认证')
const userInitial = computed(() => displayName.value.slice(0, 1))
const logout = async () => {
  await app.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell" :class="{ collapsed: app.sidebarCollapsed }">
    <aside class="sidebar"><div class="brand"><div class="brand-icon">MS</div><div v-show="!app.sidebarCollapsed" class="brand-copy"><strong>智能 ERP</strong><span>仓储管理系统</span></div></div><nav class="menu"><div v-for="group in menuGroups" :key="group.label" class="menu-group"><button v-for="item in group.items" :key="item.path" class="menu-item" :class="{ active: activeMenuPath === item.path }" :title="item.label" @click="navigate(item.path)"><span class="menu-icon">{{ item.icon }}</span><span v-show="!app.sidebarCollapsed">{{ item.label }}</span></button></div></nav><div class="sidebar-bottom"><div v-show="!app.sidebarCollapsed" class="connection online"><span /> FastAPI 已接入</div></div></aside>
    <section class="main-column"><header class="topbar"><div class="topbar-left"><el-button text class="collapse-button" @click="app.toggleSidebar"><el-icon><component :is="app.sidebarCollapsed ? Expand : Fold" /></el-icon></el-button><nav class="breadcrumb" aria-label="页面路径"><template v-for="(item, index) in breadcrumbs" :key="item.label"><i v-if="index > 0">/</i><RouterLink v-if="item.path" :to="item.path" class="breadcrumb-link">{{ item.label }}</RouterLink><b v-else :aria-current="item.current ? 'page' : undefined">{{ item.label }}</b></template></nav></div><div class="topbar-right"><div class="global-search"><el-icon><Search /></el-icon><span>全局搜索（当前版本支持页面内查询）</span></div><el-button circle text><el-icon><Bell /></el-icon></el-button><el-button circle text><el-icon><Setting /></el-icon></el-button><div class="user"><div class="avatar">{{ userInitial }}</div><div class="user-name"><strong>{{ displayName }}</strong><span>{{ roleText }}</span></div></div><el-button text title="退出登录" @click="logout"><el-icon><ArrowLeft /></el-icon></el-button></div></header><WorkspaceView /></section>
  </div>
</template>

<style scoped>
.connection.online span { background: var(--success); }
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 252px minmax(0, 1fr); background: var(--canvas); transition: grid-template-columns .2s ease; }.app-shell.collapsed { grid-template-columns: 72px minmax(0, 1fr); }.sidebar { background: #101c33; color: #bac5d9; min-height: 100vh; display: flex; flex-direction: column; overflow: hidden; }.brand { height: 76px; display: flex; align-items: center; gap: 11px; padding: 0 18px; border-bottom: 1px solid rgba(255,255,255,.08); color: white; white-space: nowrap; }.brand-icon { flex: 0 0 37px; height: 37px; border-radius: 10px; display: grid; place-items: center; background: linear-gradient(135deg,#4b91ff,#205ed8); font-weight: 800; font-size: 12px; letter-spacing: .05em; }.brand-copy { display: grid; gap: 3px; }.brand-copy strong { font-size: 15px; }.brand-copy span { font-size: 11px; color: #7f92b4; }.menu { padding: 14px 10px 25px; overflow-y: auto; flex: 1; }.menu-group { margin-bottom: 19px; }.menu-item { width: 100%; height: 38px; display: flex; align-items: center; gap: 11px; border: 0; padding: 0 11px; background: transparent; color: #bdc9dc; cursor: pointer; font-size: 13px; border-radius: 7px; text-align: left; white-space: nowrap; transition: .18s; }.menu-item:hover { background: #18294a; color: #fff; }.menu-item.active { background: linear-gradient(90deg,#275fcb,#214a9a); color: white; box-shadow: 0 4px 12px rgba(5,25,70,.3); }.menu-icon { flex: 0 0 17px; text-align: center; font-size: 17px; }.collapsed .brand, .collapsed .menu-item { justify-content: center; padding-left: 0; padding-right: 0; }.sidebar-bottom { padding: 14px; border-top: 1px solid rgba(255,255,255,.08); }.connection { display: flex; align-items: center; gap: 7px; font-size: 11px; white-space: nowrap; color: #95a4be; }.connection span { width: 7px; height: 7px; border-radius: 50%; background: var(--warning); }.main-column { min-width: 0; }.topbar { height: 76px; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; background: #fff; border-bottom: 1px solid var(--line); gap: 15px; }.topbar-left, .topbar-right { display: flex; align-items: center; gap: 17px; }.collapse-button { font-size: 19px; color: #566178; }.breadcrumb { color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 9px; white-space: nowrap; }.breadcrumb i { font-style: normal; color: #c2c9d4; }.breadcrumb-link { color: #53617a; text-decoration: none; font-weight: 500; }.breadcrumb-link:hover { color: var(--brand); }.breadcrumb b { color: var(--ink); font-weight: 700; }.global-search { min-width: 235px; height: 34px; border: 1px solid var(--line); border-radius: 7px; color: #a2abb9; display: flex; align-items: center; gap: 7px; padding: 0 10px; font-size: 12px; }.user { display: flex; align-items: center; gap: 8px; }.avatar { width: 33px; height: 33px; border-radius: 50%; display: grid; place-items: center; color: var(--brand); background: #e9f0ff; font-weight: 700; font-size: 13px; }.user-name { display: grid; gap: 1px; font-size: 12px; white-space: nowrap; }.user-name strong { font-size: 12px; }.user-name span { color: var(--muted); font-size: 10px; }
@media (max-width: 900px) { .app-shell { grid-template-columns: 72px minmax(0,1fr); }.brand, .menu-item { justify-content: center; padding-left: 0; padding-right: 0; }.brand-copy, .connection { display: none; }.global-search { display: none; }.topbar { padding: 0 14px; }.breadcrumb { max-width: 52vw; overflow-x: auto; scrollbar-width: none; }.breadcrumb::-webkit-scrollbar { display: none; }.user-name { display: none; } }
</style>
