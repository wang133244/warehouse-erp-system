<!-- 导入批次明细。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入导入明细页控制器。
import { useImportDetailController } from '../controllers/importDetailController' // import { useImportDe

// 从控制器取出路由、加载状态与批次数据。
const { // const {
  // 当前路由对象。
  route, // route,
  // 路由实例，用于返回列表。
  router, // router,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 当前批次详情。
  batch, // batch,
  // 批次 ID。
  batchId, // batchId,
  // 重新加载方法。
  load // load
} = useImportDetailController() // } = useImportDetailC

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 导入批次详情页主容器。 -->
  <main class="workspace-page" data-testid="import-detail-page"> <!-- <main class="workspa -->
    <!-- 页头：只读查看导入批次。 -->
    <PageHeader title="导入批次详情" subtitle="只读查看 Mega Star 导入批次和校验说明" section="系统管理" /> <!-- <PageHeader title="导 -->
    <!-- 详情卡片，加载时显示遮罩。 -->
    <el-card shadow="never" v-loading="loading"> <!-- <el-card shadow="nev -->
      <!-- 返回列表工具条。 -->
      <div class="toolbar"> <!-- <div class="toolbar" -->
        <!-- 回到导入列表。 -->
        <el-button @click="router.push('/imports')">返回列表</el-button> <!-- <el-button @click="r -->
      </div> <!-- 结束 div -->
      <!-- 加载失败时的警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" /> <!-- <el-alert v-if="erro -->
      <!-- 有批次数据时展示描述列表。 -->
      <el-descriptions v-else-if="batch" :column="2" border> <!-- <el-descriptions v-e -->
        <!-- 批次号。 -->
        <el-descriptions-item label="批次号">{{ batch.batch_no }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 源文件名。 -->
        <el-descriptions-item label="文件名称">{{ batch.dataset_name }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 数据集版本。 -->
        <el-descriptions-item label="数据版本">{{ batch.dataset_version }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 导入状态。 -->
        <el-descriptions-item label="导入状态">{{ batch.status }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 总行数。 -->
        <el-descriptions-item label="导入行数">{{ batch.total_rows }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 校验通过行数。 -->
        <el-descriptions-item label="成功行数">{{ batch.valid_rows }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 校验失败行数。 -->
        <el-descriptions-item label="失败行数">{{ batch.invalid_rows }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 导入时间，按中文 24 小时制格式化。 -->
        <el-descriptions-item label="导入时间">{{ new Date(batch.imported_at).toLocaleString('zh-CN', { hour12: false }) }}</el-descriptions-item> <!-- <el-descriptions-ite -->
        <!-- 校验说明跨两列。 -->
        <el-descriptions-item label="校验说明" :span="2">{{ batch.notes || '无附加说明' }}</el-descriptions-item> <!-- <el-descriptions-ite -->
      </el-descriptions> <!-- 结束 el-descriptions -->
      <!-- 找不到批次时的空状态。 -->
      <EmptyDataState v-else title="未找到导入批次" description="请返回导入列表后重新选择。" /> <!-- <EmptyDataState v-el -->
    </el-card> <!-- 结束 el-card -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台页边距与最大宽度。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; } /* .workspace-page { pa */
/* 工具条与下方内容留白。 */
.toolbar { margin-bottom: 16px; } /* .toolbar { margin-bo */
</style> <!-- 结束 style -->
