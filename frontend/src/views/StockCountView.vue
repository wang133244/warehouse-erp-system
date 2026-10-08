<!-- 盘点页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入盘点弹窗。
import StockCountDialog from '../components/business/StockCountDialog.vue' // import StockCountDia
// 引入盘点页控制器。
import { useStockCountController } from '../controllers/stockCountController' // import { useStockCou

// 从控制器取出列表、权限与盘点动作。
const { // const {
  // 页面文案配置。
  config, // config,
  // 全局应用状态。
  app, // app,
  // 盘点单行。
  rows, // rows,
  // 商品列表。
  products, // products,
  // 库位列表。
  locations, // locations,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 筛选关键字。
  keyword, // keyword,
  // 弹窗是否打开。
  dialogVisible, // dialogVisible,
  // 正在编辑的盘点单。
  editing, // editing,
  // 弹窗保存中。
  submitting, // submitting,
  // 行内提交中的盘点单 ID。
  pendingId, // pendingId,
  // 当前用户是否可写。
  canWrite, // canWrite,
  // 状态码转中文。
  statusText, // statusText,
  // 按 ID 取商品名。
  productName, // productName,
  // 按 ID 取库位名。
  locationName, // locationName,
  // 把明细拼成可读文本。
  lineText, // lineText,
  // 加载列表。
  loadData, // loadData,
  // 打开新建弹窗。
  openCreate, // openCreate,
  // 打开实盘录入。
  openEdit, // openEdit,
  // 弹窗保存回调。
  submitDialog, // submitDialog,
  // 行内提交盘点。
  submitRow, // submitRow,
  // 按关键字查询。
  search, // search,
  // 重置筛选。
  reset // reset
} = useStockCountController() // } = useStockCountCon

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 盘点页主容器。 -->
  <main class="workspace-page" data-testid="workspace-extension-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 表格卡片。 -->
    <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
      <!-- 关键字筛选条。 -->
      <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-model -->
      <!-- 新建按钮工具条。 -->
      <div class="toolbar"> <!-- <div class="toolbar" -->
        <!-- 有写权限时显示新建盘点单。 -->
        <el-button v-if="canWrite" type="primary" data-testid="stock-count-create" @click="openCreate">新建盘点单</el-button> <!-- <el-button v-if="can -->
      </div> <!-- 结束 div -->
      <!-- 接口错误警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
      <!-- 盘点单表。 -->
      <el-table v-loading="loading" :data="rows" class="data-table" height="420"> <!-- <el-table v-loading= -->
        <!-- 盘点单号列。 -->
        <el-table-column prop="order_no" label="盘点单号" min-width="170" /> <!-- <el-table-column pro -->
        <!-- 明细摘要列。 -->
        <el-table-column label="明细" min-width="280"> <!-- <el-table-column lab -->
          <!-- 用控制器拼出的明细文本。 -->
          <template #default="{ row }">{{ lineText(row) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 状态列。 -->
        <el-table-column label="状态" min-width="120"> <!-- <el-table-column lab -->
          <!-- 状态码转中文。 -->
          <template #default="{ row }">{{ statusText(row.status) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 右侧操作列。 -->
        <el-table-column label="操作" fixed="right" width="180"> <!-- <el-table-column lab -->
          <!-- 草稿/盘点中可录入实盘并提交。 -->
          <template #default="{ row }"> <!-- 页面模板 -->
            <!-- 打开实盘录入弹窗。 -->
            <el-button
              v-if="canWrite && (row.status === 'draft' || row.status === 'counting')"
              text
              type="primary"
              @click="openEdit(row)"
            >录入实盘</el-button> <!-- >录入实盘</el-button> -->
            <!-- 提交盘点单。 -->
            <el-button
              v-if="canWrite && (row.status === 'draft' || row.status === 'counting')"
              :data-testid="`stock-count-submit-${row.stock_count_order_id}`"
              text
              type="primary"
              :disabled="pendingId === row.stock_count_order_id"
              @click="submitRow(row)"
            >提交盘点</el-button> <!-- >提交盘点</el-button> -->
          </template> <!-- 结束 template -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 表格空状态。 -->
        <template #empty> <!-- 页面模板 -->
          <!-- 无盘点单时的占位。 -->
          <EmptyDataState title="暂无盘点单" :description="errorMessage || config.emptyDescription" /> <!-- <EmptyDataState titl -->
        </template> <!-- 结束 template -->
      </el-table> <!-- 结束 el-table -->
    </el-card> <!-- 结束 el-card -->
    <!-- 新建/实盘弹窗。 -->
    <StockCountDialog
      v-model="dialogVisible"
      :products="products"
      :locations="locations"
      :initial-value="editing"
      :submitting="submitting"
      @submit="submitDialog"
    /> <!-- /> -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台页边距与最大宽度。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; } /* .workspace-page { pa */
/* 工具条内边距。 */
.toolbar { padding: 16px 16px 0; } /* .toolbar { padding:  */
/* 表格上方错误条间距。 */
.table-error { margin: 16px; } /* .table-error { margi */
/* 表格通栏并带顶部分割线。 */
.data-table { width: 100%; border-top: 1px solid var(--line); } /* .data-table { width: */
</style> <!-- 结束 style -->
