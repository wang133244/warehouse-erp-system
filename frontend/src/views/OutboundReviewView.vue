<!-- 出库复核页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入出库复核页控制器。
import { useOutboundReviewController } from '../controllers/outboundReviewController' // import { useOutbound

// 从控制器取出列表、复核与完成出库方法。
const { // const {
  // 页面文案配置。
  config, // config,
  // 出库单行。
  rows, // rows,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 筛选关键字。
  keyword, // keyword,
  // 正在操作的出库单 ID。
  pendingId, // pendingId,
  // 状态码转中文。
  statusText, // statusText,
  // 计算复核数量。
  reviewQuantity, // reviewQuantity,
  // 加载列表。
  loadData, // loadData,
  // 开始复核。
  review, // review,
  // 完成出库。
  complete, // complete,
  // 按关键字查询。
  search, // search,
  // 重置筛选。
  reset // reset
} = useOutboundReviewController() // } = useOutboundRevie

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 出库复核页主容器。 -->
  <main class="workspace-page" data-testid="outbound-review-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 表格卡片。 -->
    <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
      <!-- 关键字筛选条。 -->
      <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-model -->
      <!-- 接口错误警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
      <!-- 出库复核表。 -->
      <el-table v-loading="loading" :data="rows" class="data-table" height="420"> <!-- <el-table v-loading= -->
        <!-- 出库单号列。 -->
        <el-table-column prop="order_no" label="出库单号" min-width="160" /> <!-- <el-table-column pro -->
        <!-- 客户编号列。 -->
        <el-table-column prop="customer_id" label="客户编号" min-width="120" /> <!-- <el-table-column pro -->
        <!-- 复核数量列。 -->
        <el-table-column label="复核数量" min-width="120"> <!-- <el-table-column lab -->
          <!-- 由控制器汇总复核数量。 -->
          <template #default="{ row }">{{ reviewQuantity(row) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 复核状态列。 -->
        <el-table-column label="复核状态" min-width="120"> <!-- <el-table-column lab -->
          <!-- 状态码转中文。 -->
          <template #default="{ row }">{{ statusText(row.status) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 右侧操作列。 -->
        <el-table-column label="操作" fixed="right" width="180"> <!-- <el-table-column lab -->
          <!-- 按状态显示开始复核或完成出库。 -->
          <template #default="{ row }"> <!-- 页面模板 -->
            <!-- 已拣货时开始复核。 -->
            <el-button
              v-if="row.status === 'picked'"
              :data-testid="`outbound-review-${row.outbound_order_id}`"
              text
              type="primary"
              :disabled="pendingId === row.outbound_order_id"
              @click="review(row)"
            >开始复核</el-button> <!-- >开始复核</el-button> -->
            <!-- 已复核时完成出库。 -->
            <el-button
              v-if="row.status === 'reviewed'"
              :data-testid="`outbound-complete-${row.outbound_order_id}`"
              text
              type="primary"
              :disabled="pendingId === row.outbound_order_id"
              @click="complete(row)"
            >完成出库</el-button> <!-- >完成出库</el-button> -->
          </template> <!-- 结束 template -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 表格空状态。 -->
        <template #empty> <!-- 页面模板 -->
          <!-- 无待复核记录时的占位。 -->
          <EmptyDataState title="暂无待复核记录" :description="errorMessage || config.emptyDescription" /> <!-- <EmptyDataState titl -->
        </template> <!-- 结束 template -->
      </el-table> <!-- 结束 el-table -->
    </el-card> <!-- 结束 el-card -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台页边距与最大宽度。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; } /* .workspace-page { pa */
/* 表格上方错误条间距。 */
.table-error { margin: 16px; } /* .table-error { margi */
/* 表格通栏并带顶部分割线。 */
.data-table { width: 100%; border-top: 1px solid var(--line); } /* .data-table { width: */
</style> <!-- 结束 style -->
