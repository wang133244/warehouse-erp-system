<!-- 看板统计卡。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入计算属性，用于把空值显示成占位符。
import { computed } from 'vue' // import { computed } 

// 统计卡文案、数值、提示与强调色。
const props = defineProps<{ label: string; value?: number | string; hint?: string; accent?: string }>() // const props = define
// 无数值时显示 --，避免空白。
const displayValue = computed(() => props.value ?? '--') // const displayValue =
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 统计卡容器，强调色通过 CSS 变量传入。 -->
  <div class="stat-card" :style="{ '--accent': accent || 'var(--brand)' }"> <!-- <div class="stat-car -->
    <!-- 顶部标签与装饰图标。 -->
    <div class="stat-top"><span>{{ label }}</span><span class="stat-icon">◈</span></div> <!-- <div class="stat-top -->
    <!-- 主数值，空值已替换为 --。 -->
    <div class="stat-value">{{ displayValue }}</div> <!-- <div class="stat-val -->
    <!-- 底部提示，缺省时显示等待接入。 -->
    <div class="stat-hint">{{ hint || '等待接口接入' }}</div> <!-- <div class="stat-hin -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 白底描边卡片，左侧强调条通过伪元素绘制。 */
.stat-card { position: relative; padding: 18px 20px; border: 1px solid var(--line); border-radius: 14px; background: #fff; overflow: hidden; } /* .stat-card { positio */
/* 左侧 4px 强调色竖条。 */
.stat-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--accent); } /* .stat-card::before { */
/* 顶部标签行左右排布。 */
.stat-top { display: flex; justify-content: space-between; color: var(--muted); font-size: 13px; } /* .stat-top { display: */
/* 装饰图标使用强调色。 */
.stat-icon { color: var(--accent); font-size: 18px; } /* .stat-icon { color:  */
/* 大号数值，未接入时偏灰。 */
.stat-value { font-size: 29px; font-weight: 800; margin: 15px 0 7px; color: #98a2b3; letter-spacing: .05em; } /* .stat-value { font-s */
/* 底部提示小号灰色。 */
.stat-hint { color: #a7afbd; font-size: 12px; } /* .stat-hint { color:  */
</style> <!-- 结束 style -->
