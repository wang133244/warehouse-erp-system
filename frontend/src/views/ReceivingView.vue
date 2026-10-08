<!-- 收货确认页。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入收货页控制器。
import { useReceivingController } from '../controllers/receivingController' // import { useReceivin

// 从控制器取出配置、列表与确认方法。
const { // const {
  // 页面文案配置。
  config, // config,
  // 待收货行。
  rows, // rows,
  // 商品字典。
  products, // products,
  // 库位字典。
  locations, // locations,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 正在确认的入库单 ID。
  pendingId, // pendingId,
  // 按 ID 取商品名。
  productName, // productName,
  // 按 ID 取库位名。
  locationName, // locationName,
  // 把明细拼成可读文本。
  lineText, // lineText,
  // 加载列表。
  loadData, // loadData,
  // 提交收货确认。
  confirm // confirm
} = useReceivingController() // } = useReceivingCont

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 收货确认页主容器。 -->
  <main class="workspace-page" data-testid="receiving-page"> <!-- <main class="workspa -->
    <!-- 页头使用配置中的标题信息。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 表格卡片。 -->
    <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
      <!-- 接口错误警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
      <!-- 待收货表格。 -->
      <el-table v-loading="loading" :data="rows" class="data-table" height="420"> <!-- <el-table v-loading= -->
        <!-- 入库单号列。 -->
        <el-table-column prop="order_no" label="入库单号" min-width="160" /> <!-- <el-table-column pro -->
        <!-- 待收货明细列。 -->
        <el-table-column label="待收货明细" min-width="280"> <!-- <el-table-column lab -->
          <!-- 用控制器拼出的明细文本。 -->
          <template #default="{ row }">{{ lineText(row) }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 异常/备注列。 -->
        <el-table-column label="异常状态" min-width="120"> <!-- <el-table-column lab -->
          <!-- 无备注时显示「无」。 -->
          <template #default="{ row }">{{ row.note || '无' }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 右侧操作列。 -->
        <el-table-column label="操作" fixed="right" width="140"> <!-- <el-table-column lab -->
          <!-- 行内提交收货。 -->
          <template #default="{ row }"> <!-- 页面模板 -->
            <!-- 确认当前入库单收货，提交中禁用。 -->
            <el-button
              :data-testid="`receiving-confirm-${row.inbound_order_id}`"
              text
              type="primary"
              :disabled="pendingId === row.inbound_order_id"
              @click="confirm(row)"
            >提交收货结果</el-button> <!-- >提交收货结果</el-button> -->
          </template> <!-- 结束 template -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 表格空状态。 -->
        <template #empty> <!-- 页面模板 -->
          <!-- 无待收货记录时的占位。 -->
          <EmptyDataState title="暂无待收货记录" :description="errorMessage || config.emptyDescription" /> <!-- <EmptyDataState titl -->
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
