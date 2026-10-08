<!-- 报表页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入报表页控制器。
import { useReportsController } from '../controllers/reportsController' // import { useReportsC

// 从控制器取出 ABC、周转、日报周报与拣货 KPI。
const { // const {
  // 页面文案配置。
  config, // config,
  // ABC 分类原始项。
  abcItems, // abcItems,
  // 周转原始项。
  turnoverItems, // turnoverItems,
  // 日报原始项。
  dailyItems, // dailyItems,
  // 周报原始项。
  weeklyItems, // weeklyItems,
  // 拣货 KPI。
  picking, // picking,
  // 分类依据：出库或现存量。
  basis, // basis,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 筛选关键字。
  keyword, // keyword,
  // 日报天数。
  days, // days,
  // 周报周数。
  weeks, // weeks,
  // 空状态说明。
  emptyDescription, // emptyDescription,
  // 关键字是否匹配某行。
  matchesKeyword, // matchesKeyword,
  // 过滤后的 ABC 表数据。
  visibleAbc, // visibleAbc,
  // 过滤后的周转表数据。
  visibleTurnover, // visibleTurnover,
  // 过滤后的日报。
  visibleDaily, // visibleDaily,
  // 过滤后的周报。
  visibleWeekly, // visibleWeekly,
  // 加载报表。
  loadData, // loadData,
  // 刷新报表。
  refresh, // refresh,
  // 按关键字查询。
  search, // search,
  // 重置筛选。
  reset // reset
} = useReportsController() // } = useReportsContro

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 报表页主容器。 -->
  <main class="workspace-page" data-testid="reports-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 筛选卡片。 -->
    <el-card shadow="never" class="filter-card"> <!-- <el-card shadow="nev -->
      <!-- 关键字筛选条。 -->
      <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-model -->
    </el-card> <!-- 结束 el-card -->
    <!-- 刷新与时间范围工具条。 -->
    <div class="toolbar"> <!-- <div class="toolbar" -->
      <!-- 重新拉取报表。 -->
      <el-button type="primary" data-testid="refresh-reports" :loading="loading" @click="refresh">刷新报表</el-button> <!-- <el-button type="pri -->
      <!-- 日报天数。 -->
      <el-select v-model="days" style="width: 140px" @change="loadData"> <!-- <el-select v-model=" -->
        <!-- 7 天。 -->
        <el-option :value="7" label="日报 7 天" /> <!-- <el-option :value="7 -->
        <!-- 14 天。 -->
        <el-option :value="14" label="日报 14 天" /> <!-- <el-option :value="1 -->
        <!-- 31 天。 -->
        <el-option :value="31" label="日报 31 天" /> <!-- <el-option :value="3 -->
      </el-select> <!-- 结束 el-select -->
      <!-- 周报周数。 -->
      <el-select v-model="weeks" style="width: 140px" @change="loadData"> <!-- <el-select v-model=" -->
        <!-- 4 周。 -->
        <el-option :value="4" label="周报 4 周" /> <!-- <el-option :value="4 -->
        <!-- 8 周。 -->
        <el-option :value="8" label="周报 8 周" /> <!-- <el-option :value="8 -->
        <!-- 12 周。 -->
        <el-option :value="12" label="周报 12 周" /> <!-- <el-option :value="1 -->
      </el-select> <!-- 结束 el-select -->
      <!-- 分类依据与数据来源说明。 -->
      <span class="hint">分类依据：{{ basis === 'outbound' ? '出库流水' : '现存量' }}。日报/周报只统计 stock_ledger，不回放历史导入表。</span> <!-- <span class="hint">分 -->
    </div> <!-- 结束 div -->
    <!-- 接口错误提示。 -->
    <p v-if="errorMessage" class="hint">{{ errorMessage }}</p> <!-- <p v-if="errorMessag -->
    <!-- 拣货 KPI 四卡片。 -->
    <section class="kpi-grid" v-if="picking"> <!-- <section class="kpi- -->
      <!-- 拣货任务总数。 -->
      <el-card shadow="never"><strong>{{ picking.total_tasks }}</strong><span>拣货任务</span></el-card> <!-- <el-card shadow="nev -->
      <!-- 已完成任务数。 -->
      <el-card shadow="never"><strong>{{ picking.completed_tasks }}</strong><span>已拣货/完成</span></el-card> <!-- <el-card shadow="nev -->
      <!-- 完成率百分比。 -->
      <el-card shadow="never"><strong>{{ (picking.completion_rate * 100).toFixed(1) }}%</strong><span>拣货完成率</span></el-card> <!-- <el-card shadow="nev -->
      <!-- 平均确认秒数。 -->
      <el-card shadow="never"><strong>{{ picking.average_confirm_seconds }}s</strong><span>平均确认耗时</span></el-card> <!-- <el-card shadow="nev -->
    </section> <!-- 结束 section -->
    <!-- 四张报表网格。 -->
    <section class="report-grid"> <!-- <section class="repo -->
      <!-- ABC 分类表。 -->
      <el-card shadow="never"> <!-- <el-card shadow="nev -->
        <!-- 卡片标题。 -->
        <template #header><div class="card-title">ABC 分类</div></template> <!-- 页面模板 -->
        <!-- 有数据时展示表格。 -->
        <el-table v-if="visibleAbc.length" :data="visibleAbc" stripe height="360"> <!-- <el-table v-if="visi -->
          <!-- 系统 SKU。 -->
          <el-table-column prop="sku_code" label="系统 SKU" /> <!-- <el-table-column pro -->
          <!-- ABC 分类。 -->
          <el-table-column prop="class" label="分类" width="80" /> <!-- <el-table-column pro -->
          <!-- 份额百分比。 -->
          <el-table-column label="份额" width="100"> <!-- <el-table-column lab -->
            <!-- 转成百分数保留一位小数。 -->
            <template #default="{ row }">{{ (row.share * 100).toFixed(1) }}%</template> <!-- 页面模板 -->
          </el-table-column> <!-- 结束 el-table-column -->
        </el-table> <!-- 结束 el-table -->
        <!-- 无 ABC 数据。 -->
        <EmptyDataState v-else title="暂无 ABC 数据" :description="emptyDescription" /> <!-- <EmptyDataState v-el -->
      </el-card> <!-- 结束 el-card -->
      <!-- 库存周转表。 -->
      <el-card shadow="never"> <!-- <el-card shadow="nev -->
        <!-- 卡片标题。 -->
        <template #header><div class="card-title">库存周转</div></template> <!-- 页面模板 -->
        <!-- 有数据时展示表格。 -->
        <el-table v-if="visibleTurnover.length" :data="visibleTurnover" stripe height="360"> <!-- <el-table v-if="visi -->
          <!-- 系统 SKU。 -->
          <el-table-column prop="sku_code" label="系统 SKU" /> <!-- <el-table-column pro -->
          <!-- 出库量。 -->
          <el-table-column prop="outbound_quantity" label="出库量" /> <!-- <el-table-column pro -->
          <!-- 现存量。 -->
          <el-table-column prop="on_hand_quantity" label="现存量" /> <!-- <el-table-column pro -->
          <!-- 周转率。 -->
          <el-table-column prop="turnover_rate" label="周转率" /> <!-- <el-table-column pro -->
        </el-table> <!-- 结束 el-table -->
        <!-- 无周转数据。 -->
        <EmptyDataState v-else title="暂无周转数据" :description="emptyDescription" /> <!-- <EmptyDataState v-el -->
      </el-card> <!-- 结束 el-card -->
      <!-- 库存日报。 -->
      <el-card shadow="never"> <!-- <el-card shadow="nev -->
        <!-- 卡片标题。 -->
        <template #header><div class="card-title">库存日报</div></template> <!-- 页面模板 -->
        <!-- 有数据时展示表格。 -->
        <el-table v-if="visibleDaily.length" :data="visibleDaily" stripe data-testid="daily-report-table"> <!-- <el-table v-if="visi -->
          <!-- 日期。 -->
          <el-table-column prop="date" label="日期" /> <!-- <el-table-column pro -->
          <!-- 入库量。 -->
          <el-table-column prop="inbound_quantity" label="入库量" /> <!-- <el-table-column pro -->
          <!-- 出库量。 -->
          <el-table-column prop="outbound_quantity" label="出库量" /> <!-- <el-table-column pro -->
        </el-table> <!-- 结束 el-table -->
        <!-- 无日报。 -->
        <EmptyDataState v-else title="暂无日报" :description="emptyDescription" /> <!-- <EmptyDataState v-el -->
      </el-card> <!-- 结束 el-card -->
      <!-- 库存周报。 -->
      <el-card shadow="never"> <!-- <el-card shadow="nev -->
        <!-- 卡片标题。 -->
        <template #header><div class="card-title">库存周报</div></template> <!-- 页面模板 -->
        <!-- 有数据时展示表格。 -->
        <el-table v-if="visibleWeekly.length" :data="visibleWeekly" stripe> <!-- <el-table v-if="visi -->
          <!-- 周。 -->
          <el-table-column prop="week" label="周" /> <!-- <el-table-column pro -->
          <!-- 入库量。 -->
          <el-table-column prop="inbound_quantity" label="入库量" /> <!-- <el-table-column pro -->
          <!-- 出库量。 -->
          <el-table-column prop="outbound_quantity" label="出库量" /> <!-- <el-table-column pro -->
        </el-table> <!-- 结束 el-table -->
        <!-- 无周报。 -->
        <EmptyDataState v-else title="暂无周报" :description="emptyDescription" /> <!-- <EmptyDataState v-el -->
      </el-card> <!-- 结束 el-card -->
    </section> <!-- 结束 section -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台页边距与最大宽度。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; } /* .workspace-page { pa */
/* 筛选卡片与下方留白并裁切溢出。 */
.filter-card { margin-bottom: 16px; overflow: hidden; } /* .filter-card { margi */
/* 工具条横向对齐。 */
.toolbar { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; } /* .toolbar { display:  */
/* KPI 四列网格。 */
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; } /* .kpi-grid { display: */
/* KPI 大号数字。 */
.kpi-grid strong { display: block; font-size: 22px; } /* .kpi-grid strong { d */
/* KPI 标签小号灰色。 */
.kpi-grid span { color: var(--muted); font-size: 12px; } /* .kpi-grid span { col */
/* 报表两列网格。 */
.report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } /* .report-grid { displ */
/* 卡片标题加粗。 */
.card-title { font-weight: 700; } /* .card-title { font-w */
/* 提示文字小号灰色。 */
.hint { color: var(--muted); font-size: 12px; } /* .hint { color: var(- */
/* 中等宽度改为两列。 */
@media (max-width: 1100px) { .report-grid, .kpi-grid { grid-template-columns: 1fr 1fr; } } /* @media (max-width: 1 */
</style> <!-- 结束 style -->
