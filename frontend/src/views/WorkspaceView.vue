<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, InfoFilled } from '@element-plus/icons-vue'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyDataState from '../components/common/EmptyDataState.vue'
import FilterPanel from '../components/business/FilterPanel.vue'
import StatCard from '../components/business/StatCard.vue'
import OperationDialog from '../components/business/OperationDialog.vue'
import { pageConfigs } from '../config/pages'
import { useBackendUnavailable } from '../composables/useBackendUnavailable'
import { listImports, listLocations, listProducts, listWarehouses, type Location, type Product, type Warehouse } from '../api/catalog'
import {
  getDashboardSummary,
  listAlerts,
  listAuditLogs,
  listBalances,
  listLedgers,
  type DashboardSummary
} from '../api/inventory'
import {
  allocateOutbound,
  completeOutbound,
  confirmInbound,
  confirmPickingTask,
  createInbound,
  createOutbound,
  getInbound,
  getOutbound,
  listInbounds,
  listOutbounds,
  listPickingTasks,
  type OperationSubmission
} from '../api/operations'
import { ApiError } from '../api/client'

type TableRow = Record<string, unknown>

const route = useRoute()
const router = useRouter()
const { notify } = useBackendUnavailable()
const config = computed(() => pageConfigs[route.path] ?? pageConfigs['/dashboard'])

const rows = ref<TableRow[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const dashboardSummary = ref<DashboardSummary | null>(null)
const dialogVisible = ref(false)
const selectedAction = ref('')

const productMap = ref(new Map<number, Product>())
const locationMap = ref(new Map<number, Location>())
const warehouseMap = ref(new Map<number, Warehouse>())
const referenceLoaded = ref(false)
const productOptions = ref<Product[]>([])
const locationOptions = ref<Location[]>([])

const offset = computed(() => (currentPage.value - 1) * pageSize)
const emptyDescription = computed(() =>
  loading.value ? '正在从 FastAPI 加载数据...' : errorMessage.value || config.value.emptyDescription
)

const dashboardCards = computed(() => {
  const summary = dashboardSummary.value
  return [
    { label: '库存总数量', value: summary?.stock_quantity ?? 0, hint: 'stock_balance 实际库存合计', accent: 'var(--brand)' },
    { label: '锁定量', value: summary?.reserved_quantity ?? 0, hint: '已分配给出库单的库存', accent: '#6a8bf5' },
    { label: '可用量', value: summary?.available_quantity ?? 0, hint: '实际库存减去锁定量', accent: 'var(--success)' },
    {
      label: '待处理作业',
      value: (summary?.inbound_draft ?? 0) + (summary?.outbound_pending ?? 0),
      hint: `待入库 ${summary?.inbound_draft ?? 0} / 待出库 ${summary?.outbound_pending ?? 0}`,
      accent: 'var(--warning)'
    }
  ]
})

const columnFields: Record<string, Record<string, string>> = {
  '/products': {
    '系统 SKU': 'sku_code', '商品编码': 'source_product_code', '商品名称': 'product_name',
    '品牌': 'brand', '托盘容量': 'pallet_capacity', '状态': 'status'
  },
  '/locations': {
    '仓库编码': 'warehouse_code', '库位编码': 'location_code', '库区': 'zone_code',
    '巷道': 'aisle_code', '货架': 'rack_code', '储位状态': 'status'
  },
  '/inventory': {
    '系统 SKU': 'sku_code', '商品编码': 'source_product_code', '库位编码': 'location_code',
    '实际库存数量': 'quantity', '可用量': 'available_quantity', '锁定量': 'reserved_quantity',
    '冻结量': 'frozen_quantity', '最后更新时间': 'updated_at'
  },
  '/inventory-ledger': {
    '流水号': 'ledger_id', '系统 SKU': 'sku_code', '库位编码': 'location_code',
    '业务类型': 'transaction_type', '变动数量': 'quantity_delta', '变动前数量': 'before_quantity',
    '变动后数量': 'after_quantity', '发生时间': 'created_at'
  },
  '/inbounds': {
    '入库单号': 'order_no', '商品编码': 'source_product_code', '系统 SKU': 'sku_code',
    '收货数量': 'quantity', '收货库位': 'location_code', '单据状态': 'status', '创建时间': 'created_at'
  },
  '/outbounds': {
    '出库单号': 'order_no', '客户编号': 'customer_id', '商品编码': 'source_product_code',
    '需求数量': 'quantity', '分配数量': 'allocated_quantity', '单据状态': 'status', '创建时间': 'created_at'
  },
  '/picking': {
    '任务号': 'task_no', '出库单号': 'outbound_order_id', '库位编码': 'location_code',
    '系统 SKU': 'sku_code', '拣货数量': 'quantity', '任务状态': 'status', '优先级': 'priority'
  },
  '/imports': {
    '批次号': 'batch_no', '文件名称': 'dataset_name', '数据类型': 'dataset_name',
    '导入行数': 'total_rows', '成功行数': 'valid_rows', '失败行数': 'invalid_rows',
    '导入状态': 'status', '导入时间': 'imported_at'
  },
  '/audit': {
    '审计编号': 'audit_log_id', '操作人': 'user_id', '操作类型': 'action',
    '业务对象': 'entity_type', '业务单号': 'entity_id', '操作结果': 'result', '操作时间': 'created_at'
  },
  '/alerts': {
    '预警编号': 'balance_id', '预警类型': 'alert_type', '系统 SKU': 'sku_code',
    '库位编码': 'location_code', '当前数量': 'quantity', '预警阈值': 'threshold',
    '处理状态': 'status', '产生时间': 'created_at'
  }
}

const getColumnField = (column: string) => columnFields[route.path]?.[column] ?? column

const statusLabels: Record<string, string> = {
  draft: '草稿', confirmed: '已确认', allocated: '已分配', picked: '已拣货', completed: '已完成'
}
const statusText = (status: string) => statusLabels[status] ?? status
const formatDateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'

async function loadReferenceData() {
  if (referenceLoaded.value) return
  const [productPage, locationPage, warehousePage] = await Promise.all([
    listProducts({ limit: 200 }),
    listLocations({ limit: 200 }),
    listWarehouses()
  ])
  productMap.value = new Map(productPage.items.map((item) => [item.product_id, item]))
  locationMap.value = new Map(locationPage.items.map((item) => [item.location_id, item]))
  warehouseMap.value = new Map(warehousePage.items.map((item) => [item.warehouse_id, item]))
  productOptions.value = productPage.items
  locationOptions.value = locationPage.items
  referenceLoaded.value = true
}

async function loadProducts() {
  const page = await listProducts({
    keyword: keyword.value.trim() || undefined,
    offset: offset.value,
    limit: pageSize
  })
  rows.value = page.items.map((item) => ({ ...item, status: '启用' }))
  total.value = page.total ?? page.items.length
}

async function loadLocations() {
  await loadReferenceData()
  const page = await listLocations({ offset: offset.value, limit: pageSize })
  rows.value = page.items.map((item) => ({
    ...item,
    warehouse_code: warehouseMap.value.get(item.warehouse_id)?.warehouse_code ?? `仓库#${item.warehouse_id}`,
    status: '可用'
  }))
  total.value = page.total ?? page.items.length
}

async function loadInventory() {
  await loadReferenceData()
  const page = await listBalances({ offset: offset.value, limit: pageSize })
  rows.value = page.items.map((item) => {
    const product = productMap.value.get(item.product_id)
    const location = locationMap.value.get(item.location_id)
    return {
      ...item,
      sku_code: product?.sku_code ?? `商品#${item.product_id}`,
      source_product_code: product?.source_product_code ?? '-',
      location_code: location?.location_code ?? `库位#${item.location_id}`,
      frozen_quantity: 0
    }
  })
  total.value = page.total ?? page.items.length
}

async function loadLedgers() {
  await loadReferenceData()
  const page = await listLedgers({ limit: 100 })
  rows.value = page.items.map((item) => {
    const product = productMap.value.get(item.product_id)
    const location = locationMap.value.get(item.location_id)
    return {
      ...item,
      created_at: formatDateTime(item.created_at),
      sku_code: product?.sku_code ?? `商品#${item.product_id}`,
      location_code: location?.location_code ?? `库位#${item.location_id}`
    }
  })
  total.value = page.items.length
}

async function loadInbounds() {
  await loadReferenceData()
  const orders = await listInbounds()
  const details = await Promise.all(orders.items.map((order) => getInbound(order.inbound_order_id)))
  rows.value = orders.items.map((order, index) => {
    const item = details[index]?.items?.[0]
    const product = item ? productMap.value.get(item.product_id) : undefined
    const location = item ? locationMap.value.get(item.location_id) : undefined
    return {
      inbound_order_id: order.inbound_order_id,
      status_code: order.status,
      order_no: order.order_no,
      source_product_code: product?.source_product_code ?? (item ? `商品#${item.product_id}` : '-'),
      sku_code: product?.sku_code ?? '-',
      quantity: item?.quantity ?? 0,
      location_code: location?.location_code ?? (item ? `库位#${item.location_id}` : '-'),
      status: statusText(order.status),
      created_at: formatDateTime(order.created_at)
    }
  })
  total.value = orders.items.length
}

async function loadOutbounds() {
  await loadReferenceData()
  const orders = await listOutbounds()
  const details = await Promise.all(orders.items.map((order) => getOutbound(order.outbound_order_id)))
  rows.value = orders.items.map((order, index) => {
    const item = details[index]?.items?.[0]
    const product = item ? productMap.value.get(item.product_id) : undefined
    return {
      outbound_order_id: order.outbound_order_id,
      status_code: order.status,
      order_no: order.order_no,
      customer_id: order.customer_id ?? '-',
      source_product_code: product?.source_product_code ?? (item ? `商品#${item.product_id}` : '-'),
      quantity: item?.quantity ?? 0,
      allocated_quantity: item?.allocated_quantity ?? 0,
      status: statusText(order.status),
      created_at: formatDateTime(order.created_at)
    }
  })
  total.value = orders.items.length
}

async function loadPickingTasks() {
  await loadReferenceData()
  const tasks = await listPickingTasks()
  rows.value = tasks.items.map((item) => {
    const product = productMap.value.get(item.product_id)
    const location = locationMap.value.get(item.location_id)
    return {
      ...item,
      status_code: item.status,
      sku_code: product?.sku_code ?? `商品#${item.product_id}`,
      location_code: location?.location_code ?? `库位#${item.location_id}`,
      status: statusText(item.status),
      priority: '普通'
    }
  })
  total.value = tasks.items.length
}

async function loadImports() {
  const page = await listImports()
  rows.value = page.items.map((item) => ({ ...item, imported_at: formatDateTime(item.imported_at) }))
  total.value = page.total ?? page.items.length
}

async function loadAuditLogs() {
  const page = await listAuditLogs({ limit: 100 })
  rows.value = page.items.map((item) => ({ ...item, result: '成功', created_at: formatDateTime(item.created_at) }))
  total.value = page.items.length
}

async function loadAlerts() {
  await loadReferenceData()
  const page = await listAlerts({ threshold: 10 })
  rows.value = page.items.map((item) => {
    const product = productMap.value.get(item.product_id)
    const location = locationMap.value.get(item.location_id)
    return {
      ...item,
      alert_type: '低库存',
      sku_code: product?.sku_code ?? `商品#${item.product_id}`,
      location_code: location?.location_code ?? `库位#${item.location_id}`,
      threshold: page.threshold,
      status: '待处理'
    }
  })
  total.value = page.items.length
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    if (route.path === '/dashboard') {
      dashboardSummary.value = await getDashboardSummary()
      return
    }
    if (route.path === '/products') await loadProducts()
    else if (route.path === '/locations') await loadLocations()
    else if (route.path === '/inventory') await loadInventory()
    else if (route.path === '/inventory-ledger') await loadLedgers()
    else if (route.path === '/inbounds') await loadInbounds()
    else if (route.path === '/outbounds') await loadOutbounds()
    else if (route.path === '/picking') await loadPickingTasks()
    else if (route.path === '/imports') await loadImports()
    else if (route.path === '/audit') await loadAuditLogs()
    else if (route.path === '/alerts') await loadAlerts()
    else {
      rows.value = []
      total.value = 0
      errorMessage.value = '该页面暂无对应后端接口，后续版本将开放。'
    }
  } catch (error) {
    rows.value = []
    total.value = 0
    errorMessage.value = error instanceof Error ? error.message : '数据加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => route.path,
  async () => {
    rows.value = []
    total.value = 0
    keyword.value = ''
    currentPage.value = 1
    errorMessage.value = ''
    await loadData()
  },
  { immediate: true }
)

const search = () => {
  currentPage.value = 1
  loadData()
}
const reset = () => {
  keyword.value = ''
  currentPage.value = 1
  loadData()
}
const changePage = (page: number) => {
  currentPage.value = page
  loadData()
}
const openAction = async (action: string) => {
  if (action !== '新建入库单' && action !== '新建出库单') {
    ElMessage.info('请在具体业务记录中执行该操作；未开放接口的功能将在后续版本提供。')
    return
  }
  if (!referenceLoaded.value) await loadReferenceData()
  selectedAction.value = action
  dialogVisible.value = true
}

interface RowAction {
  label: string
  kind: 'inbound-confirm' | 'outbound-allocate' | 'outbound-complete' | 'picking-confirm'
}

const rowAction = (row: TableRow): RowAction | null => {
  if (route.path === '/inbounds' && row.status_code === 'draft') {
    return { label: '确认收货', kind: 'inbound-confirm' }
  }
  if (route.path === '/outbounds' && row.status_code === 'draft') {
    return { label: '分配库存', kind: 'outbound-allocate' }
  }
  if (route.path === '/outbounds' && row.status_code === 'allocated') {
    return { label: '完成出库', kind: 'outbound-complete' }
  }
  if (route.path === '/picking' && row.status_code === 'allocated') {
    return { label: '确认拣货', kind: 'picking-confirm' }
  }
  return null
}

const handleRowAction = async (row: TableRow) => {
  const action = rowAction(row)
  if (!action) return
  try {
    if (action.kind === 'inbound-confirm') await confirmInbound(Number(row.inbound_order_id))
    else if (action.kind === 'outbound-allocate') await allocateOutbound(Number(row.outbound_order_id))
    else if (action.kind === 'outbound-complete') await completeOutbound(Number(row.outbound_order_id))
    else if (action.kind === 'picking-confirm') await confirmPickingTask(Number(row.picking_task_id))
    ElMessage.success(`${action.label}成功`)
    await loadData()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : `${action.label}失败`)
  }
}

const submitAction = async (submission: OperationSubmission) => {
  dialogVisible.value = false
  try {
    if (submission.type === 'inbound') await createInbound(submission.payload)
    else await createOutbound(submission.payload)
    ElMessage.success('业务单已创建')
    await loadData()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '业务单创建失败')
  }
}
</script>

<template>
  <main class="workspace-page">
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" />

    <template v-if="config.kind === 'group'">
      <section class="module-hero">
        <div>
          <div class="eyebrow">模块功能导航</div>
          <h2>选择功能进入具体页面</h2>
          <p>核心业务页面已接入 FastAPI，可查看真实商品、库存和作业数据。</p>
        </div>
        <el-tag type="success" effect="plain">{{ config.children?.length ?? 0 }} 个功能</el-tag>
      </section>
      <el-card shadow="never" class="module-note"><el-icon><InfoFilled /></el-icon><span>请选择下面的功能进入具体页面。部分扩展流程仍会在后续版本开放接口。</span></el-card>
      <section class="module-grid"><el-card v-for="child in config.children" :key="child.path" shadow="never" class="module-card" @click="router.push(child.path)"><div class="module-icon">{{ child.icon }}</div><div class="module-card-content"><h3>{{ child.label }}</h3><p>{{ child.subtitle }}</p><span>进入功能 <el-icon><ArrowRight /></el-icon></span></div></el-card></section>
    </template>

    <template v-else-if="config.kind === 'dashboard'">
      <section class="stat-grid"><StatCard v-for="card in dashboardCards" :key="card.label" :label="card.label" :value="card.value" :hint="card.hint" :accent="card.accent" /></section>
      <section class="dashboard-grid">
        <el-card shadow="never" class="chart-card"><template #header><div class="card-title"><span>库存数量趋势</span><el-button text type="primary" @click="loadData">刷新</el-button></div></template><div class="chart-placeholder"><div class="chart-line" /><div class="chart-line line-two" /><div class="chart-line line-three" /><span>真实库存与作业指标已接入，趋势图将在下一版细化。</span></div></el-card>
        <el-card shadow="never" class="chart-card"><template #header><div class="card-title"><span>重点作业</span><el-tag type="success" effect="light">FastAPI 已接入</el-tag></div></template><EmptyDataState title="待处理作业" :description="`待入库 ${dashboardSummary?.inbound_draft ?? 0} 单 / 待出库 ${dashboardSummary?.outbound_pending ?? 0} 单`" /></el-card>
        <el-card shadow="never" class="wide-card"><template #header><div class="card-title"><span>库位库存热力分布</span><span class="card-caption">按库区 / 巷道 / 货架汇总</span></div></template><div class="heatmap-placeholder"><span v-for="i in 48" :key="i" /><div>库位结构数据已接入，热力图将在下一版细化。</div></div></el-card>
      </section>
    </template>

    <template v-else-if="config.kind === 'ai'">
      <section class="ai-grid"><el-card class="session-card" shadow="never"><template #header><div class="card-title"><span>会话列表</span><el-button type="primary" plain size="small" @click="openAction('新建会话')">新建会话</el-button></div></template><EmptyDataState title="暂无会话" description="AI 服务接入后，可保存库存查询和运营分析会话。" /></el-card><el-card class="conversation-card" shadow="never"><template #header><div class="card-title"><span>智能分析</span><el-tag effect="plain">LangGraph 待接入</el-tag></div></template><EmptyDataState :title="config.emptyTitle" :description="config.emptyDescription" /><div class="ask-box"><el-input type="textarea" :rows="2" disabled placeholder="例如：查询某商品在各库位的可用库存" /><el-button type="primary" @click="notify('AI 提问')">发送</el-button></div></el-card><el-card class="source-card" shadow="never"><template #header><div class="card-title">数据引用</div></template><EmptyDataState title="暂无引用" description="AI 响应将标注数据来源、查询时间和工具调用记录。" /></el-card></section>
    </template>

    <template v-else>
      <el-card shadow="never" class="table-card">
        <FilterPanel v-model="keyword" :filters="config.filters" @search="search" @reset="reset" />
        <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" />
        <div class="table-toolbar"><div><span class="table-title">{{ config.title }}列表</span><span class="table-count">共 {{ total }} 条</span></div><div class="action-buttons"><el-button v-for="action in config.actions" :key="action" :type="/新建|上传|生成/.test(action) ? 'primary' : 'default'" @click="openAction(action)">{{ action }}</el-button></div></div>
        <el-table v-loading="loading" :data="rows" class="data-table" height="390"><el-table-column v-for="column in config.columns" :key="column" :prop="getColumnField(column)" :label="column" min-width="150" /><el-table-column label="操作" fixed="right" width="150"><template #default="{ row }"><el-button v-if="rowAction(row)" data-testid="row-action" text type="primary" @click="handleRowAction(row)">{{ rowAction(row)?.label }}</el-button><el-button v-else text type="primary" disabled>查看</el-button></template></el-table-column><template #empty><EmptyDataState :title="config.emptyTitle" :description="emptyDescription" /></template></el-table>
        <div class="pagination"><span>支持服务端分页、筛选和排序</span><el-pagination background layout="prev, pager, next" :total="total" :page-size="pageSize" :current-page="currentPage" @current-change="changePage" /></div>
      </el-card>
    </template>

    <OperationDialog v-model="dialogVisible" :action="selectedAction" :page-title="config.title" :products="productOptions" :locations="locationOptions" @submit="submitAction" />
  </main>
</template>

<style scoped>
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; }.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }.dashboard-grid { display: grid; grid-template-columns: 1.45fr 1fr; gap: 16px; }.wide-card { grid-column: 1 / -1; }.card-title { display: flex; align-items: center; justify-content: space-between; font-weight: 700; font-size: 14px; }.card-caption { color: var(--muted); font-weight: 400; font-size: 12px; }.chart-placeholder { height: 245px; position: relative; overflow: hidden; display: grid; align-items: end; padding: 30px 25px; color: var(--muted); font-size: 12px; }.chart-placeholder::before { content: ''; position: absolute; inset: 22px 20px 45px; background: repeating-linear-gradient(to bottom, transparent 0, transparent 47px, #edf1f7 48px); }.chart-line { position: absolute; height: 76px; width: 56%; left: 12%; top: 75px; border-radius: 50%; border-top: 3px solid #8bb7ff; transform: rotate(-10deg); }.line-two { left: 36%; top: 100px; width: 41%; border-color: #b6cffc; transform: rotate(12deg); }.line-three { left: 55%; top: 61px; width: 25%; border-color: #5e94ef; transform: rotate(-40deg); }.chart-placeholder span { position: relative; z-index: 1; }.heatmap-placeholder { min-height: 190px; display: grid; grid-template-columns: repeat(12, 1fr); gap: 7px; position: relative; padding: 24px; }.heatmap-placeholder span { aspect-ratio: 1; border-radius: 5px; background: #edf3ff; }.heatmap-placeholder span:nth-child(3n) { background: #d5e5ff; }.heatmap-placeholder span:nth-child(5n) { background: #b6d1ff; }.heatmap-placeholder div { position: absolute; inset: 0; display: grid; place-items: center; color: var(--muted); background: rgba(255,255,255,.68); font-size: 13px; }.table-card { overflow: hidden; }.table-error { margin: 12px 16px 0; }.table-toolbar { display: flex; justify-content: space-between; gap: 18px; align-items: center; padding: 16px; }.table-title { font-weight: 700; }.table-count { margin-left: 9px; color: var(--muted); font-size: 12px; }.action-buttons { display: flex; gap: 8px; flex-wrap: wrap; justify-content: end; }.data-table { width: 100%; border-top: 1px solid var(--line); }.data-table :deep(.el-table__empty-block) { width: 100% !important; }.pagination { height: 58px; padding: 0 16px; color: var(--muted); font-size: 12px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--line); }.ai-grid { display: grid; grid-template-columns: 255px minmax(430px, 1fr) 280px; gap: 16px; }.ask-box { display: flex; align-items: end; gap: 10px; padding: 14px 0 0; border-top: 1px solid var(--line); }.ask-box :deep(.el-input) { flex: 1; }.module-hero { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 20px 22px; margin-bottom: 16px; background: linear-gradient(135deg, #f5f8ff, #ffffff); border: 1px solid var(--line); border-radius: 14px; }.module-hero h2 { margin: 0 0 7px; font-size: 18px; }.module-hero p { margin: 0; color: var(--muted); font-size: 13px; }.module-note { margin-bottom: 16px; color: var(--muted); }.module-note :deep(.el-card__body) { display: flex; align-items: center; gap: 9px; padding: 14px 18px; font-size: 13px; }.module-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }.module-card { cursor: pointer; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }.module-card:hover { transform: translateY(-3px); border-color: #91b8ff; box-shadow: 0 12px 28px rgba(37,95,203,.12); }.module-card :deep(.el-card__body) { display: flex; align-items: flex-start; gap: 15px; min-height: 138px; padding: 22px; }.module-icon { width: 42px; height: 42px; flex: 0 0 42px; display: grid; place-items: center; border-radius: 12px; color: var(--brand); background: #edf4ff; font-size: 21px; font-weight: 700; }.module-card-content { min-width: 0; }.module-card h3 { margin: 1px 0 8px; font-size: 16px; }.module-card p { min-height: 38px; margin: 0 0 13px; color: var(--muted); font-size: 12px; line-height: 1.7; }.module-card span { display: inline-flex; align-items: center; gap: 4px; color: var(--brand); font-size: 12px; font-weight: 700; }
@media (max-width: 1100px) { .stat-grid { grid-template-columns: repeat(2, 1fr); }.ai-grid { grid-template-columns: 1fr; }.dashboard-grid { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .module-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 700px) { .workspace-page { padding: 19px 15px; }.stat-grid { grid-template-columns: 1fr; }.table-toolbar, .pagination { align-items: flex-start; flex-direction: column; height: auto; padding: 14px; }.action-buttons { justify-content: start; }.module-grid { grid-template-columns: 1fr; }.module-hero { align-items: flex-start; flex-direction: column; } }
</style>
