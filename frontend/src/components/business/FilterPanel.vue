<!-- 列表筛选条。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入计算属性，把关键字做成可写的 v-model。
import { computed } from 'vue' // import { computed } 

// 筛选项标签、当前关键字。
const props = defineProps<{ filters: string[]; modelValue: string }>() // const props = define
// 向外同步关键字，以及查询 / 重置事件。
const emit = defineEmits<{ 'update:modelValue': [value: string]; search: []; reset: [] }>() // const emit = defineE

// 把 props.modelValue 包装成可双向绑定的计算属性。
const keyword = computed({ // const keyword = comp
  // 读取父组件传入的关键字。
  get: () => props.modelValue, // get: () => props.mod
  // 输入变化时回写父组件。
  set: (value: string) => emit('update:modelValue', value) // set: (value: string)
}) // 结束调用
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 筛选条容器：字段 + 操作按钮。 -->
  <div class="filter-panel"> <!-- <div class="filter-p -->
    <!-- 关键字输入字段。 -->
    <div class="filter-field"> <!-- <div class="filter-f -->
      <!-- 使用配置里的第一项作为标签，缺省为「关键字」。 -->
      <label>{{ filters[0] ?? '关键字' }}</label> <!-- <label>{{ filters[0] -->
      <!-- 关键字输入框，回车触发查询。 -->
      <el-input v-model="keyword" :placeholder="`请输入${filters[0] ?? '关键字'}`" clearable @keyup.enter="emit('search')" /> <!-- <el-input v-model="k -->
    </div> <!-- 结束 div -->
    <!-- 查询与重置按钮组。 -->
    <div class="filter-actions"> <!-- <div class="filter-a -->
      <!-- 按当前关键字查询列表。 -->
      <el-button type="primary" @click="emit('search')">查询</el-button> <!-- <el-button type="pri -->
      <!-- 清空筛选条件。 -->
      <el-button @click="emit('reset')">重置</el-button> <!-- <el-button @click="e -->
    </div> <!-- 结束 div -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 筛选条横向折行，浅底并带底部分割线。 */
.filter-panel { display: flex; align-items: end; flex-wrap: wrap; gap: 14px; padding: 16px; background: #fbfcff; border-bottom: 1px solid var(--line); } /* .filter-panel { disp */
/* 关键字字段弹性宽度并设上限。 */
.filter-field { min-width: 180px; flex: 1; max-width: 245px; } /* .filter-field { min- */
/* 字段标签小号灰色。 */
label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 7px; } /* label { display: blo */
/* 查询重置按钮横向排列。 */
.filter-actions { display: flex; gap: 8px; } /* .filter-actions { di */
</style> <!-- 结束 style -->
