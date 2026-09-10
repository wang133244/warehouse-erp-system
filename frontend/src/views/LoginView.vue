<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { ApiError } from '../api/client'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const router = useRouter()
const route = useRoute()
const app = useAppStore()

const submit = async () => {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await app.login(form.username.trim(), form.password)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.push(redirect)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-visual"><div class="brand-mark">MS</div><div class="visual-copy"><div class="mini-label">MEGA STAR DISTRIBUTION CENTRE</div><h1>让仓储作业<br /><span>更清晰、更可控</span></h1><p>面向真实企业仓储场景的智能 ERP / WMS 工作台。</p></div><div class="visual-footer">Vue 3 · FastAPI · MySQL · Redis · LangGraph</div></div>
<div class="login-form-wrap"><div class="login-form"><div class="form-kicker">SMART ERP · WMS</div><h2>欢迎登录</h2><p class="form-subtitle">登录智能 ERP 仓管系统</p><el-form :model="form" label-position="top" @submit.prevent="submit"><el-form-item label="账号"><el-input v-model="form.username" placeholder="请输入账号" size="large" autocomplete="username" /></el-form-item><el-form-item label="密码"><el-input v-model="form.password" type="password" show-password placeholder="请输入密码" size="large" autocomplete="current-password" @keyup.enter="submit" /></el-form-item><div class="form-options"><el-checkbox>记住账号</el-checkbox><span>需要帮助？</span></div><el-button type="primary" size="large" class="login-button" native-type="submit" :loading="loading">登录系统</el-button></el-form><div class="login-note">默认使用后端初始化的管理员账号，密码保存在 backend/.admin-password</div></div></div>
  </div>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; grid-template-columns: 45% 55%; background: #fff; }
.login-visual { position: relative; padding: 54px 7vw; display: flex; flex-direction: column; justify-content: space-between; color: #fff; overflow: hidden; background: linear-gradient(145deg, #14366f, #2368e6 68%, #5ca3ff); }
.login-visual::after { content: ''; position: absolute; width: 420px; height: 420px; right: -150px; bottom: -145px; border: 1px solid rgba(255,255,255,.25); border-radius: 50%; box-shadow: 0 0 0 36px rgba(255,255,255,.05), 0 0 0 72px rgba(255,255,255,.04); }
.brand-mark { width: 52px; height: 52px; display: grid; place-items: center; border: 1px solid rgba(255,255,255,.5); border-radius: 14px; font-weight: 800; letter-spacing: .08em; }
.visual-copy { position: relative; z-index: 1; margin-top: 12vh; }.mini-label { font-size: 11px; letter-spacing: .16em; opacity: .7; margin-bottom: 24px; }
h1 { font-size: clamp(36px, 4vw, 58px); line-height: 1.18; margin: 0; letter-spacing: -.04em; } h1 span { color: #a9d2ff; }.visual-copy p { margin-top: 25px; color: rgba(255,255,255,.72); line-height: 1.8; }.visual-footer { color: rgba(255,255,255,.55); font-size: 12px; letter-spacing: .08em; }
.login-form-wrap { display: grid; place-items: center; padding: 30px; }.login-form { width: min(390px, 100%); }.form-kicker { color: var(--brand); font-weight: 800; font-size: 12px; letter-spacing: .14em; }.login-form h2 { font-size: 32px; margin: 16px 0 8px; }.form-subtitle { color: var(--muted); margin: 0 0 30px; font-size: 14px; }.form-options { display: flex; justify-content: space-between; align-items: center; color: var(--muted); font-size: 12px; margin: -3px 0 22px; }.login-button { width: 100%; height: 46px; }.login-note { margin-top: 22px; color: #a0a9b8; background: #f7f9fc; padding: 11px; border-radius: 8px; text-align: center; font-size: 12px; }
@media (max-width: 800px) { .login-page { grid-template-columns: 1fr; }.login-visual { min-height: 270px; padding: 28px; }.visual-copy { margin-top: 35px; }.visual-copy h1 { font-size: 34px; }.visual-footer { display: none; } }
</style>
