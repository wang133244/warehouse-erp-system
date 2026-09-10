<script setup lang="ts">
defineProps<{ title: string; subtitle: string; section: string }>()
</script>

<template>
  <div class="page-header">
    <div>
      <div class="eyebrow">{{ section }}</div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>
    <div class="header-status online"><span class="status-dot" /> FastAPI 已接入</div>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 22px; }
.eyebrow { color: var(--brand); font-size: 12px; font-weight: 700; letter-spacing: .08em; margin-bottom: 7px; }
h1 { margin: 0 0 7px; font-size: 26px; letter-spacing: -.02em; }
p { margin: 0; color: var(--muted); font-size: 13px; }
.header-status { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; background: #fff; padding: 9px 13px; border: 1px solid var(--line); border-radius: 999px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--warning); }
.online .status-dot { background: var(--success); }
</style>
