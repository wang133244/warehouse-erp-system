<!-- 列表空状态。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 声明可选标题与说明，并给出默认空数据文案。
withDefaults(defineProps<{ title?: string; description?: string }>(), { // withDefaults(defineP
  // 默认空状态标题。
  title: '暂无数据', // title: '暂无数据',
  // 默认空状态说明，提示接口尚未接入。
  description: '后端接口尚未接入，接入真实服务后将在这里展示数据。' // description: '后端接口尚未
}) // 结束调用
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 空状态居中容器。 -->
  <div class="empty-state"> <!-- <div class="empty-st -->
    <!-- 装饰性空图标。 -->
    <div class="empty-icon">◌</div> <!-- <div class="empty-ic -->
    <!-- 空状态标题。 -->
    <div class="empty-title">{{ title }}</div> <!-- <div class="empty-ti -->
    <!-- 空状态补充说明。 -->
    <div class="empty-description">{{ description }}</div> <!-- <div class="empty-de -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 空状态占位高度并居中对齐。 */
.empty-state { min-height: 220px; display: grid; place-content: center; justify-items: center; color: var(--muted); text-align: center; padding: 30px; } /* .empty-state { min-h */
/* 圆形浅蓝底图标。 */
.empty-icon { width: 52px; height: 52px; display: grid; place-items: center; border-radius: 50%; background: #eef3ff; color: var(--brand); font-size: 28px; margin-bottom: 12px; } /* .empty-icon { width: */
/* 空标题用正文色加粗。 */
.empty-title { color: var(--ink); font-weight: 700; font-size: 16px; margin-bottom: 8px; } /* .empty-title { color */
/* 说明文字限制宽度并加大行高。 */
.empty-description { font-size: 13px; max-width: 460px; line-height: 1.7; } /* .empty-description { */
</style> <!-- 结束 style -->
