<!-- 7 日入出库简易柱状图，无第三方图表库。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 图表标题与数据点（标签 + 数值）。
defineProps<{ // 声明组件入参类型
  // 图表标题，如「近 7 日入库单数」。
  title: string // title: string
  // 柱状图数据点列表。
  points: { label: string; value: number }[] // points: { label: str
}>() // 结束类型实参调用
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 简易柱状图外层。 -->
  <div class="chart"> <!-- <div class="chart"> -->
    <!-- 图表标题。 -->
    <div class="chart-title">{{ title }}</div> <!-- <div class="chart-ti -->
    <!-- 有数据时渲染柱列。 -->
    <div v-if="points.length" class="bars"> <!-- <div v-if="points.le -->
      <!-- 每个数据点一列：柱高、日期、数值。 -->
      <div v-for="point in points" :key="point.label" class="bar-col"> <!-- <div v-for="point in -->
        <!-- 按最大值归一化柱高，最小 8px 以免看不见。 -->
        <div class="bar" :style="{ height: `${Math.max(8, Math.round((point.value / Math.max(1, ...points.map((item) => item.value))) * 140))}px` }" /> <!-- <div class="bar" :st -->
        <!-- 只显示标签末 5 位，通常是月-日。 -->
        <span>{{ point.label.slice(-5) }}</span> <!-- <span>{{ point.label -->
        <!-- 柱底数值。 -->
        <b>{{ point.value }}</b> <!-- <b>{{ point.value }} -->
      </div> <!-- 结束 div -->
    </div> <!-- 结束 div -->
    <!-- 无数据时的占位文案。 -->
    <div v-else class="empty">暂无作业趋势</div> <!-- <div v-else class="e -->
  </div> <!-- 结束 div -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 图表最小高度，避免布局塌陷。 */
.chart { min-height: 220px; } /* .chart { min-height: */
/* 标题加粗并与柱区留白。 */
.chart-title { font-weight: 700; margin-bottom: 12px; } /* .chart-title { font- */
/* 柱列底部对齐的横向 flex。 */
.bars { display: flex; align-items: end; gap: 10px; height: 180px; } /* .bars { display: fle */
/* 单列居中显示日期与数值。 */
.bar-col { flex: 1; display: grid; justify-items: center; gap: 6px; color: var(--muted); font-size: 11px; } /* .bar-col { flex: 1;  */
/* 蓝色渐变圆角柱。 */
.bar { width: 100%; max-width: 28px; border-radius: 8px 8px 0 0; background: linear-gradient(180deg, #4b91ff, #205ed8); } /* .bar { width: 100%;  */
/* 空数据占位与柱区同高并居中。 */
.empty { height: 180px; display: grid; place-items: center; color: var(--muted); } /* .empty { height: 180 */
</style> <!-- 结束 style -->
