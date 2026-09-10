<script setup lang="ts">
withDefaults(defineProps<{ title?: string; description?: string }>(), {
  title: '暂无数据',
  description: '后端接口尚未接入，接入真实服务后将在这里展示数据。'
})
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">◌</div>
    <div class="empty-title">{{ title }}</div>
    <div class="empty-description">{{ description }}</div>
  </div>
</template>

<style scoped>
.empty-state { min-height: 220px; display: grid; place-content: center; justify-items: center; color: var(--muted); text-align: center; padding: 30px; }
.empty-icon { width: 52px; height: 52px; display: grid; place-items: center; border-radius: 50%; background: #eef3ff; color: var(--brand); font-size: 28px; margin-bottom: 12px; }
.empty-title { color: var(--ink); font-weight: 700; font-size: 16px; margin-bottom: 8px; }
.empty-description { font-size: 13px; max-width: 460px; line-height: 1.7; }
</style>
