<!-- 调拨页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入调拨弹窗。
import TransferDialog from '../components/business/TransferDialog.vue' // import TransferDialo
// 引入调拨页控制器。
import { useTransferController } from '../controllers/transferController' // import { useTransfer

// 从控制器取出待处理/历史列表与调拨动作。
const { // const {
  // 待处理状态集合。
  PENDING_STATUSES, // PENDING_STATUSES,
  // 历史状态集合。
  HISTORY_STATUSES, // HISTORY_STATUSES,
  // 页面文案配置。
  config, // config,
  // 全局应用状态。
  app, // app,
  // 调拨单行。
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
  // 当前列表视图：待处理或历史。
  listView, // listView,
  // 弹窗是否打开。
  dialogVisible, // dialogVisible,
  // 正在编辑的调拨单。
  editing, // editing,
  // 弹窗保存中。
  submitting, // submitting,
  // 行内操作中的调拨单 ID。
  pendingId, // pendingId,
  // 当前用户是否可写。
  canWrite, // canWrite,
  // 状态码转中文。
  statusText, // statusText,
  // 按 ID 取库位名。
  locationName, // locationName,
  // 把明细拼成可读文本。
  lineText, // lineText,
  // 加载列表。
  loadData, // loadData,
  // 切换待处理/历史。
  switchView, // switchView,
  // 打开新建。
  openCreate, // openCreate,
  // 打开编辑。
  openEdit, // openEdit,
  // 弹窗保存回调。
  submitDialog, // submitDialog,
  // 行内提交审批。
  submitRow, // submitRow,
  // 库存不足等错误文本。
  inventoryErrorText, // inventoryErrorText,
  // 执行已审批调拨。
  executeRow, // executeRow,
  // 按关键字查询。
  search, // search,
  // 重置筛选。
  reset // reset
} = useTransferController() // } = useTransferContr

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 调拨页主容器。 -->
  <main class="workspace-page" data-testid="workspace-extension-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 表格卡片。 -->
    <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
      <!-- 关键字筛选条。 -->
      <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-model -->
      <!-- 视图切换与新建工具条。 -->
      <div class="toolbar"> <!-- <div class="toolbar" -->
        <!-- 切到待处理列表。 -->
        <el-button :type="listView === 'pending' ? 'primary' : 'default'" data-testid="transfer-pending" @click="switchView('pending')">待处理</el-button> <!-- <el-button :type="li -->
        <!-- 切到历史记录。 -->
        <el-button :type="listView === 'history' ? 'primary' : 'default'" data-testid="transfer-history" @click="switchView('history')">历史记录</el-button> <!-- <el-button :type="li -->
        <!-- 待处理视图且可写时显示新建。 -->
        <el-button v-if="canWrite && listView === 'pending'" type="primary" data-testid="transfer-create" @click="openCreate">新建调拨单</el-button> <!-- <el-button v-if="can -->
        <!-- 流程说明。 -->
        <span class="hint">提交后进入审批中心，审批通过后才能执行。已完成调拨在历史记录中查看。</span> <!-- <span class="hint">提 -->
      </div> <!-- 结束 div -->
      <!-- 接口错误警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
      <!-- 调拨单表。 -->
      <el-table v-loading="loading" :data="rows" class="data-table" height="420"> <!-- <el-table v-loading= -->
        <!-- 调拨单号列。 -->
        <el-table-column prop="order_no" label="调拨单号" min-width="170" /> <!-- <el-table-column pro -->
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
        <!-- 创建人账号列。 -->
        <el-table-column label="账户名" min-width="120"> <!-- <el-table-column lab -->
          <!-- 无账号时显示短横。 -->
          <template #default="{ row }">{{ row.username || '-' }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 待处理视图才显示操作列。 -->
        <el-table-column v-if="listView === 'pending'" label="操作" fixed="right" width="200"> <!-- <el-table-column v-i -->
          <!-- 草稿可编辑/提交，可执行时可执行调拨。 -->
          <template #default="{ row }"> <!-- 页面模板 -->
            <!-- 编辑草稿。 -->
            <el-button v-if="canWrite && row.status === 'draft'" text type="primary" @click="openEdit(row)">编辑</el-button> <!-- <el-button v-if="can -->
            <!-- 提交审批。 -->
            <el-button
              v-if="canWrite && row.status === 'draft'"
              text
              type="primary"
              :disabled="pendingId === row.transfer_order_id"
              @click="submitRow(row)"
            >提交审批</el-button> <!-- >提交审批</el-button> -->
            <!-- 审批通过后执行调拨。 -->
            <el-button
              v-if="canWrite && row.status === 'executable'"
              :data-testid="`transfer-execute-${row.transfer_order_id}`"
              text
              type="primary"
              :disabled="pendingId === row.transfer_order_id"
              @click="executeRow(row)"
            >执行调拨</el-button> <!-- >执行调拨</el-button> -->
          </template> <!-- 结束 template -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 表格空状态。 -->
        <template #empty> <!-- 页面模板 -->
          <!-- 历史与待处理使用不同空标题。 -->
          <EmptyDataState :title="listView === 'history' ? '暂无调拨历史' : '暂无调拨单'" :description="errorMessage || config.emptyDescription" /> <!-- <EmptyDataState :tit -->
        </template> <!-- 结束 template -->
      </el-table> <!-- 结束 el-table -->
    </el-card> <!-- 结束 el-card -->
    <!-- 新建/编辑调拨弹窗。 -->
    <TransferDialog
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
/* 工具条横向折行对齐。 */
.toolbar { padding: 16px 16px 0; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; } /* .toolbar { padding:  */
/* 流程说明小号灰色。 */
.hint { color: var(--muted); font-size: 12px; } /* .hint { color: var(- */
/* 表格上方错误条间距。 */
.table-error { margin: 16px; } /* .table-error { margi */
/* 表格通栏并带顶部分割线。 */
.data-table { width: 100%; border-top: 1px solid var(--line); } /* .data-table { width: */
</style> <!-- 结束 style -->
