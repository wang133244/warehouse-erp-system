<!-- 多数业务表页的通用工作台。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入箭头与信息图标。
import { ArrowRight, InfoFilled } from '@element-plus/icons-vue' // import { ArrowRight,
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入看板统计卡。
import StatCard from '../components/business/StatCard.vue' // import StatCard from
// 引入入出库作业弹窗。
import OperationDialog from '../components/business/OperationDialog.vue' // import OperationDial
// 引入主数据弹窗。
import CatalogDialog from '../components/business/CatalogDialog.vue' // import CatalogDialog
// 引入简易柱状图。
import SimpleBarChart from '../components/business/SimpleBarChart.vue' // import SimpleBarChar
// 引入工作台控制器。
import { useWorkspaceController } from '../controllers/workspaceController' // import { useWorkspac

// 从控制器取出当前页配置、列表、看板与各类动作。
const { // const {
  // 当前路由。
  route, // route,
  // 路由实例。
  router, // router,
  // 全局应用状态。
  app, // app,
  // 当前页面配置。
  config, // config,
  // 表格行。
  rows, // rows,
  // 总条数。
  total, // total,
  // 加载中。
  loading, // loading,
  // 错误文案。
  errorMessage, // errorMessage,
  // 筛选关键字。
  keyword, // keyword,
  // 当前页码。
  currentPage, // currentPage,
  // 每页条数。
  pageSize, // pageSize,
  // 入库页：待确认 / 历史。
  inboundView, // inboundView,
  // 入库表引用，用于全选。
  inboundTableRef, // inboundTableRef,
  // 已勾选的入库单。
  selectedInbounds, // selectedInbounds,
  // 看板汇总。
  dashboardSummary, // dashboardSummary,
  // 看板图表数据。
  dashboardCharts, // dashboardCharts,
  // 作业弹窗是否打开。
  dialogVisible, // dialogVisible,
  // 主数据弹窗是否打开。
  catalogVisible, // catalogVisible,
  // 主数据种类。
  catalogKind, // catalogKind,
  // 主数据保存中。
  catalogSubmitting, // catalogSubmitting,
  // 正在编辑的商品。
  editingProduct, // editingProduct,
  // 正在编辑的库位。
  editingLocation, // editingLocation,
  // 当前作业动作名。
  selectedAction, // selectedAction,
  // 助手带入的作业草稿。
  operationDraft, // operationDraft,
  // 库位地图弹窗是否打开。
  locationMapVisible, // locationMapVisible,
  // 库位地图加载中。
  locationMapLoading, // locationMapLoading,
  // 按仓库/库区分组的库位。
  locationMapGroups, // locationMapGroups,
  // 记录详情弹窗是否打开。
  detailVisible, // detailVisible,
  // 详情 JSON 行。
  detailRow, // detailRow,
  // 商品字典。
  productMap, // productMap,
  // 库位字典。
  locationMap, // locationMap,
  // 仓库字典。
  warehouseMap, // warehouseMap,
  // 主数据是否已加载。
  referenceLoaded, // referenceLoaded,
  // 作业弹窗商品选项。
  productOptions, // productOptions,
  // 作业弹窗库位选项。
  locationOptions, // locationOptions,
  // 分页偏移。
  offset, // offset,
  // 空状态说明。
  emptyDescription, // emptyDescription,
  // 看板卡片数据。
  dashboardCards, // dashboardCards,
  // 列标题映射到字段名。
  getColumnField, // getColumnField,
  // 状态码转中文。
  statusText, // statusText,
  // 流水方向文案。
  ledgerDirection, // ledgerDirection,
  // 时间格式化。
  formatDateTime, // formatDateTime,
  // 加载主数据。
  loadReferenceData, // loadReferenceData,
  // 加载商品。
  loadProducts, // loadProducts,
  // 加载库位。
  loadLocations, // loadLocations,
  // 加载库存。
  loadInventory, // loadInventory,
  // 加载流水。
  loadLedgers, // loadLedgers,
  // 加载入库单。
  loadInbounds, // loadInbounds,
  // 加载出库单。
  loadOutbounds, // loadOutbounds,
  // 加载拣货任务。
  loadPickingTasks, // loadPickingTasks,
  // 加载导入批次。
  loadImports, // loadImports,
  // 加载审计日志。
  loadAuditLogs, // loadAuditLogs,
  // 加载预警。
  loadAlerts, // loadAlerts,
  // 按当前页加载列表。
  loadData, // loadData,
  // 套用待处理草稿。
  applyPendingDraft, // applyPendingDraft,
  // 查询。
  search, // search,
  // 重置筛选。
  reset, // reset,
  // 翻页。
  changePage, // changePage,
  // 打印拣货单。
  printPickingList, // printPickingList,
  // 打开顶部动作。
  openAction, // openAction,
  // 当前行可用的行内动作。
  rowAction, // rowAction,
  // 执行行内动作。
  handleRowAction, // handleRowAction,
  // 当前用户可见的顶部按钮。
  visibleActions, // visibleActions,
  // 分组页可见子功能。
  visibleChildren, // visibleChildren,
  // 入库是否全选。
  inboundAllSelected, // inboundAllSelected,
  // 入库是否半选。
  inboundIndeterminate, // inboundIndeterminate
  // 切换入库视图。
  switchInboundView, // switchInboundView,
  // 勾选变化。
  onInboundSelection, // onInboundSelection,
  // 切换全选。
  toggleInboundSelectAll, // toggleInboundSelectA
  // 批量确认收货。
  confirmSelectedInbounds, // confirmSelectedInbou
  // 保存主数据。
  submitCatalog, // submitCatalog,
  // 提交作业。
  submitAction // submitAction
} = useWorkspaceController() // } = useWorkspaceCont

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 通用工作台主容器。 -->
  <main class="workspace-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->

    <!-- 分组导航页：展示子功能入口。 -->
    <template v-if="config.kind === 'group'"> <!-- 页面模板 -->
      <!-- 模块介绍横幅。 -->
      <section class="module-hero"> <!-- <section class="modu -->
        <!-- 文案区。 -->
        <div> <!-- <div> -->
          <!-- 眉题。 -->
          <div class="eyebrow">模块功能导航</div> <!-- <div class="eyebrow" -->
          <!-- 引导标题。 -->
          <h2>选择功能进入具体页面</h2> <!-- <h2>选择功能进入具体页面</h2> -->
          <!-- 说明。 -->
          <p>核心业务页面已接入 FastAPI，可查看真实商品、库存和作业数据。</p> <!-- <p>核心业务页面已接入 FastAPI -->
        </div> <!-- 结束 div -->
        <!-- 可见功能数量。 -->
        <el-tag type="success" effect="plain">{{ visibleChildren.length }} 个功能</el-tag> <!-- <el-tag type="succes -->
      </section> <!-- 结束 section -->
      <!-- 灰色提示条。 -->
      <el-card shadow="never" class="module-note"><el-icon><InfoFilled /></el-icon><span>请选择下面的功能进入具体页面。待入库确认、出库复核、用户管理和智能查询均已接入真实接口。</span></el-card> <!-- <el-card shadow="nev -->
      <!-- 子功能卡片网格：图标、标题、说明、进入。 -->
      <section class="module-grid"><el-card v-for="child in visibleChildren" :key="child.path" shadow="never" class="module-card" @click="router.push(child.path)"><div class="module-icon">{{ child.icon }}</div><div class="module-card-content"><h3>{{ child.label }}</h3><p>{{ child.subtitle }}</p><span>进入功能 <el-icon><ArrowRight /></el-icon></span></div></el-card></section> <!-- <section class="modu -->
    </template> <!-- 结束 template -->

    <!-- 看板页：统计卡与图表。 -->
    <template v-else-if="config.kind === 'dashboard'"> <!-- 页面模板 -->
      <!-- 统计卡网格。 -->
      <section class="stat-grid"><StatCard v-for="card in dashboardCards" :key="card.label" :label="card.label" :value="card.value" :hint="card.hint" :accent="card.accent" /></section> <!-- <section class="stat -->
      <!-- 图表网格。 -->
      <section class="dashboard-grid"> <!-- <section class="dash -->
        <!-- 近 7 日入库柱状图。 -->
        <el-card shadow="never" class="chart-card"> <!-- <el-card shadow="nev -->
          <!-- 入库单数趋势。 -->
          <SimpleBarChart title="近 7 日入库单数" :points="(dashboardCharts?.inbound_by_day ?? []).map((item) => ({ label: item.date, value: item.count }))" /> <!-- <SimpleBarChart titl -->
        </el-card> <!-- 结束 el-card -->
        <!-- 近 7 日出库柱状图。 -->
        <el-card shadow="never" class="chart-card"> <!-- <el-card shadow="nev -->
          <!-- 出库单数趋势。 -->
          <SimpleBarChart title="近 7 日出库单数" :points="(dashboardCharts?.outbound_by_day ?? []).map((item) => ({ label: item.date, value: item.count }))" /> <!-- <SimpleBarChart titl -->
        </el-card> <!-- 结束 el-card -->
        <!-- 仓库库存分布。 -->
        <el-card shadow="never" class="wide-card"> <!-- <el-card shadow="nev -->
          <!-- 卡片标题与说明。 -->
          <template #header><div class="card-title"><span>仓库库存分布</span><span class="card-caption">按仓库汇总实际库存</span></div></template> <!-- 页面模板 -->
          <!-- 按仓库列出数量。 -->
          <div class="warehouse-bars"> <!-- <div class="warehous -->
            <!-- 每个仓库一行。 -->
            <div v-for="item in dashboardCharts?.stock_by_warehouse ?? []" :key="item.warehouse_id" class="warehouse-bar"> <!-- <div v-for="item in  -->
              <!-- 仓库编码与名称。 -->
              <span>{{ item.warehouse_code }} {{ item.warehouse_name }}</span> <!-- <span>{{ item.wareho -->
              <!-- 库存数量。 -->
              <b>{{ item.quantity }}</b> <!-- <b>{{ item.quantity  -->
            </div> <!-- 结束 div -->
            <!-- 无汇总时的空状态。 -->
            <EmptyDataState v-if="!dashboardCharts?.stock_by_warehouse?.length" title="暂无仓库汇总" description="库存余额接入后将按仓库汇总。" /> <!-- <EmptyDataState v-if -->
          </div> <!-- 结束 div -->
        </el-card> <!-- 结束 el-card -->
      </section> <!-- 结束 section -->
    </template> <!-- 结束 template -->

    <!-- 普通列表页。 -->
    <template v-else> <!-- 页面模板 -->
      <!-- 表格卡片。 -->
      <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
        <!-- 关键字筛选条。 -->
        <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-model -->
        <!-- 接口错误警告。 -->
        <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
        <!-- 表头工具条：视图切换 / 标题 / 动作按钮。 -->
        <div class="table-toolbar"> <!-- <div class="table-to -->
          <!-- 左侧标题或入库视图切换。 -->
          <div class="toolbar-left"> <!-- <div class="toolbar- -->
            <!-- 入库页：待确认 / 历史。 -->
            <template v-if="route.path === '/inbounds'"> <!-- 页面模板 -->
              <!-- 待入库确认列表。 -->
              <el-button :type="inboundView === 'pending' ? 'primary' : 'default'" @click="switchInboundView('pending')">待入库确认列表</el-button> <!-- <el-button :type="in -->
              <!-- 历史记录。 -->
              <el-button :type="inboundView === 'history' ? 'primary' : 'default'" data-testid="inbound-history" @click="switchInboundView('history')">历史记录</el-button> <!-- <el-button :type="in -->
            </template> <!-- 结束 template -->
            <!-- 其他页显示列表标题。 -->
            <span v-else class="table-title">{{ config.title }}列表</span> <!-- <span v-else class=" -->
            <!-- 总条数。 -->
            <span class="table-count">共 {{ total }} 条</span> <!-- <span class="table-c -->
          </div> <!-- 结束 div -->
          <!-- 顶部动作按钮，新建类用主色。 -->
          <div class="action-buttons"><el-button v-for="action in visibleActions" :key="action" :type="/新建|上传|生成|收货确认/.test(action) ? 'primary' : 'default'" @click="openAction(action)">{{ action }}</el-button></div> <!-- <div class="action-b -->
        </div> <!-- 结束 div -->
        <!-- 数据表，入库待确认时支持勾选。 -->
        <el-table
          ref="inboundTableRef"
          v-loading="loading"
          :data="rows"
          class="data-table"
          :class="{ 'inbound-pending-table': route.path === '/inbounds' && inboundView === 'pending' }"
          height="390"
          @selection-change="onInboundSelection"
        > <!-- > -->
          <!-- 入库待确认显示勾选列。 -->
          <el-table-column v-if="route.path === '/inbounds' && inboundView === 'pending'" type="selection" width="48" /> <!-- <el-table-column v-i -->
          <!-- 按页面配置动态列。 -->
          <el-table-column v-for="column in config.columns" :key="column" :prop="getColumnField(column)" :label="column" min-width="150" /> <!-- <el-table-column v-f -->
          <!-- 非入库待确认时显示行内操作。 -->
          <el-table-column v-if="route.path !== '/inbounds' || inboundView === 'history'" label="操作" fixed="right" width="150"> <!-- <el-table-column v-i -->
            <!-- 行内主操作按钮。 -->
            <template #default="{ row }"><el-button v-if="rowAction(row)" data-testid="row-action" text type="primary" @click="handleRowAction(row)">{{ rowAction(row)?.label }}</el-button></template> <!-- 页面模板 -->
          </el-table-column> <!-- 结束 el-table-column -->
          <!-- 表格空状态。 -->
          <template #empty><EmptyDataState :title="config.emptyTitle" :description="emptyDescription" /></template> <!-- 页面模板 -->
        </el-table> <!-- 结束 el-table -->
        <!-- 入库待确认底部全选与已选提示。 -->
        <div v-if="route.path === '/inbounds' && inboundView === 'pending'" class="inbound-footer"> <!-- <div v-if="route.pat -->
          <!-- 自定义全选，避免表头复选框重复。 -->
          <el-checkbox data-testid="inbound-select-all" :model-value="inboundAllSelected" :indeterminate="inboundIndeterminate" @click.prevent="toggleInboundSelectAll(!inboundAllSelected)">全选</el-checkbox> <!-- <el-checkbox data-te -->
          <!-- 已选条数说明。 -->
          <span>已选 {{ selectedInbounds.length }} 条，点「收货确认」后写入历史记录</span> <!-- <span>已选 {{ selected -->
        </div> <!-- 结束 div -->
        <!-- 底部分页。 -->
        <div class="pagination"><span>支持服务端分页、筛选和排序</span><el-pagination background layout="prev, pager, next" :total="total" :page-size="pageSize" :current-page="currentPage" @current-change="changePage" /></div> <!-- <div class="paginati -->
      </el-card> <!-- 结束 el-card -->
    </template> <!-- 结束 template -->

    <!-- 入出库作业弹窗。 -->
    <OperationDialog v-model="dialogVisible" :action="selectedAction" :page-title="config.title" :products="productOptions" :locations="locationOptions" :draft="operationDraft" @submit="submitAction" /> <!-- <OperationDialog v-m -->
    <!-- 商品/仓库/库位弹窗。 -->
    <CatalogDialog v-model="catalogVisible" :kind="catalogKind" :warehouses="Array.from(warehouseMap.values())" :product="editingProduct" :location="editingLocation" :submitting="catalogSubmitting" @submit="submitCatalog" /> <!-- <CatalogDialog v-mod -->
    <!-- 库位信息弹窗。 -->
    <el-dialog v-model="locationMapVisible" title="库位信息" width="860px"> <!-- <el-dialog v-model=" -->
      <!-- 分组说明。 -->
      <p class="map-hint">按仓库 / 库区列出全部库位，可在右侧滚动查看。</p> <!-- <p class="map-hint"> -->
      <!-- 可滚动的分组列表。 -->
      <el-scrollbar v-loading="locationMapLoading" height="62vh" class="map-scroll"> <!-- <el-scrollbar v-load -->
        <!-- 每个仓库库区一组。 -->
        <div v-for="group in locationMapGroups" :key="`${group.warehouse_code}-${group.zone_code}`" class="map-group"> <!-- <div v-for="group in -->
          <!-- 仓库 / 库区。 -->
          <strong>{{ group.warehouse_code }} / {{ group.zone_code }}</strong> <!-- <strong>{{ group.war -->
          <!-- 库位数量。 -->
          <span>共 {{ group.location_count }} 个库位</span> <!-- <span>共 {{ group.loc -->
          <!-- 库位编码用顿号拼接。 -->
          <p class="map-codes">{{ group.location_codes.join('、') }}</p> <!-- <p class="map-codes" -->
        </div> <!-- 结束 div -->
        <!-- 无库位时的空状态。 -->
        <EmptyDataState v-if="!locationMapLoading && !locationMapGroups.length" title="暂无库位" description="请先维护仓库与库位。" /> <!-- <EmptyDataState v-if -->
      </el-scrollbar> <!-- 结束 el-scrollbar -->
    </el-dialog> <!-- 结束 el-dialog -->
    <!-- 记录详情 JSON 弹窗。 -->
    <el-dialog v-model="detailVisible" title="记录详情" width="560px"> <!-- <el-dialog v-model=" -->
      <!-- 格式化 JSON。 -->
      <pre class="detail-json">{{ JSON.stringify(detailRow, null, 2) }}</pre> <!-- <pre class="detail-j -->
    </el-dialog> <!-- 结束 el-dialog -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台、看板网格、表格工具条、模块导航与库位地图等样式。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; }.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }.dashboard-grid { display: grid; grid-template-columns: 1.45fr 1fr; gap: 16px; }.wide-card { grid-column: 1 / -1; }.card-title { display: flex; align-items: center; justify-content: space-between; font-weight: 700; font-size: 14px; }.card-caption { color: var(--muted); font-weight: 400; font-size: 12px; }.warehouse-bars { display: grid; gap: 10px; padding: 8px 4px; }.warehouse-bar { display: flex; justify-content: space-between; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px; }.table-card { overflow: hidden; }.table-error { margin: 12px 16px 0; }.table-toolbar { display: flex; justify-content: space-between; gap: 18px; align-items: center; padding: 16px; }.table-title { font-weight: 700; }.toolbar-left { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }.inbound-footer { display: flex; align-items: center; gap: 16px; padding: 12px 16px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }.inbound-pending-table :deep(thead .el-table-column--selection .el-checkbox) { display: none; }.table-count { margin-left: 9px; color: var(--muted); font-size: 12px; }.action-buttons { display: flex; gap: 8px; flex-wrap: wrap; justify-content: end; }.data-table { width: 100%; border-top: 1px solid var(--line); }.data-table :deep(.el-table__empty-block) { width: 100% !important; }.pagination { height: 58px; padding: 0 16px; color: var(--muted); font-size: 12px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--line); }.ai-grid { display: grid; grid-template-columns: 255px minmax(430px, 1fr) 280px; gap: 16px; }.ask-box { display: flex; align-items: end; gap: 10px; padding: 14px 0 0; border-top: 1px solid var(--line); }.ask-box :deep(.el-input) { flex: 1; }.module-hero { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 20px 22px; margin-bottom: 16px; background: linear-gradient(135deg, #f5f8ff, #ffffff); border: 1px solid var(--line); border-radius: 14px; }.module-hero h2 { margin: 0 0 7px; font-size: 18px; }.module-hero p { margin: 0; color: var(--muted); font-size: 13px; }.module-note { margin-bottom: 16px; color: var(--muted); }.module-note :deep(.el-card__body) { display: flex; align-items: center; gap: 9px; padding: 14px 18px; font-size: 13px; }.module-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }.module-card { cursor: pointer; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }.module-card:hover { transform: translateY(-3px); border-color: #91b8ff; box-shadow: 0 12px 28px rgba(37,95,203,.12); }.module-card :deep(.el-card__body) { display: flex; align-items: flex-start; gap: 15px; min-height: 138px; padding: 22px; }.module-icon { width: 42px; height: 42px; flex: 0 0 42px; display: grid; place-items: center; border-radius: 12px; color: var(--brand); background: #edf4ff; font-size: 21px; font-weight: 700; }.module-card-content { min-width: 0; }.module-card h3 { margin: 1px 0 8px; font-size: 16px; }.module-card p { min-height: 38px; margin: 0 0 13px; color: var(--muted); font-size: 12px; line-height: 1.7; }.module-card span { display: inline-flex; align-items: center; gap: 4px; color: var(--brand); font-size: 12px; font-weight: 700; }.map-hint { color: var(--muted); font-size: 12px; margin: 0 0 12px; }.map-scroll { padding-right: 6px; }.map-group { display: grid; gap: 6px; padding: 12px 4px 14px; border-bottom: 1px solid var(--line); }.map-codes { margin: 0; color: #334155; font-size: 13px; line-height: 1.8; overflow-wrap: anywhere; word-break: break-word; }.detail-json { white-space: pre-wrap; font-size: 12px; line-height: 1.6; } /* .workspace-page { pa */
/* 中等宽度：看板两列、图表单列。 */
@media (max-width: 1100px) { .stat-grid { grid-template-columns: repeat(2, 1fr); }.ai-grid { grid-template-columns: 1fr; }.dashboard-grid { grid-template-columns: 1fr; } } /* @media (max-width: 1 */
/* 平板：模块入口两列。 */
@media (max-width: 900px) { .module-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } } /* @media (max-width: 9 */
/* 手机：单列并缩小内边距。 */
@media (max-width: 700px) { .workspace-page { padding: 19px 15px; }.stat-grid { grid-template-columns: 1fr; }.table-toolbar, .pagination { align-items: flex-start; flex-direction: column; height: auto; padding: 14px; }.action-buttons { justify-content: start; }.module-grid { grid-template-columns: 1fr; }.module-hero { align-items: flex-start; flex-direction: column; } } /* @media (max-width: 7 */
</style> <!-- 结束 style -->
