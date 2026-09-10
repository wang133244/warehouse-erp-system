export type PageKind = 'dashboard' | 'ai' | 'table' | 'group'
export interface PageChild { path: string; label: string; subtitle: string; icon: string }
export interface BreadcrumbItem { label: string; path?: string; current?: boolean }
export interface PageConfig {
  title: string; subtitle: string; section: string; kind?: PageKind
  columns: string[]; filters: string[]; actions: string[]; emptyTitle: string; emptyDescription: string; children?: PageChild[]
}

const table = (title: string, subtitle: string, section: string, columns: string[], filters: string[], actions: string[], emptyTitle = '暂无数据'): PageConfig => ({
  title, subtitle, section, columns, filters, actions, kind: 'table', emptyTitle,
  emptyDescription: 'FastAPI 已接入，当前没有符合条件的数据。'
})

const group = (title: string, subtitle: string, section: string, children: PageChild[]): PageConfig => ({
  title, subtitle, section, kind: 'group', columns: [], filters: [], actions: [],
  emptyTitle: '暂无功能', emptyDescription: '后端接入后将在对应功能页面展示真实业务数据。', children
})

export const pageConfigs: Record<string, PageConfig> = {
  '/overview': group('运营总览', '仓储运营核心指标和作业概览', '运营总览', [
    { path: '/dashboard', label: '仓储运营看板', subtitle: '查看库存、入库、出库和重点作业概览', icon: '▦' }
  ]),
  '/master-data': group('基础资料', '维护商品、SKU、仓库和库位基础信息', '基础资料', [
    { path: '/products', label: '商品与 SKU', subtitle: '维护商品编码、品牌和托盘容量', icon: '□' },
    { path: '/locations', label: '仓库与库位', subtitle: '查看仓库、库区、货架和储位结构', icon: '⌗' }
  ]),
  '/inventory-center': group('库存中心', '查询库存现状并追踪库存变化', '库存中心', [
    { path: '/inventory', label: '库存查询', subtitle: '按商品、库位和库存状态查询库存', icon: '▤' },
    { path: '/inventory-ledger', label: '库存流水', subtitle: '追踪入库、出库、盘点和调拨变动', icon: '↕' }
  ]),
  '/inbound-management': group('入库管理', '管理收货预约、收货记录和入库确认', '入库管理', [
    { path: '/inbounds', label: '入库单', subtitle: '管理入库单和收货预约', icon: '↓' },
    { path: '/receiving', label: '收货确认', subtitle: '核对实际收货数量、库位和异常', icon: '✓' }
  ]),
  '/outbound-management': group('出库管理', '管理客户订单、拣货和出库复核', '出库管理', [
    { path: '/outbounds', label: '出库单', subtitle: '管理客户订单和库存分配', icon: '↑' },
    { path: '/picking', label: '拣货任务', subtitle: '按库位和优先级组织拣货作业', icon: '⌁' },
    { path: '/outbound-review', label: '出库复核', subtitle: '复核拣货数量和客户订单信息', icon: '◉' }
  ]),
  '/inventory-operations': group('库存作业', '处理盘点、差异和库位调拨业务', '库存作业', [
    { path: '/counting', label: '盘点管理', subtitle: '发起盘点并提交差异审核', icon: '⊞' },
    { path: '/transfer', label: '调拨管理', subtitle: '管理库位之间的库存调拨', icon: '⇄' }
  ]),
  '/operations': group('运营管理', '统一处理库存预警和业务审批', '运营管理', [
    { path: '/alerts', label: '预警中心', subtitle: '查看低库存、异常库存和作业异常', icon: '!' },
    { path: '/approvals', label: '审批中心', subtitle: '处理库存调整、盘点和调拨审批', icon: '◌' }
  ]),
  '/system': group('系统管理', '管理数据导入和系统操作审计', '系统管理', [
    { path: '/imports', label: '数据导入', subtitle: '查看 Mega Star 数据批次和校验结果', icon: '⇩' },
    { path: '/audit', label: '操作审计', subtitle: '追踪用户、时间、对象和操作结果', icon: '◍' }
  ]),
  '/assistant': group('智能助手', '通过 AI 辅助查询、分析、预警和业务草稿', '智能助手', [
    { path: '/ai-workbench', label: 'AI 智能工作台', subtitle: '连接 LangGraph 多智能体后的统一入口', icon: '✦' }
  ]),
  '/dashboard': { title: '仓储运营看板', subtitle: 'Mega Star Distribution Centre · 实时运营视图', section: '首页看板', kind: 'dashboard', columns: [], filters: [], actions: ['刷新看板', '导出运营摘要'], emptyTitle: '等待真实数据接入', emptyDescription: '统计卡和图表将在后端接口接入后展示真实结果。' },
  '/products': table('商品与 SKU', '维护商品主数据、品牌和托盘容量', '基础资料', ['系统 SKU', '商品编码', '商品名称', '品牌', '托盘容量', '状态'], ['系统 SKU / 商品编码', '品牌', '状态'], ['新建商品', '导入商品', '查看详情']),
  '/locations': table('仓库与库位', '查看仓库、库区、巷道、货架和储位结构', '基础资料', ['仓库编码', '库位编码', '库区', '巷道', '货架', '储位状态'], ['库位编码', '库区', '状态'], ['新建库位', '批量导入', '查看库位地图']),
  '/inventory': table('库存查询', '按商品、库位和库存状态查询当前库存', '库存中心', ['系统 SKU', '商品编码', '库位编码', '实际库存数量', '可用量', '锁定量', '冻结量', '最后更新时间'], ['系统 SKU / 商品编码', '库位编码', '库存状态'], ['库存调整申请', '导出库存', '查看库存详情'], '暂无库存数据'),
  '/inventory-ledger': table('库存流水', '追踪入库、出库、盘点和调拨产生的库存变动', '库存中心', ['流水号', '系统 SKU', '库位编码', '业务类型', '变动数量', '变动前数量', '变动后数量', '发生时间'], ['流水号', '业务类型', '时间范围'], ['导出流水', '查看关联单据'], '暂无库存流水'),
  '/inbounds': table('入库单', '管理收货预约、收货记录和入库确认', '入库管理', ['入库单号', '商品编码', '系统 SKU', '收货数量', '收货库位', '单据状态', '创建时间'], ['入库单号', '商品编码', '单据状态'], ['新建入库单', '收货确认', '查看详情']),
  '/receiving': table('收货确认', '核对实际收货数量、库位和异常信息', '入库管理', ['收货记录号', '入库单号', '商品编码', '实际收货数量', '库位编码', '异常状态'], ['收货记录号', '入库单号', '异常状态'], ['开始收货', '提交收货结果'], '暂无待收货记录'),
  '/outbounds': table('出库单', '管理客户订单、库存分配和出库完成', '出库管理', ['出库单号', '客户编号', '商品编码', '需求数量', '分配数量', '单据状态', '创建时间'], ['出库单号', '客户编号', '单据状态'], ['新建出库单', '分配库存', '查看详情']),
  '/picking': table('拣货任务', '按库位和任务优先级组织拣货作业', '出库管理', ['任务号', '出库单号', '库位编码', '系统 SKU', '拣货数量', '任务状态', '优先级'], ['任务号', '库位编码', '任务状态'], ['生成拣货任务', '确认拣货', '打印拣货单'], '暂无拣货任务'),
  '/outbound-review': table('出库复核', '复核拣货数量、商品和客户订单信息', '出库管理', ['复核单号', '出库单号', '客户编号', '复核数量', '异常说明', '复核状态'], ['复核单号', '出库单号', '复核状态'], ['开始复核', '完成出库复核'], '暂无待复核记录'),
  '/counting': table('盘点管理', '发起盘点、登记实盘数量并提交差异审核', '库存作业', ['盘点单号', '盘点范围', '库位编码', '系统 SKU', '账面数量', '实盘数量', '差异数量', '盘点状态'], ['盘点单号', '盘点范围', '盘点状态'], ['新建盘点单', '录入实盘数量', '提交盘点']),
  '/transfer': table('调拨管理', '管理库位之间的库存调拨申请和执行', '库存作业', ['调拨单号', '来源库位', '目标库位', '系统 SKU', '调拨数量', '审批状态', '执行状态'], ['调拨单号', '来源库位', '目标库位', '执行状态'], ['新建调拨单', '提交审批', '执行调拨']),
  '/alerts': table('预警中心', '集中查看低库存、异常库存和作业异常', '运营管理', ['预警编号', '预警类型', '系统 SKU', '库位编码', '当前数量', '预警阈值', '处理状态', '产生时间'], ['预警类型', '处理状态', '时间范围'], ['标记已处理', '生成补货草稿'], '暂无预警'),
  '/approvals': table('审批中心', '处理盘点差异、库存调整和调拨等审批事项', '运营管理', ['审批编号', '业务类型', '业务单号', '申请人', '申请时间', '审批状态'], ['审批编号', '业务类型', '审批状态'], ['查看申请', '同意', '驳回'], '暂无待审批事项'),
  '/imports': table('数据导入', '查看 Mega Star 数据批次和校验结果', '系统管理', ['批次号', '文件名称', '数据类型', '导入行数', '成功行数', '失败行数', '导入状态', '导入时间'], ['批次号', '数据类型', '导入状态'], ['上传文件', '查看错误明细', '重新校验'], '暂无导入批次'),
  '/audit': table('操作审计', '追踪用户、时间、业务对象和操作结果', '系统管理', ['审计编号', '操作人', '操作类型', '业务对象', '业务单号', '操作结果', '操作时间'], ['操作人', '操作类型', '时间范围'], ['导出审计记录', '查看详情'], '暂无审计记录'),
  '/ai-workbench': { title: 'AI 智能工作台', subtitle: '查询、分析、预警和草稿建议统一入口', section: '智能助手', kind: 'ai', columns: [], filters: [], actions: ['新建会话', '清空会话'], emptyTitle: 'AI 服务尚未接入', emptyDescription: '接入 LangGraph 多智能体后，可在这里查询库存、分析作业并生成待审批草稿。' }
}

export const getBreadcrumbItems = (path: string): BreadcrumbItem[] => {
  const config = pageConfigs[path] ?? pageConfigs['/dashboard']
  const moduleEntry = Object.entries(pageConfigs).find(([, item]) => item.kind === 'group' && item.section === config.section)
  const items: BreadcrumbItem[] = [{ label: '智能 ERP', path: '/overview' }]

  if (moduleEntry) {
    const [modulePath] = moduleEntry
    if (path === modulePath) items.push({ label: config.section, path: undefined, current: true })
    else items.push({ label: config.section, path: modulePath })
  }
  if (path !== moduleEntry?.[0]) {
    items.push({ label: config.title, path: undefined, current: true })
  }
  return items
}

export const menuGroups = [
  { label: '运营总览', items: [{ path: '/overview', label: '运营总览', icon: '▦' }] },
  { label: '基础资料', items: [{ path: '/master-data', label: '基础资料', icon: '□' }] },
  { label: '库存中心', items: [{ path: '/inventory-center', label: '库存中心', icon: '▤' }] },
  { label: '入库管理', items: [{ path: '/inbound-management', label: '入库管理', icon: '↓' }] },
  { label: '出库管理', items: [{ path: '/outbound-management', label: '出库管理', icon: '↑' }] },
  { label: '库存作业', items: [{ path: '/inventory-operations', label: '库存作业', icon: '⊞' }] },
  { label: '运营管理', items: [{ path: '/operations', label: '运营管理', icon: '!' }] },
  { label: '系统管理', items: [{ path: '/system', label: '系统管理', icon: '◍' }] },
  { label: '智能助手', items: [{ path: '/assistant', label: '智能助手', icon: '✦' }] }
]
