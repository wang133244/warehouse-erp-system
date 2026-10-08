<!-- 登录页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入登录页控制器。
import { useLoginController } from '../controllers/loginController' // import { useLoginCon

// 从控制器取出表单、记住账号与提交。
const { // const {
  // 账号密码表单。
  form, // form,
  // 是否记住账号。
  rememberUsername, // rememberUsername,
  // 提交中。
  loading, // loading,
  // 路由实例。
  router, // router,
  // 当前路由。
  route, // route,
  // 全局应用状态。
  app, // app,
  // 提交登录。
  submit // submit
} = useLoginController() // } = useLoginControll

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 登录页左右分栏。 -->
  <div class="login-page"> <!-- <div class="login-pa -->
    <!-- 左侧品牌视觉区：标志、口号、技术栈。 -->
    <div class="login-visual"><div class="brand-mark">MS</div><div class="visual-copy"><div class="mini-label">MEGA STAR DISTRIBUTION CENTRE</div><h1>让仓储作业<br /><span>更清晰、更可控</span></h1><p>面向真实企业仓储场景的智能 ERP / WMS 工作台。</p></div><div class="visual-footer">Vue 3 · FastAPI · MySQL · Redis · LangGraph</div></div> <!-- <div class="login-vi -->
    <!-- 右侧登录表单：账号、密码、记住账号、提交。 -->
    <div class="login-form-wrap"><div class="login-form"><div class="form-kicker">SMART ERP · WMS</div><h2>欢迎登录</h2><p class="form-subtitle">登录智能 ERP 仓管系统</p><el-form :model="form" label-position="top" @submit.prevent="submit"><el-form-item label="账号"><el-input v-model="form.username" placeholder="请输入账号" size="large" autocomplete="username" /></el-form-item><el-form-item label="密码"><el-input v-model="form.password" type="password" show-password placeholder="请输入密码" size="large" autocomplete="current-password" @keyup.enter="submit" /></el-form-item><div class="form-options"><el-checkbox v-model="rememberUsername">记住账号</el-checkbox><span>需要帮助？</span></div><el-button type="primary" size="large" class="login-button" native-type="submit" :loading="loading">登录系统</el-button></el-form><div class="login-note">默认使用后端初始化的管理员账号，密码保存在 backend/.admin-password</div></div></div> <!-- <div class="login-fo -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 登录页左右 45/55 分栏全屏白底。 */
.login-page { min-height: 100vh; display: grid; grid-template-columns: 45% 55%; background: #fff; } /* .login-page { min-he */
/* 左侧渐变品牌区，纵向两端对齐。 */
.login-visual { position: relative; padding: 54px 7vw; display: flex; flex-direction: column; justify-content: space-between; color: #fff; overflow: hidden; background: linear-gradient(145deg, #14366f, #2368e6 68%, #5ca3ff); } /* .login-visual { posi */
/* 右下角装饰圆环。 */
.login-visual::after { content: ''; position: absolute; width: 420px; height: 420px; right: -150px; bottom: -145px; border: 1px solid rgba(255,255,255,.25); border-radius: 50%; box-shadow: 0 0 0 36px rgba(255,255,255,.05), 0 0 0 72px rgba(255,255,255,.04); } /* .login-visual::after */
/* 左上角 MS 品牌方标。 */
.brand-mark { width: 52px; height: 52px; display: grid; place-items: center; border: 1px solid rgba(255,255,255,.5); border-radius: 14px; font-weight: 800; letter-spacing: .08em; } /* .brand-mark { width: */
/* 口号区相对定位；迷你英文标签。 */
.visual-copy { position: relative; z-index: 1; margin-top: 12vh; }.mini-label { font-size: 11px; letter-spacing: .16em; opacity: .7; margin-bottom: 24px; } /* .visual-copy { posit */
/* 主标题、高亮副句、说明与页脚技术栈。 */
h1 { font-size: clamp(36px, 4vw, 58px); line-height: 1.18; margin: 0; letter-spacing: -.04em; } h1 span { color: #a9d2ff; }.visual-copy p { margin-top: 25px; color: rgba(255,255,255,.72); line-height: 1.8; }.visual-footer { color: rgba(255,255,255,.55); font-size: 12px; letter-spacing: .08em; } /* h1 { font-size: clam */
/* 右侧表单居中、标题、选项与登录按钮。 */
.login-form-wrap { display: grid; place-items: center; padding: 30px; }.login-form { width: min(390px, 100%); }.form-kicker { color: var(--brand); font-weight: 800; font-size: 12px; letter-spacing: .14em; }.login-form h2 { font-size: 32px; margin: 16px 0 8px; }.form-subtitle { color: var(--muted); margin: 0 0 30px; font-size: 14px; }.form-options { display: flex; justify-content: space-between; align-items: center; color: var(--muted); font-size: 12px; margin: -3px 0 22px; }.login-button { width: 100%; height: 46px; }.login-note { margin-top: 22px; color: #a0a9b8; background: #f7f9fc; padding: 11px; border-radius: 8px; text-align: center; font-size: 12px; } /* .login-form-wrap { d */
/* 窄屏改为单列并隐藏页脚技术栈。 */
@media (max-width: 800px) { .login-page { grid-template-columns: 1fr; }.login-visual { min-height: 270px; padding: 28px; }.visual-copy { margin-top: 35px; }.visual-copy h1 { font-size: 34px; }.visual-footer { display: none; } } /* @media (max-width: 8 */
</style> <!-- 结束 style -->
