<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ label: string; value?: number | string; hint?: string; accent?: string }>()
const displayValue = computed(() => props.value ?? '--')
</script>

<template>
  <div class="stat-card" :style="{ '--accent': accent || 'var(--brand)' }">
    <div class="stat-top"><span>{{ label }}</span><span class="stat-icon">◈</span></div>
    <div class="stat-value">{{ displayValue }}</div>
    <div class="stat-hint">{{ hint || '等待接口接入' }}</div>
  </div>
</template>

<style scoped>
.stat-card { position: relative; padding: 18px 20px; border: 1px solid var(--line); border-radius: 14px; background: #fff; overflow: hidden; }
.stat-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--accent); }
.stat-top { display: flex; justify-content: space-between; color: var(--muted); font-size: 13px; }
.stat-icon { color: var(--accent); font-size: 18px; }
.stat-value { font-size: 29px; font-weight: 800; margin: 15px 0 7px; color: #98a2b3; letter-spacing: .05em; }
.stat-hint { color: #a7afbd; font-size: 12px; }
</style>
