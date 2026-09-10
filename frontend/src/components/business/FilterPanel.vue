<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ filters: string[]; modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; search: []; reset: [] }>()

const keyword = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
})
</script>

<template>
  <div class="filter-panel">
    <div class="filter-field">
      <label>{{ filters[0] ?? '关键字' }}</label>
      <el-input v-model="keyword" :placeholder="`请输入${filters[0] ?? '关键字'}`" clearable @keyup.enter="emit('search')" />
    </div>
    <div class="filter-actions">
      <el-button type="primary" @click="emit('search')">查询</el-button>
      <el-button @click="emit('reset')">重置</el-button>
    </div>
  </div>
</template>

<style scoped>
.filter-panel { display: flex; align-items: end; flex-wrap: wrap; gap: 14px; padding: 16px; background: #fbfcff; border-bottom: 1px solid var(--line); }
.filter-field { min-width: 180px; flex: 1; max-width: 245px; }
label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 7px; }
.filter-actions { display: flex; gap: 8px; }
</style>
