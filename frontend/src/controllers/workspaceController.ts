/** 通用工作台：看板、库存、入出库、预警、导入等列表操作。 */
import { computed, ref, watch } from 'vue' // 引入 Vue 计算属性、ref 与侦听器
import { useRoute, useRouter } from 'vue-router' // 引入当前路由与跳转
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs, canPerformAction, visibleChildrenFor } from '../config/pages' // 页面配置与按钮/子入口权限
import { createLocation, createProduct, createWarehouse, listImports, listLocationMap, listLocations, listProducts, listWarehouses, updateLocation, updateProduct, uploadProductCsv, type Location, type LocationMapGroup, type Product, type Warehouse } from '../models/catalog' // 主数据与导入 API
import { // 库存、看板、预警、审计 API
  ackAlert, // 确认预警
  exportAuditCsv, // 导出审计
  exportInventoryCsv, // 导出库存
  exportLedgerCsv, // 导出流水
  getDashboardCharts, // 看板图表
  getDashboardSummary, // 看板汇总
  listAlerts, // 预警列表
  listAuditLogs, // 审计列表
  listBalances, // 库存余额
  listLedgers, // 库存流水
  type DashboardCharts, // 图表类型
  type DashboardSummary // 汇总类型
} from '../models/inventory' // 来自库存模型
import { // 入出库与拣货 API
  allocateOutbound, // 分配库存
  completeOutbound, // 完成出库
  confirmInbound, // 确认入库
  confirmPickingTask, // 确认拣货
  createInbound, // 新建入库
  createOutbound, // 新建出库
  getInbound, // 入库详情
  getOutbound, // 出库详情
  listInbounds, // 入库列表
  listOutbounds, // 出库列表
  listPickingTasks, // 拣货列表
  type OperationSubmission // 新建单据联合类型
} from '../models/operations' // 来自作业模型
import { ApiError } from '../models/client' // API 错误类型
import { useAppStore } from '../stores/app' // 登录态与助手草稿

export function useWorkspaceController() { // 通用工作台控制器
  type TableRow = Record<string, unknown> // 表格行用宽松字典

  const route = useRoute() // 当前路由
  const router = useRouter() // 路由器
  const app = useAppStore() // 应用仓库
  const config = computed(() => pageConfigs[route.path] ?? pageConfigs['/dashboard']) // 当前页配置，缺省看板

  const rows = ref<TableRow[]>([]) // 表格数据
  const total = ref(0) // 总条数
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const keyword = ref('') // 搜索关键字
  const currentPage = ref(1) // 当前页码
  const pageSize = 20 // 每页条数
  const inboundView = ref<'pending' | 'history'>('pending') // 入库待确认/历史
  const inboundTableRef = ref<{ toggleAllSelection?: () => void; clearSelection?: () => void } | null>(null) // 入库表格实例
  const selectedInbounds = ref<TableRow[]>([]) // 已勾选入库单
  const dashboardSummary = ref<DashboardSummary | null>(null) // 看板汇总
  const dashboardCharts = ref<DashboardCharts | null>(null) // 看板图表
  const dialogVisible = ref(false) // 入出库新建弹窗
  const catalogVisible = ref(false) // 主数据弹窗
  const catalogKind = ref<'product' | 'location' | 'warehouse'>('product') // 主数据弹窗种类
  const catalogSubmitting = ref(false) // 主数据提交中
  const editingProduct = ref<Product | null>(null) // 正在编辑的商品
  const editingLocation = ref<Location | null>(null) // 正在编辑的库位
  const selectedAction = ref('') // 当前工具栏动作
  const operationDraft = ref<import('../stores/app').OperationDraft | null>(null) // 助手单据草稿
  const locationMapVisible = ref(false) // 库位地图弹窗
  const locationMapLoading = ref(false) // 地图加载中
  const locationMapGroups = ref<LocationMapGroup[]>([]) // 地图分组
  const detailVisible = ref(false) // 行详情弹窗
  const detailRow = ref<TableRow | null>(null) // 详情行

  const productMap = ref(new Map<number, Product>()) // 商品 ID 映射
  const locationMap = ref(new Map<number, Location>()) // 库位 ID 映射
  const warehouseMap = ref(new Map<number, Warehouse>()) // 仓库 ID 映射
  const referenceLoaded = ref(false) // 主数据是否已缓存
  const productOptions = ref<Product[]>([]) // 商品下拉
  const locationOptions = ref<Location[]>([]) // 库位下拉

  const offset = computed(() => (currentPage.value - 1) * pageSize) // 分页偏移
  const emptyDescription = computed(() => // 空态文案
    loading.value ? '正在从 FastAPI 加载数据...' : errorMessage.value || config.value.emptyDescription // 加载中/错误/默认空态
  ) // 结束 emptyDescription

  const dashboardCards = computed(() => { // 看板统计卡
    const summary = dashboardSummary.value // 当前汇总
    return [ // 卡片列表
      { label: '库存总数量', value: summary?.stock_quantity ?? 0, hint: 'stock_balance 实际库存合计', accent: 'var(--brand)' }, // 总量
      { label: '锁定量', value: summary?.reserved_quantity ?? 0, hint: '已分配给出库单的库存', accent: '#6a8bf5' }, // 锁定
      { label: '可用量', value: summary?.available_quantity ?? 0, hint: '实际库存减去锁定量', accent: 'var(--success)' }, // 可用
      { // 待处理作业卡
        label: '待处理作业', // 标题
        value: (summary?.inbound_draft ?? 0) + (summary?.outbound_pending ?? 0), // 待入+待出
        hint: `待入库 ${summary?.inbound_draft ?? 0} / 待出库 ${summary?.outbound_pending ?? 0} / 待复核 ${summary?.pending_review ?? 0}`, // 明细提示
        accent: 'var(--warning)' // 警告色
      }, // 结束待处理卡
      { label: '待审批', value: summary?.pending_approvals ?? 0, hint: '盘点差异与调拨', accent: '#8b5cf6' }, // 审批
      { label: '低库存预警', value: summary?.low_stock_alerts ?? 0, hint: '可用量不超过阈值且未确认', accent: '#ef4444' } // 预警
    ] // 结束卡片数组
  }) // 结束 dashboardCards

  const columnFields: Record<string, Record<string, string>> = { // 列标题到字段名
    '/products': { // 商品列
      '系统 SKU': 'sku_code', '商品编码': 'source_product_code', '商品名称': 'product_name', // SKU/编码/名称
      '品牌': 'brand', '托盘容量': 'pallet_capacity', '状态': 'status' // 品牌/容量/状态
    }, // 结束商品列
    '/locations': { // 库位列
      '仓库编码': 'warehouse_code', '库位编码': 'location_code', '库区': 'zone_code', // 仓库/库位/库区
      '巷道': 'aisle_code', '货架': 'rack_code', '储位状态': 'status' // 巷道/货架/状态
    }, // 结束库位列
    '/inventory': { // 库存列
      '系统 SKU': 'sku_code', '商品编码': 'source_product_code', '库位编码': 'location_code', // SKU/编码/库位
      '实际库存数量': 'quantity', '可用量': 'available_quantity', '锁定量': 'reserved_quantity', // 数量
      '冻结量': 'frozen_quantity', '最后更新时间': 'updated_at' // 冻结与时间
    }, // 结束库存列
    '/inventory-ledger': { // 流水列
      '流水号': 'ledger_id', '系统 SKU': 'sku_code', '库位编码': 'location_code', // 编号/SKU/库位
      '业务类型': 'transaction_type', '变动方向': 'direction', '变动数量': 'quantity_delta', '变动前数量': 'before_quantity', // 变动
      '变动后数量': 'after_quantity', '发生时间': 'created_at' // 变动后与时间
    }, // 结束流水列
    '/inbounds': { // 入库列
      '入库单号': 'order_no', '商品编码': 'source_product_code', '系统 SKU': 'sku_code', // 单号/编码/SKU
      '收货数量': 'quantity', '收货库位': 'location_code', '单据状态': 'status', '账户名': 'username', '创建时间': 'created_at' // 数量与状态
    }, // 结束入库列
    '/outbounds': { // 出库列
      '出库单号': 'order_no', '客户编号': 'customer_id', '商品编码': 'source_product_code', // 单号/客户/编码
      '需求数量': 'quantity', '分配数量': 'allocated_quantity', '单据状态': 'status', '创建时间': 'created_at' // 数量与状态
    }, // 结束出库列
    '/picking': { // 拣货列
      '任务号': 'task_no', '出库单号': 'outbound_order_id', '库位编码': 'location_code', // 任务/出库单/库位
      '系统 SKU': 'sku_code', '拣货数量': 'quantity', '任务状态': 'status', '优先级': 'priority' // SKU/数量/状态
    }, // 结束拣货列
    '/imports': { // 导入列
      '批次号': 'batch_no', '文件名称': 'dataset_name', '数据类型': 'dataset_name', // 批次与文件
      '导入行数': 'total_rows', '成功行数': 'valid_rows', '失败行数': 'invalid_rows', // 行数
      '导入状态': 'status', '导入时间': 'imported_at' // 状态与时间
    }, // 结束导入列
    '/audit': { // 审计列
      '审计编号': 'audit_log_id', '账户名': 'username', '操作类型': 'action', // 编号/用户/操作
      '业务对象': 'entity_type', '业务单号': 'entity_id', '操作结果': 'result', '操作时间': 'created_at' // 对象与结果
    }, // 结束审计列
    '/alerts': { // 预警列
      '预警编号': 'balance_id', '预警类型': 'alert_type', '系统 SKU': 'sku_code', // 编号/类型/SKU
      '库位编码': 'location_code', '当前数量': 'quantity', '预警阈值': 'threshold', // 库位与数量
      '处理状态': 'status', '产生时间': 'created_at' // 状态与时间
    } // 结束预警列
  } // 结束 columnFields

  const getColumnField = (column: string) => columnFields[route.path]?.[column] ?? column // 列标题映射字段，缺省用标题本身

  const statusLabels: Record<string, string> = { // 单据状态中文
    draft: '草稿', confirmed: '已确认', allocated: '已分配', picked: '已拣货', reviewed: '已复核', completed: '已完成', pending: '待处理', acked: '已处理' // 状态字典
  } // 结束 statusLabels
  const statusText = (status: string) => statusLabels[status] ?? status // 未知状态原样返回
  const ledgerTypeLabels: Record<string, string> = { // 流水业务类型中文
    inbound: '入库', // 入库
    outbound: '出库', // 出库
    count_gain: '盘盈', // 盘盈
    count_loss: '盘亏', // 盘亏
    transfer_in: '调拨入库', // 调入
    transfer_out: '调拨出库' // 调出
  } // 结束 ledgerTypeLabels
  const ledgerDirection = (type: string, delta: number) => { // 流水方向
    if (type === 'inbound' || type === 'transfer_in' || type === 'count_gain') return '入库' // 增加类
    if (type === 'outbound' || type === 'transfer_out' || type === 'count_loss') return '出库' // 减少类
    return delta >= 0 ? '入库' : '出库' // 其余按数量正负
  } // 结束 ledgerDirection
  const formatDateTime = (value?: string | null) => // 格式化时间
    value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-' // 空值显示横杠

  async function loadReferenceData() { // 缓存商品/库位/仓库
    if (referenceLoaded.value) return // 已加载则跳过
    const [productPage, locationPage, warehousePage] = await Promise.all([ // 并行拉取
      listProducts({ limit: 200 }), // 商品
      listLocations({ limit: 200 }), // 库位
      listWarehouses() // 仓库
    ]) // 结束 Promise.all
    productMap.value = new Map(productPage.items.map((item) => [item.product_id, item])) // 建商品映射
    locationMap.value = new Map(locationPage.items.map((item) => [item.location_id, item])) // 建库位映射
    warehouseMap.value = new Map(warehousePage.items.map((item) => [item.warehouse_id, item])) // 建仓库映射
    productOptions.value = productPage.items // 下拉商品
    locationOptions.value = locationPage.items // 下拉库位
    referenceLoaded.value = true // 标记已加载
  } // 结束 loadReferenceData

  async function loadProducts() { // 加载商品表
    const page = await listProducts({ // 查询商品
      keyword: keyword.value.trim() || undefined, // 关键字
      offset: offset.value, // 偏移
      limit: pageSize // 条数
    }) // 结束 listProducts
    rows.value = page.items.map((item) => ({ ...item, status: item.is_active === false ? '停用' : '启用' })) // 附加状态文案
    total.value = page.total ?? page.items.length // 总条数
  } // 结束 loadProducts

  async function loadLocations() { // 加载库位表
    await loadReferenceData() // 先有仓库映射
    const page = await listLocations({ keyword: keyword.value.trim() || undefined, offset: offset.value, limit: pageSize }) // 查询库位
    rows.value = page.items.map((item) => ({ // 展平展示字段
      ...item, // 原始库位
      warehouse_code: warehouseMap.value.get(item.warehouse_id)?.warehouse_code ?? `仓库#${item.warehouse_id}`, // 仓库编码
      status: item.is_active === false ? '停用' : '可用' // 状态文案
    })) // 结束 map
    total.value = page.total ?? page.items.length // 总条数
  } // 结束 loadLocations

  async function loadInventory() { // 加载库存余额
    await loadReferenceData() // 先有主数据
    const page = await listBalances({ keyword: keyword.value.trim() || undefined, offset: offset.value, limit: pageSize }) // 查询余额
    rows.value = page.items.map((item) => { // 补 SKU/库位
      const product = productMap.value.get(item.product_id) // 查商品
      const location = locationMap.value.get(item.location_id) // 查库位
      return { // 展示行
        ...item, // 原始余额
        sku_code: product?.sku_code ?? item.sku_code ?? `商品#${item.product_id}`, // SKU
        source_product_code: product?.source_product_code ?? item.source_product_code ?? '-', // 来源编码
        location_code: location?.location_code ?? item.location_code ?? `库位#${item.location_id}`, // 库位
        frozen_quantity: item.frozen_quantity ?? 0, // 冻结量默认 0
        updated_at: formatDateTime(item.updated_at) // 格式化时间
      } // 结束 return
    }) // 结束 map
    total.value = page.total ?? page.items.length // 总条数
  } // 结束 loadInventory

  async function loadLedgers() { // 加载库存流水
    await loadReferenceData() // 先有主数据
    const page = await listLedgers({ keyword: keyword.value.trim() || undefined, limit: 100 }) // 查询流水
    rows.value = page.items.map((item) => { // 补展示字段
      const product = productMap.value.get(item.product_id) // 查商品
      const location = locationMap.value.get(item.location_id) // 查库位
      return { // 展示行
        ...item, // 原始流水
        created_at: formatDateTime(item.created_at), // 格式化时间
        sku_code: product?.sku_code ?? `商品#${item.product_id}`, // SKU
        location_code: location?.location_code ?? `库位#${item.location_id}`, // 库位
        transaction_type: ledgerTypeLabels[item.transaction_type] ?? item.transaction_type, // 类型中文
        direction: ledgerDirection(item.transaction_type, item.quantity_delta) // 方向
      } // 结束 return
    }) // 结束 map
    total.value = page.items.length // 流水接口无 total 用长度
  } // 结束 loadLedgers

  async function loadInbounds() { // 加载入库单（展平首条明细）
    await loadReferenceData() // 先有主数据
    selectedInbounds.value = [] // 切换数据时清空勾选
    const orders = await listInbounds({ // 查询入库单
      keyword: keyword.value.trim() || undefined, // 关键字
      status: inboundView.value === 'history' ? 'confirmed' : 'draft' // 历史看已确认
    }) // 结束 listInbounds
    const details = await Promise.all(orders.items.map((order) => getInbound(order.inbound_order_id))) // 并行拉明细
    rows.value = orders.items.map((order, index) => { // 展平第一行明细
      const item = details[index]?.items?.[0] // 首条明细
      const product = item ? productMap.value.get(item.product_id) : undefined // 商品
      const location = item ? locationMap.value.get(item.location_id) : undefined // 库位
      return { // 展示行
        inbound_order_id: order.inbound_order_id, // 入库单 ID
        status_code: order.status, // 原始状态码
        order_no: order.order_no, // 单号
        source_product_code: product?.source_product_code ?? (item ? `商品#${item.product_id}` : '-'), // 商品编码
        sku_code: product?.sku_code ?? '-', // SKU
        quantity: item?.quantity ?? 0, // 数量
        location_code: location?.location_code ?? (item ? `库位#${item.location_id}` : '-'), // 库位
        status: statusText(order.status), // 状态中文
        username: order.username ?? '-', // 创建人
        created_at: formatDateTime(order.created_at) // 创建时间
      } // 结束 return
    }) // 结束 map
    total.value = orders.items.length // 当前结果条数
  } // 结束 loadInbounds

  async function loadOutbounds() { // 加载出库单（展平首条明细）
    await loadReferenceData() // 先有主数据
    const orders = await listOutbounds({ keyword: keyword.value.trim() || undefined }) // 查询出库单
    const details = await Promise.all(orders.items.map((order) => getOutbound(order.outbound_order_id))) // 并行拉明细
    rows.value = orders.items.map((order, index) => { // 展平第一行明细
      const item = details[index]?.items?.[0] // 首条明细
      const product = item ? productMap.value.get(item.product_id) : undefined // 商品
      return { // 展示行
        outbound_order_id: order.outbound_order_id, // 出库单 ID
        status_code: order.status, // 原始状态码
        order_no: order.order_no, // 单号
        customer_id: order.customer_id ?? '-', // 客户
        source_product_code: product?.source_product_code ?? (item ? `商品#${item.product_id}` : '-'), // 商品编码
        quantity: item?.quantity ?? 0, // 需求数量
        allocated_quantity: item?.allocated_quantity ?? 0, // 已分配
        status: statusText(order.status), // 状态中文
        created_at: formatDateTime(order.created_at) // 创建时间
      } // 结束 return
    }) // 结束 map
    total.value = orders.items.length // 当前结果条数
  } // 结束 loadOutbounds

  async function loadPickingTasks() { // 加载拣货任务
    await loadReferenceData() // 先有主数据
    const tasks = await listPickingTasks({ keyword: keyword.value.trim() || undefined }) // 查询任务
    rows.value = tasks.items.map((item) => { // 补 SKU/库位
      const product = productMap.value.get(item.product_id) // 商品
      const location = locationMap.value.get(item.location_id) // 库位
      return { // 展示行
        ...item, // 原始任务
        status_code: item.status, // 原始状态码
        sku_code: product?.sku_code ?? `商品#${item.product_id}`, // SKU
        location_code: location?.location_code ?? `库位#${item.location_id}`, // 库位
        status: statusText(item.status), // 状态中文
        priority: '普通' // 前端固定优先级展示
      } // 结束 return
    }) // 结束 map
    total.value = tasks.items.length // 条数
  } // 结束 loadPickingTasks

  async function loadImports() { // 加载导入批次
    const page = await listImports({ keyword: keyword.value.trim() || undefined }) // 查询批次
    rows.value = page.items.map((item) => ({ ...item, imported_at: formatDateTime(item.imported_at) })) // 格式化时间
    total.value = page.total ?? page.items.length // 总条数
  } // 结束 loadImports

  async function loadAuditLogs() { // 加载审计
    const page = await listAuditLogs({ keyword: keyword.value.trim() || undefined, limit: 100 }) // 查询审计
    rows.value = page.items.map((item) => ({ // 补展示字段
      ...item, // 原始审计
      username: item.username ?? '-', // 账户名
      result: '成功', // 列表默认成功
      created_at: formatDateTime(item.created_at) // 格式化时间
    })) // 结束 map
    total.value = page.items.length // 条数
  } // 结束 loadAuditLogs

  async function loadAlerts() { // 加载预警
    await loadReferenceData() // 先有主数据
    const page = await listAlerts({ threshold: 10, keyword: keyword.value.trim() || undefined, offset: offset.value, limit: pageSize }) // 查询预警
    rows.value = page.items.map((item) => { // 补类型与编码
      const product = productMap.value.get(item.product_id) // 商品
      const location = locationMap.value.get(item.location_id) // 库位
      return { // 展示行
        ...item, // 原始预警
        alert_type: item.alert_type === 'stale_stock' ? '呆滞库存' : (item.alert_type === 'low_stock' ? '低库存' : (item.alert_type ?? '低库存')), // 类型中文
        sku_code: product?.sku_code ?? item.sku_code ?? `商品#${item.product_id}`, // SKU
        location_code: location?.location_code ?? item.location_code ?? `库位#${item.location_id}`, // 库位
        threshold: page.threshold, // 当前阈值
        status: statusText(item.status ?? 'pending'), // 状态中文
        status_code: item.status ?? 'pending', // 原始状态码
        created_at: formatDateTime(item.created_at) // 产生时间
      } // 结束 return
    }) // 结束 map
    total.value = page.total ?? page.items.length // 总条数
  } // 结束 loadAlerts

  async function loadData() { // 按当前路径分发加载
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 按路由加载
      if (route.path === '/dashboard') { // 看板
        dashboardSummary.value = await getDashboardSummary() // 拉汇总
        dashboardCharts.value = await getDashboardCharts() // 拉图表
        return // 看板不走表格
      } // 结束看板分支
      if (route.path === '/products') await loadProducts() // 商品
      else if (route.path === '/locations') await loadLocations() // 库位
      else if (route.path === '/inventory') await loadInventory() // 库存
      else if (route.path === '/inventory-ledger') await loadLedgers() // 流水
      else if (route.path === '/inbounds') await loadInbounds() // 入库
      else if (route.path === '/outbounds') await loadOutbounds() // 出库
      else if (route.path === '/picking') await loadPickingTasks() // 拣货
      else if (route.path === '/imports') await loadImports() // 导入
      else if (route.path === '/audit') await loadAuditLogs() // 审计
      else if (route.path === '/alerts') await loadAlerts() // 预警
      else { // 未接接口的页面
        rows.value = [] // 清空表格
        total.value = 0 // 清总条数
        errorMessage.value = '该页面暂无对应后端接口，后续版本将开放。' // 占位提示
      } // 结束未接接口分支
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      total.value = 0 // 清总条数
      errorMessage.value = error instanceof Error ? error.message : '数据加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const applyPendingDraft = async () => { // 消费助手入出库草稿
    const draft = app.pendingDraft // 读取草稿
    if (!draft || draft.type === 'counting') return // 无草稿或盘点草稿交给盘点页
    const target = draft.type === 'outbound' ? '/outbounds' : '/inbounds' // 目标业务页
    if (route.path !== target) return // 不在目标页则等跳转后再消费
    if (!referenceLoaded.value) await loadReferenceData() // 确保下拉有数据
    operationDraft.value = app.consumePendingDraft() // 消费并交给弹窗
    selectedAction.value = draft.type === 'outbound' ? '新建出库单' : '新建入库单' // 对应动作
    dialogVisible.value = true // 打开新建弹窗
  } // 结束 applyPendingDraft

  watch( // 路由或关键字变化时重载
    () => [route.path, route.query.keyword] as const, // 监听路径和 query.keyword
    async () => { // 变化后重置并加载
      rows.value = [] // 清空表格
      total.value = 0 // 清总条数
      keyword.value = typeof route.query.keyword === 'string' ? route.query.keyword : '' // 同步 URL 关键字
      currentPage.value = 1 // 回到第一页
      inboundView.value = 'pending' // 入库视图回到待确认
      selectedInbounds.value = [] // 清空勾选
      errorMessage.value = '' // 清空错误
      await loadData() // 加载当前页
      await applyPendingDraft() // 尝试打开助手草稿
    }, // 结束回调
    { immediate: true } // 进入页面立即执行
  ) // 结束 watch 路由

  const search = () => { // 搜索
    currentPage.value = 1 // 回到第一页
    loadData() // 重新加载
  } // 结束 search
  const reset = () => { // 重置筛选
    keyword.value = '' // 清空关键字
    currentPage.value = 1 // 回到第一页
    loadData() // 重新加载
  } // 结束 reset
  const changePage = (page: number) => { // 翻页
    currentPage.value = page // 更新页码
    loadData() // 重新加载
  } // 结束 changePage
  const printPickingList = () => { // 打印拣货单
    const lines = rows.value.map((row) => // 生成表格行 HTML
      `<tr><td>${row.task_no ?? ''}</td><td>${row.outbound_order_id ?? ''}</td><td>${row.location_code ?? ''}</td><td>${row.sku_code ?? ''}</td><td>${row.quantity ?? ''}</td><td>${row.status ?? ''}</td></tr>` // 任务字段
    ) // 结束 map
    const html = `<!doctype html><html><head><title>拣货单</title><style>body{font-family:sans-serif;padding:24px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #d7deea;padding:8px;font-size:12px;text-align:left}th{background:#f5f7fb}</style></head><body><h1>拣货任务</h1><table><thead><tr><th>任务号</th><th>出库单</th><th>库位</th><th>SKU</th><th>数量</th><th>状态</th></tr></thead><tbody>${lines.join('')}</tbody></table></body></html>` // 打印页 HTML
    const popup = window.open('', '_blank') // 打开打印窗口
    if (!popup) { // 弹窗被拦
      ElMessage.warning('浏览器拦截了打印窗口，请允许弹窗后重试。') // 提示允许弹窗
      return // 中止打印
    } // 结束拦截分支
    popup.document.write(html) // 写入打印内容
    popup.document.close() // 结束写入
    popup.focus() // 聚焦窗口
    popup.print() // 调起打印
  } // 结束 printPickingList

  const openAction = async (action: string) => { // 工具栏按钮分发
    if (action === '刷新看板') { // 刷新看板
      await loadData() // 重拉看板数据
      return // 结束
    } // 结束刷新看板
    if (action === '导出库存') { // 导出库存
      await exportInventoryCsv() // 下载 CSV
      return // 结束
    } // 结束导出库存
    if (action === '导出流水') { // 导出流水
      await exportLedgerCsv() // 下载 CSV
      return // 结束
    } // 结束导出流水
    if (action === '导出审计记录') { // 导出审计
      await exportAuditCsv() // 下载 CSV
      return // 结束
    } // 结束导出审计
    if (action === '导出运营摘要') { // 看板导出用库存 CSV
      await exportInventoryCsv() // 下载库存文件
      return // 结束
    } // 结束导出摘要
    if (action === '新建商品' || action === '新建库位' || action === '新建仓库') { // 主数据新建
      if (!referenceLoaded.value) await loadReferenceData() // 确保下拉有数据
      catalogKind.value = action === '新建商品' ? 'product' : action === '新建仓库' ? 'warehouse' : 'location' // 弹窗种类
      editingProduct.value = null // 非编辑商品
      editingLocation.value = null // 非编辑库位
      catalogVisible.value = true // 打开主数据弹窗
      return // 结束
    } // 结束主数据新建
    if (action === '上传商品CSV') { // 选择 CSV 上传
      const input = document.createElement('input') // 隐藏 file input
      input.type = 'file' // 文件类型
      input.accept = '.csv,text/csv' // 仅 CSV
      input.onchange = async () => { // 选文件后上传
        const file = input.files?.[0] // 第一个文件
        if (!file) return // 未选则退出
        try { // 调用导入
          const batch = await uploadProductCsv(file) // 上传
          ElMessage.success(`已导入 ${batch.valid_rows} 行，失败 ${batch.invalid_rows} 行`) // 结果提示
          await loadData() // 刷新当前页
        } catch (error) { // 导入失败
          ElMessage.error(error instanceof ApiError ? error.message : '导入失败') // 错误提示
        } // 结束 catch
      } // 结束 onchange
      input.click() // 弹出文件选择
      return // 结束
    } // 结束上传 CSV
    if (action === '查看导入批次' || action === '查看错误明细' || action === '查看明细') { // 导入相关跳转
      if (action === '查看导入批次') { // 去导入列表
        await router.push('/imports') // 跳转导入页
        return // 结束
      } // 结束查看批次
      ElMessage.info('请在导入批次行中查看明细。当前导入批次只读，不支持上传或重新校验。') // 行内查看提示
      return // 结束
    } // 结束导入查看
    if (action === '库位信息' || action === '查看库位地图') { // 打开库位地图
      locationMapVisible.value = true // 显示弹窗
      locationMapLoading.value = true // 开始加载
      try { // 拉地图
        const page = await listLocationMap() // 查询分组
        locationMapGroups.value = page.items // 写入分组
      } catch (error) { // 加载失败
        locationMapGroups.value = [] // 清空
        ElMessage.error(error instanceof Error ? error.message : '库位信息加载失败') // 错误提示
      } finally { // 无论成败
        locationMapLoading.value = false // 结束加载
      } // 结束 finally
      return // 结束
    } // 结束库位地图
    if (action === '库存调整申请') { // 调整走盘点
      await router.push('/counting') // 跳转盘点页
      return // 结束
    } // 结束库存调整
    if (action === '收货确认') { // 批量确认入库
      await confirmSelectedInbounds() // 确认已勾选
      return // 结束
    } // 结束收货确认
    if (action === '去拣货任务') { // 去拣货页
      await router.push('/picking') // 跳转拣货
      return // 结束
    } // 结束去拣货
    if (action === '去出库单分配') { // 引导去出库单分配
      ElMessage.info('请在出库单草稿行点击「分配库存」，分配后会生成拣货任务。') // 操作说明
      await router.push('/outbounds') // 跳出库单
      return // 结束
    } // 结束去分配
    if (action === '打印拣货单') { // 打印
      if (!rows.value.length) { // 无任务
        ElMessage.info('当前没有可打印的拣货任务。') // 提示
        return // 结束
      } // 结束空列表
      printPickingList() // 打开打印
      return // 结束
    } // 结束打印
    if (action === '生成补货草稿') { // 用预警生成入库草稿
      const page = await listAlerts({ threshold: 10, limit: 20 }) // 拉预警
      const pending = page.items.filter((item) => item.status !== 'acked').slice(0, 5) // 未处理前 5 条
      if (!pending.length) { // 没有可生成项
        ElMessage.info('当前没有待处理的低库存预警，无法生成补货草稿。') // 提示
        return // 结束
      } // 结束无预警
      app.setPendingDraft({ // 写入入库草稿
        type: 'inbound', // 入库类型
        items: pending.map((item) => ({ // 按预警补数量
          sku_code: item.sku_code ?? null, // SKU
          location_code: item.location_code ?? null, // 库位
          quantity: Math.max(1, Number(item.threshold ?? 10) - Number(item.available_quantity ?? item.quantity ?? 0)) // 补到阈值至少 1
        })) // 结束 items
      }) // 结束 setPendingDraft
      ElMessage.success('已生成入库补货草稿，请人工确认后保存。') // 提示核对
      await router.push('/inbounds') // 跳转入库页消费草稿
      return // 结束
    } // 结束补货草稿
    if (action !== '新建入库单' && action !== '新建出库单') { // 其余按钮需在行上操作
      ElMessage.info('请在具体业务记录中执行该操作。') // 提示点行操作
      return // 结束
    } // 结束未知动作
    if (!referenceLoaded.value) await loadReferenceData() // 确保下拉有数据
    operationDraft.value = null // 非助手草稿
    selectedAction.value = action // 记录动作
    dialogVisible.value = true // 打开新建弹窗
  } // 结束 openAction

  interface RowAction { // 行操作描述
    label: string // 按钮文案
    kind: 'inbound-confirm' | 'outbound-allocate' | 'outbound-complete' | 'picking-confirm' | 'goto-review' | 'alert-ack' | 'edit-product' | 'edit-location' | 'import-detail' | 'view-detail' // 动作种类
  } // 结束 RowAction

  const rowAction = (row: TableRow): RowAction | null => { // 根据页面与状态决定行按钮
    if (route.path === '/products') { // 商品行
      return { label: '编辑', kind: 'edit-product' } // 编辑商品
    } // 结束商品
    if (route.path === '/locations') { // 库位行
      return { label: '编辑', kind: 'edit-location' } // 编辑库位
    } // 结束库位
    if (route.path === '/imports') { // 导入行
      return { label: '查看明细', kind: 'import-detail' } // 去批次详情
    } // 结束导入
    if (route.path === '/inbounds') { // 入库行
      return inboundView.value === 'history' ? { label: '查看', kind: 'view-detail' } : null // 历史可查看，待确认用勾选
    } // 结束入库
    if (route.path === '/outbounds' && row.status_code === 'draft') { // 出库草稿
      return { label: '分配库存', kind: 'outbound-allocate' } // 分配
    } // 结束分配
    if (route.path === '/outbounds' && row.status_code === 'picked') { // 已拣货
      return { label: '去复核', kind: 'goto-review' } // 去复核页
    } // 结束去复核
    if (route.path === '/outbounds' && row.status_code === 'reviewed') { // 已复核
      return { label: '完成出库', kind: 'outbound-complete' } // 完成扣账
    } // 结束完成出库
    if (route.path === '/picking' && row.status_code === 'allocated') { // 待拣货
      return { label: '确认拣货', kind: 'picking-confirm' } // 确认拣货
    } // 结束确认拣货
    if (route.path === '/alerts' && row.status_code !== 'acked') { // 未处理预警
      return { label: '标记已处理', kind: 'alert-ack' } // 确认预警
    } // 结束预警
    return { label: '查看', kind: 'view-detail' } // 默认查看详情
  } // 结束 rowAction

  const handleRowAction = async (row: TableRow) => { // 执行行操作
    const action = rowAction(row) // 解析动作
    if (!action) return // 无按钮则退出
    try { // 按 kind 分发
      if (action.kind === 'outbound-allocate') await allocateOutbound(Number(row.outbound_order_id)) // 分配库存
      else if (action.kind === 'outbound-complete') await completeOutbound(Number(row.outbound_order_id)) // 完成出库
      else if (action.kind === 'picking-confirm') await confirmPickingTask(Number(row.picking_task_id)) // 确认拣货
      else if (action.kind === 'goto-review') { // 去复核
        await router.push('/outbound-review') // 跳转复核页
        return // 不刷新当前表
      } // 结束去复核
      else if (action.kind === 'alert-ack') await ackAlert(Number(row.balance_id), '已处理') // 确认预警
      else if (action.kind === 'edit-product') { // 编辑商品
        if (!referenceLoaded.value) await loadReferenceData() // 确保主数据
        catalogKind.value = 'product' // 商品弹窗
        editingProduct.value = row as unknown as Product // 回填商品
        editingLocation.value = null // 清库位编辑
        catalogVisible.value = true // 打开弹窗
        return // 结束
      } // 结束编辑商品
      else if (action.kind === 'edit-location') { // 编辑库位
        if (!referenceLoaded.value) await loadReferenceData() // 确保主数据
        catalogKind.value = 'location' // 库位弹窗
        editingLocation.value = row as unknown as Location // 回填库位
        editingProduct.value = null // 清商品编辑
        catalogVisible.value = true // 打开弹窗
        return // 结束
      } // 结束编辑库位
      else if (action.kind === 'import-detail') { // 导入明细
        await router.push(`/imports/${row.batch_id}`) // 跳转批次详情
        return // 结束
      } // 结束导入明细
      else if (action.kind === 'view-detail') { // 行详情
        detailRow.value = row // 记住行
        detailVisible.value = true // 打开详情
        return // 结束
      } // 结束查看详情
      ElMessage.success(`${action.label}成功`) // 接口类动作成功提示
      await loadData() // 刷新表格
    } catch (error) { // 操作失败
      ElMessage.error(error instanceof ApiError ? error.message : `${action.label}失败`) // 错误提示
    } // 结束 catch
  } // 结束 handleRowAction

  const visibleActions = computed(() => { // 按角色过滤工具栏
    const roles = app.currentUser?.roles ?? [] // 当前角色
    let actions = config.value.actions.filter((action) => canPerformAction(action, roles)) // 权限过滤
    if (route.path === '/inbounds' && inboundView.value === 'history') { // 入库历史不显示收货确认
      actions = actions.filter((action) => action !== '收货确认') // 去掉确认按钮
    } // 结束历史视图
    return actions // 可见按钮
  }) // 结束 visibleActions
  const visibleChildren = computed(() => visibleChildrenFor(route.path, app.currentUser?.roles ?? [])) // 分组页子入口
  const inboundAllSelected = computed( // 入库是否全选
    () => rows.value.length > 0 && selectedInbounds.value.length === rows.value.length // 有数据且勾选数等于行数
  ) // 结束 inboundAllSelected
  const inboundIndeterminate = computed( // 入库半选
    () => selectedInbounds.value.length > 0 && selectedInbounds.value.length < rows.value.length // 部分勾选
  ) // 结束 inboundIndeterminate
  const switchInboundView = (view: 'pending' | 'history') => { // 切换入库视图
    inboundView.value = view // 更新视图
    selectedInbounds.value = [] // 清空勾选
    currentPage.value = 1 // 回到第一页
    loadData() // 重新加载
  } // 结束 switchInboundView
  const onInboundSelection = (selection: TableRow[]) => { // 表格勾选变化
    selectedInbounds.value = selection // 同步已选
  } // 结束 onInboundSelection
  const toggleInboundSelectAll = (checked: boolean) => { // 表头全选
    selectedInbounds.value = checked ? [...rows.value] : [] // 全选或清空
    const table = inboundTableRef.value as { toggleRowSelection?: (row: TableRow, selected: boolean) => void; clearSelection?: () => void } | null // 表格 API
    if (!checked) { // 取消全选
      table?.clearSelection?.() // 清表格选中
      return // 结束
    } // 结束取消
    rows.value.forEach((row) => table?.toggleRowSelection?.(row, true)) // 逐行选中
  } // 结束 toggleInboundSelectAll
  const confirmSelectedInbounds = async () => { // 批量确认入库
    if (!selectedInbounds.value.length) { // 未勾选
      ElMessage.info('请先勾选需要收货确认的入库单。') // 提示勾选
      return // 结束
    } // 结束未勾选
    try { // 逐单确认
      for (const row of selectedInbounds.value) { // 遍历已选
        await confirmInbound(Number(row.inbound_order_id)) // 确认过账
      } // 结束 for
      ElMessage.success(`已确认 ${selectedInbounds.value.length} 张入库单，记录已写入历史。`) // 成功提示
      await loadData() // 刷新
    } catch (error) { // 中途失败
      ElMessage.error(error instanceof ApiError ? error.message : '收货确认失败') // 错误提示
      await loadData() // 仍刷新以同步状态
    } // 结束 catch
  } // 结束 confirmSelectedInbounds

  const submitCatalog = async (payload: Record<string, string | number | boolean>) => { // 保存主数据弹窗
    catalogSubmitting.value = true // 开始提交
    try { // 按种类保存
      if (catalogKind.value === 'product') { // 商品
        if (editingProduct.value) await updateProduct(editingProduct.value.product_id, payload as never) // 更新
        else await createProduct(payload as never) // 新建
      } else if (catalogKind.value === 'warehouse') { // 仓库
        await createWarehouse({ // 新建仓库
          warehouse_code: String(payload.warehouse_code ?? ''), // 仓库编码
          warehouse_name: String(payload.warehouse_name ?? '') // 仓库名称
        }) // 结束 createWarehouse
      } else if (editingLocation.value) { // 编辑库位
        await updateLocation(editingLocation.value.location_id, payload as never) // 更新库位
      } else { // 新建库位
        await createLocation(payload as never) // 创建库位
      } // 结束种类分支
      catalogVisible.value = false // 关闭弹窗
      editingProduct.value = null // 清商品编辑
      editingLocation.value = null // 清库位编辑
      referenceLoaded.value = false // 使主数据缓存失效
      ElMessage.success('基础资料已保存') // 成功提示
      await loadData() // 刷新当前表
    } catch (error) { // 保存失败
      ElMessage.error(error instanceof ApiError ? error.message : '保存失败') // 错误提示
    } finally { // 无论成败
      catalogSubmitting.value = false // 结束提交
    } // 结束 finally
  } // 结束 submitCatalog

  const submitAction = async (submission: OperationSubmission) => { // 保存入出库新建弹窗
    dialogVisible.value = false // 先关弹窗
    operationDraft.value = null // 清草稿
    try { // 按类型创建
      if (submission.type === 'inbound') await createInbound(submission.payload) // 新建入库
      else await createOutbound(submission.payload) // 新建出库
      ElMessage.success('业务单已创建') // 成功提示
      await loadData() // 刷新
    } catch (error) { // 创建失败
      ElMessage.error(error instanceof ApiError ? error.message : '业务单创建失败') // 错误提示
    } // 结束 catch
  } // 结束 submitAction

  return { // 暴露给视图
    route, // 路由
    router, // 路由器
    app, // 应用仓库
    config, // 页面配置
    rows, // 表格行
    total, // 总条数
    loading, // 加载状态
    errorMessage, // 错误信息
    keyword, // 关键字
    currentPage, // 页码
    pageSize, // 每页条数
    inboundView, // 入库视图
    inboundTableRef, // 入库表格 ref
    selectedInbounds, // 已选入库单
    dashboardSummary, // 看板汇总
    dashboardCharts, // 看板图表
    dialogVisible, // 入出库弹窗
    catalogVisible, // 主数据弹窗
    catalogKind, // 主数据种类
    catalogSubmitting, // 主数据提交中
    editingProduct, // 编辑商品
    editingLocation, // 编辑库位
    selectedAction, // 当前动作
    operationDraft, // 助手草稿
    locationMapVisible, // 地图弹窗
    locationMapLoading, // 地图加载
    locationMapGroups, // 地图分组
    detailVisible, // 详情弹窗
    detailRow, // 详情行
    productMap, // 商品映射
    locationMap, // 库位映射
    warehouseMap, // 仓库映射
    referenceLoaded, // 主数据已加载
    productOptions, // 商品选项
    locationOptions, // 库位选项
    offset, // 分页偏移
    emptyDescription, // 空态
    dashboardCards, // 看板卡片
    getColumnField, // 列字段映射
    statusText, // 状态文案
    ledgerDirection, // 流水方向
    formatDateTime, // 时间格式化
    loadReferenceData, // 加载主数据
    loadProducts, // 加载商品
    loadLocations, // 加载库位
    loadInventory, // 加载库存
    loadLedgers, // 加载流水
    loadInbounds, // 加载入库
    loadOutbounds, // 加载出库
    loadPickingTasks, // 加载拣货
    loadImports, // 加载导入
    loadAuditLogs, // 加载审计
    loadAlerts, // 加载预警
    loadData, // 分发加载
    applyPendingDraft, // 消费草稿
    search, // 搜索
    reset, // 重置
    changePage, // 翻页
    printPickingList, // 打印拣货单
    openAction, // 工具栏
    rowAction, // 行按钮
    handleRowAction, // 执行行操作
    visibleActions, // 可见按钮
    visibleChildren, // 可见子入口
    inboundAllSelected, // 入库全选
    inboundIndeterminate, // 入库半选
    switchInboundView, // 切换入库视图
    onInboundSelection, // 勾选变化
    toggleInboundSelectAll, // 全选
    confirmSelectedInbounds, // 批量确认
    submitCatalog, // 保存主数据
    submitAction, // 保存入出库
  } // 结束 return
} // 结束 useWorkspaceController
