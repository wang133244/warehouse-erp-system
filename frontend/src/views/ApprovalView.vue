<!-- 审批页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入审批弹窗。
import ApprovalDialog from '../components/business/ApprovalDialog.vue' // import ApprovalDialo
// 引入审批页控制器。
import { useApprovalController } from '../controllers/approvalController' // import { useApproval

// 从控制器取出列表、权限与审批动作。
const { // const {
  // 页面文案配置。
  config, // config,
  // 全局应用状态。
  app, // app,
  // 审批任务行。
  rows, // rows,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 筛选关键字。
  keyword, // keyword,
  // 审批弹窗是否打开。
  dialogVisible, // dialogVisible,
  // 当前正在审批的任务。
  current, // current,
  // 正在提交的任务 ID。
  pendingId, // pendingId,
  // 当前用户是否具备审批权限。
  canDecide, // canDecide,
  // 当前用户能否处理该行。
  canHandle, // canHandle,
  // 状态码转中文。
  statusText, // statusText,
  // 业务类型转中文。
  typeText, // typeText,
  // 加载列表。
  loadData, // loadData,
  // 打开审批弹窗。
  openDecision, // openDecision,
  // 提交同意/驳回。
  decide, // decide,
  // 按关键字查询。
  search, // search,
  // 重置筛选。
  reset // reset
} = useApprovalController() // } = useApprovalContr

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 审批页主容器。 -->
  <main class="workspace-page" data-testid="workspace-extension-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 表格卡片。 -->
    <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
      <!-- 关键字筛选条。 -->
      <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-model -->
      <!-- 接口错误警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
      <!-- 审批任务表。 -->
      <el-table v-loading="loading" :data="rows" class="data-table" height="420"> <!-- <el-table v-loading= -->
        <!-- 审批编号列。 -->
        <el-table-column prop="approval_task_id" label="审批编号" min-width="110" /> <!-- <el-table-column pro -->
        <!-- 业务类型列。 -->
        <el-table-column label="业务类型" min-width="120"> <!-- <el-table-column lab -->
          <!-- 把业务类型码转成中文。 -->
          <template #default="{ row }">{{ typeText(row.business_type) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 业务单号列。 -->
        <el-table-column label="业务单号" min-width="170"> <!-- <el-table-column lab -->
          <!-- 优先展示摘要中的单号。 -->
          <template #default="{ row }">{{ row.business_summary?.order_no ?? row.business_id }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 审批状态列。 -->
        <el-table-column label="审批状态" min-width="110"> <!-- <el-table-column lab -->
          <!-- 状态码转中文。 -->
          <template #default="{ row }">{{ statusText(row.status) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 右侧操作列。 -->
        <el-table-column label="操作" fixed="right" width="160"> <!-- <el-table-column lab -->
          <!-- 待审批且有权限时显示查看申请。 -->
          <template #default="{ row }"> <!-- 页面模板 -->
            <!-- 打开审批弹窗。 -->
            <el-button
              v-if="canDecide && row.status === 'pending' && canHandle(row)"
              :data-testid="`approval-open-${row.approval_task_id}`"
              text
              type="primary"
              @click="openDecision(row)"
            >查看申请</el-button> <!-- >查看申请</el-button> -->
          </template> <!-- 结束 template -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 表格空状态。 -->
        <template #empty> <!-- 页面模板 -->
          <!-- 无待审批事项时的占位。 -->
          <EmptyDataState title="暂无待审批事项" :description="errorMessage || config.emptyDescription" /> <!-- <EmptyDataState titl -->
        </template> <!-- 结束 template -->
      </el-table> <!-- 结束 el-table -->
    </el-card> <!-- 结束 el-card -->
    <!-- 同意/驳回弹窗。 -->
    <ApprovalDialog v-model="dialogVisible" :task="current" :submitting="pendingId !== null" @submit="decide" /> <!-- <ApprovalDialog v-mo -->
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
