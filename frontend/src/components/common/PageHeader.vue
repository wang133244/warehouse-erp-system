<!-- 页头标题与操作按钮槽。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 声明页头需要的分区名、主标题与副标题。
defineProps<{ title: string; subtitle: string; section: string }>() // defineProps<{ title:
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 页头横条：左侧文案，右侧接入状态。 -->
  <div class="page-header"> <!-- <div class="page-hea -->
    <!-- 标题区：模块眉题、主标题、说明。 -->
    <div> <!-- <div> -->
      <!-- 模块分区名，如「系统管理」。 -->
      <div class="eyebrow">{{ section }}</div> <!-- <div class="eyebrow" -->
      <!-- 当前页面主标题。 -->
      <h1>{{ title }}</h1> <!-- <h1>{{ title }}</h1> -->
      <!-- 当前页面副标题说明。 -->
      <p>{{ subtitle }}</p> <!-- <p>{{ subtitle }}</p -->
    </div> <!-- 结束 div -->
    <!-- 后端接入状态徽章。 -->
    <div class="header-status online"><span class="status-dot" /> FastAPI 已接入</div> <!-- <div class="header-s -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 页头左右排布并与下方内容留白。 */
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 22px; } /* .page-header { displ */
/* 分区眉题使用品牌色小号加粗字。 */
.eyebrow { color: var(--brand); font-size: 12px; font-weight: 700; letter-spacing: .08em; margin-bottom: 7px; } /* .eyebrow { color: va */
/* 主标题字号与字距。 */
h1 { margin: 0 0 7px; font-size: 26px; letter-spacing: -.02em; } /* h1 { margin: 0 0 7px */
/* 副标题使用次要文字色。 */
p { margin: 0; color: var(--muted); font-size: 13px; } /* p { margin: 0; color */
/* 接入状态胶囊：白底描边圆角。 */
.header-status { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; background: #fff; padding: 9px 13px; border: 1px solid var(--line); border-radius: 999px; } /* .header-status { dis */
/* 状态点默认警告色。 */
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--warning); } /* .status-dot { width: */
/* 在线时状态点改为成功绿。 */
.online .status-dot { background: var(--success); } /* .online .status-dot  */
</style> <!-- 结束 style -->
