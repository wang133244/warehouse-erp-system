/** 菜单、列、按钮与 canAccessPath；前端拦截，后端 RBAC 才是最终闸门。 */
export type PageKind = 'dashboard' | 'ai' | 'table' | 'group' // 页面种类
export interface PageChild { path: string; label: string; subtitle: string; icon: string } // 分组子入口
export interface BreadcrumbItem { label: string; path?: string; current?: boolean } // 面包屑项
export interface PageConfig { // 单页配置
  title: string; subtitle: string; section: string; kind?: PageKind // 标题与所属模块
  columns: string[]; filters: string[]; actions: string[]; emptyTitle: string; emptyDescription: string; children?: PageChild[] // 列、筛选、按钮与空态
} // 结束 PageConfig

const table = (title: string, subtitle: string, section: string, columns: string[], filters: string[], actions: string[], emptyTitle = '暂无数据'): PageConfig => ({ // 表格页工厂
  title, subtitle, section, columns, filters, actions, kind: 'table', emptyTitle, // 填入表格页字段
  emptyDescription: 'FastAPI 已接入，当前没有符合条件的数据。' // 统一空态说明
}) // 结束 table

const group = (title: string, subtitle: string, section: string, children: PageChild[]): PageConfig => ({ // 分组页工厂
  title, subtitle, section, kind: 'group', columns: [], filters: [], actions: [], // 分组页无表格列
  emptyTitle: '暂无功能', emptyDescription: '后端接入后将在对应功能页面展示真实业务数据。', children // 空态与子入口
}) // 结束 group

export const pageConfigs: Record<string, PageConfig> = { // 路径到页面配置
  '/overview': group('运营总览', '仓储运营核心指标和作业概览', '运营总览', [ // 运营总览分组
    { path: '/dashboard', label: '仓储运营看板', subtitle: '查看库存、入库、出库和重点作业概览', icon: '▦' } // 看板入口
  ]), // 结束运营总览
  '/master-data': group('基础资料', '维护商品、SKU、仓库和库位基础信息', '基础资料', [ // 基础资料分组
    { path: '/products', label: '商品与 SKU', subtitle: '维护商品编码、品牌和托盘容量', icon: '□' }, // 商品页
    { path: '/locations', label: '仓库与库位', subtitle: '查看仓库、库区、货架和储位结构', icon: '⌗' } // 库位页
  ]), // 结束基础资料
  '/inventory-center': group('库存中心', '查询库存现状并追踪库存变化', '库存中心', [ // 库存中心分组
    { path: '/inventory', label: '库存查询', subtitle: '按商品、库位和库存状态查询库存', icon: '▤' }, // 库存查询
    { path: '/inventory-ledger', label: '库存流水', subtitle: '追踪入库、出库、盘点和调拨变动', icon: '↕' } // 流水
  ]), // 结束库存中心
  '/inbound-management': group('入库管理', '管理待入库确认和收货历史', '入库管理', [ // 入库管理分组
    { path: '/inbounds', label: '待入库确认', subtitle: '待确认入库单、勾选收货和历史记录', icon: '↓' }, // 入库单
    { path: '/receiving', label: '收货确认', subtitle: '核对实际收货数量、库位和异常信息', icon: '◉' } // 收货
  ]), // 结束入库管理
  '/outbound-management': group('出库管理', '管理客户订单、拣货和出库复核', '出库管理', [ // 出库管理分组
    { path: '/outbounds', label: '出库单', subtitle: '管理客户订单和库存分配', icon: '↑' }, // 出库单
    { path: '/picking', label: '拣货任务', subtitle: '按库位和优先级组织拣货作业', icon: '⌁' }, // 拣货
    { path: '/outbound-review', label: '出库复核', subtitle: '复核拣货数量和客户订单信息', icon: '◉' } // 复核
  ]), // 结束出库管理
  '/inventory-operations': group('库存作业', '处理盘点、差异和库位调拨业务', '库存作业', [ // 库存作业分组
    { path: '/counting', label: '盘点管理', subtitle: '发起盘点并提交差异审核', icon: '⊞' }, // 盘点
    { path: '/transfer', label: '调拨管理', subtitle: '管理库位之间的库存调拨', icon: '⇄' } // 调拨
  ]), // 结束库存作业
  '/operations': group('运营管理', '统一处理库存预警和业务审批', '运营管理', [ // 运营管理分组
    { path: '/alerts', label: '预警中心', subtitle: '查看低库存、异常库存和作业异常', icon: '!' }, // 预警
    { path: '/approvals', label: '审批中心', subtitle: '处理库存调整、盘点和调拨审批', icon: '◌' } // 审批
  ]), // 结束运营管理
  '/analytics': group('报表分析', '查看 ABC 分类和库存周转', '报表分析', [ // 报表分组
    { path: '/reports', label: '仓储报表', subtitle: 'ABC、周转、日报周报和拣货效率', icon: '▦' } // 报表页
  ]), // 结束报表分析
  '/system': group('系统管理', '管理账号、数据导入和系统操作审计', '系统管理', [ // 系统管理分组
    { path: '/users', label: '用户与权限', subtitle: '维护账号、角色和仓库数据范围', icon: '👤' }, // 用户
    { path: '/imports', label: '数据导入', subtitle: '查看 Mega Star 数据批次和校验结果', icon: '⇩' }, // 导入
    { path: '/audit', label: '操作审计', subtitle: '追踪用户、时间、对象和操作结果', icon: '◍' } // 审计
  ]), // 结束系统管理
  '/assistant': group('智能助手', '通过 AI 辅助查询、分析、预警和业务草稿', '智能助手', [ // 智能助手分组
    { path: '/ai-workbench', label: 'AI 智能工作台', subtitle: '连接 LangGraph 多智能体后的统一入口', icon: '✦' } // 工作台
  ]), // 结束智能助手
  '/dashboard': { title: '仓储运营看板', subtitle: 'Mega Star Distribution Centre · 实时运营视图', section: '首页看板', kind: 'dashboard', columns: [], filters: [], actions: ['刷新看板', '导出运营摘要'], emptyTitle: '等待真实数据接入', emptyDescription: '统计卡和图表展示 FastAPI 聚合的真实库存与作业指标。' }, // 看板页配置
  '/products': table('商品与 SKU', '维护商品主数据、品牌和托盘容量', '基础资料', ['系统 SKU', '商品编码', '商品名称', '品牌', '托盘容量', '状态'], ['系统 SKU / 商品编码', '品牌', '状态'], ['新建商品', '查看导入批次']), // 商品表
  '/locations': table('仓库与库位', '查看仓库、库区、巷道、货架和储位结构', '基础资料', ['仓库编码', '库位编码', '库区', '巷道', '货架', '储位状态'], ['库位编码 / 库区 / 仓库'], ['新建仓库', '新建库位', '库位信息']), // 库位表
  '/inventory': table('库存查询', '按商品、库位和库存状态查询当前库存', '库存中心', ['系统 SKU', '商品编码', '库位编码', '实际库存数量', '可用量', '锁定量', '冻结量', '最后更新时间'], ['系统 SKU / 商品编码 / 库位'], ['库存调整申请', '导出库存'], '暂无库存数据'), // 库存表
  '/inventory-ledger': table('库存流水', '追踪入库、出库、盘点和调拨产生的库存变动', '库存中心', ['流水号', '系统 SKU', '库位编码', '业务类型', '变动方向', '变动数量', '变动前数量', '变动后数量', '发生时间'], ['流水号 / 业务类型 / SKU'], ['导出流水'], '暂无库存流水'), // 流水表
  '/inbounds': table('待入库确认列表', '勾选待收货入库单并确认，已确认记录可在历史中查看', '入库管理', ['入库单号', '商品编码', '系统 SKU', '收货数量', '收货库位', '单据状态', '账户名', '创建时间'], ['入库单号 / 商品编码'], ['新建入库单', '收货确认']), // 入库表
  '/receiving': table('收货确认', '核对实际收货数量、库位和异常信息', '入库管理', ['收货记录号', '入库单号', '商品编码', '实际收货数量', '库位编码', '异常状态'], ['收货记录号', '入库单号', '异常状态'], ['开始收货', '提交收货结果'], '暂无待收货记录'), // 收货表
  '/outbounds': table('出库单', '管理客户订单、库存分配和出库完成', '出库管理', ['出库单号', '客户编号', '商品编码', '需求数量', '分配数量', '单据状态', '创建时间'], ['出库单号', '客户编号', '单据状态'], ['新建出库单', '去拣货任务']), // 出库表
  '/picking': table('拣货任务', '按库位和任务优先级组织拣货作业', '出库管理', ['任务号', '出库单号', '库位编码', '系统 SKU', '拣货数量', '任务状态', '优先级'], ['任务号', '库位编码', '任务状态'], ['去出库单分配', '打印拣货单'], '暂无拣货任务'), // 拣货表
  '/outbound-review': table('出库复核', '复核拣货数量、商品和客户订单信息', '出库管理', ['复核单号', '出库单号', '客户编号', '复核数量', '异常说明', '复核状态'], ['复核单号', '出库单号', '复核状态'], ['开始复核', '完成出库复核'], '暂无待复核记录'), // 复核表
  '/counting': table('盘点管理', '发起盘点、登记实盘数量并提交差异审核', '库存作业', ['盘点单号', '盘点范围', '库位编码', '系统 SKU', '账面数量', '实盘数量', '差异数量', '盘点状态'], ['盘点单号', '盘点范围', '盘点状态'], ['新建盘点单', '录入实盘数量', '提交盘点']), // 盘点表
  '/transfer': table('调拨管理', '管理库位之间的库存调拨申请和执行', '库存作业', ['调拨单号', '来源库位', '目标库位', '系统 SKU', '调拨数量', '审批状态', '执行状态', '账户名'], ['调拨单号', '来源库位', '目标库位', '执行状态'], ['新建调拨单', '提交审批', '执行调拨']), // 调拨表
  '/alerts': table('预警中心', '集中查看低库存、异常库存和作业异常', '运营管理', ['预警编号', '预警类型', '系统 SKU', '库位编码', '当前数量', '预警阈值', '处理状态', '产生时间'], ['预警类型', '处理状态', '时间范围'], ['标记已处理', '生成补货草稿'], '暂无预警'), // 预警表
  '/approvals': table('审批中心', '处理盘点差异、库存调整和调拨等审批事项', '运营管理', ['审批编号', '业务类型', '业务单号', '申请人', '申请时间', '审批状态'], ['审批编号', '业务类型', '审批状态'], ['查看申请', '同意', '驳回'], '暂无待审批事项'), // 审批表
  '/imports': table('数据导入', '查看 Mega Star 数据批次和校验结果', '系统管理', ['批次号', '文件名称', '数据类型', '导入行数', '成功行数', '失败行数', '导入状态', '导入时间'], ['批次号', '数据类型', '导入状态'], ['上传商品CSV', '查看明细'], '暂无导入批次'), // 导入表
  '/audit': table('操作审计', '追踪用户、时间、业务对象和操作结果', '系统管理', ['审计编号', '账户名', '操作类型', '业务对象', '业务单号', '操作结果', '操作时间'], ['账户名', '操作类型', '时间范围'], ['导出审计记录'], '暂无审计记录'), // 审计表
  '/ai-workbench': { title: 'AI 智能工作台', subtitle: '查询、分析、预警和草稿建议统一入口', section: '智能助手', kind: 'ai', columns: [], filters: [], actions: ['新建会话', '清空会话'], emptyTitle: '开始提问', emptyDescription: '助手通过 LangGraph 多智能体调用白名单工具查询库存、预警和审批，并可生成待人工确认的单据草稿。' }, // AI 页配置
  '/reports': table('仓储报表', 'ABC 分类、周转、库存日报周报和拣货效率', '报表分析', ['系统 SKU', '分类', '份额', '出库量', '现存量', '周转率'], ['系统 SKU', '分类'], ['刷新报表'], '暂无报表数据'), // 报表表
  '/users': table('用户与权限', '维护登录账号、角色和仓库数据范围', '系统管理', ['账户名', '显示名', '角色', '状态'], ['账户名', '角色', '状态'], ['新建用户'], '暂无用户') // 用户表
} // 结束 pageConfigs

export function getBreadcrumbItems(path: string): BreadcrumbItem[] { // 根据路径生成面包屑
  const resolvedPath = /^\/imports\/\d+$/.test(path) ? '/imports' : path // 导入详情归到导入模块
  const config = pageConfigs[resolvedPath] ?? pageConfigs['/dashboard'] // 找不到则用看板
  const moduleEntry = Object.entries(pageConfigs).find(([, item]) => item.kind === 'group' && item.section === config.section) // 找所属分组
  const items: BreadcrumbItem[] = [{ label: '智能 ERP', path: '/overview' }] // 根面包屑

  if (moduleEntry) { // 找到模块分组
    const [modulePath] = moduleEntry // 取出模块路径
    if (resolvedPath === modulePath) items.push({ label: config.section, path: undefined, current: true }) // 就在分组页则当前项
    else items.push({ label: config.section, path: modulePath }) // 否则可点回分组
  } // 结束模块分支
  if (resolvedPath !== moduleEntry?.[0]) { // 不是分组页本身则再加当前页
    const title = /^\/imports\/\d+$/.test(path) ? '导入批次详情' : config.title // 导入详情用专用标题
    items.push({ label: title, path: undefined, current: true }) // 当前页不可点
  } // 结束当前页分支
  return items // 返回面包屑
} // 结束 getBreadcrumbItems

export const menuGroups = [ // 侧栏菜单分组
  { label: '运营总览', items: [{ path: '/overview', label: '运营总览', icon: '▦' }] }, // 总览
  { label: '基础资料', items: [{ path: '/master-data', label: '基础资料', icon: '□' }] }, // 主数据
  { label: '库存中心', items: [{ path: '/inventory-center', label: '库存中心', icon: '▤' }] }, // 库存
  { label: '入库管理', items: [{ path: '/inbound-management', label: '入库管理', icon: '↓' }] }, // 入库
  { label: '出库管理', items: [{ path: '/outbound-management', label: '出库管理', icon: '↑' }] }, // 出库
  { label: '库存作业', items: [{ path: '/inventory-operations', label: '库存作业', icon: '⊞' }] }, // 作业
  { label: '运营管理', items: [{ path: '/operations', label: '运营管理', icon: '!' }] }, // 运营
  { label: '报表分析', items: [{ path: '/analytics', label: '报表分析', icon: '▦' }] }, // 报表
  { label: '系统管理', items: [{ path: '/system', label: '系统管理', icon: '◍' }] }, // 系统
  { label: '智能助手', items: [{ path: '/assistant', label: '智能助手', icon: '✦' }] } // 助手
] // 结束 menuGroups

const ADMIN_ONLY_PREFIXES = ['/system', '/users', '/imports', '/audit'] // 仅管理员可进的路径前缀
const WRITE_PREFIXES = [ // 只读角色不可进的写路径
  '/inbound-management', // 入库分组
  '/inbounds', // 入库单
  '/receiving', // 收货
  '/outbound-management', // 出库分组
  '/outbounds', // 出库单
  '/picking', // 拣货
  '/outbound-review', // 复核
  '/inventory-operations', // 库存作业分组
  '/counting', // 盘点
  '/transfer', // 调拨
  '/approvals' // 审批
] // 结束 WRITE_PREFIXES
const WRITE_ACTIONS = new Set([ // 写操作按钮名
  '新建商品', // 商品
  '新建库位', // 库位
  '新建仓库', // 仓库
  '新建入库单', // 入库
  '收货确认', // 收货
  '开始收货', // 开始收货
  '提交收货结果', // 提交收货
  '新建出库单', // 出库
  '去拣货任务', // 拣货
  '去出库单分配', // 分配
  '打印拣货单', // 打印
  '新建盘点单', // 盘点
  '录入实盘数量', // 实盘
  '提交盘点', // 提交盘点
  '新建调拨单', // 调拨
  '提交审批', // 提交审批
  '执行调拨', // 执行
  '库存调整申请', // 调整
  '生成补货草稿', // 补货
  '标记已处理', // 预警
  '同意', // 审批同意
  '驳回', // 审批驳回
  '开始复核', // 复核
  '完成出库复核', // 完成复核
  '新建用户', // 用户
  '上传商品CSV' // 导入
]) // 结束 WRITE_ACTIONS
const MASTER_WRITE_ACTIONS = new Set(['新建商品', '新建库位', '新建仓库']) // 仅管理员/仓管可做的主数据写操作
const ADMIN_ONLY_ACTIONS = new Set(['查看导入批次', '新建用户', '上传商品CSV']) // 仅管理员按钮

function normalizedRoles(roles: string[]) { // 兼容旧 operator 角色名
  return roles.map((role) => (role === 'operator' ? 'warehouse_operator' : role)) // operator 归一为 warehouse_operator
} // 结束 normalizedRoles

function hasRole(roles: string[], ...codes: string[]) { // 是否包含任一角色
  const current = new Set(normalizedRoles(roles)) // 规范化后放入集合
  return codes.some((code) => current.has(code)) // 任一命中即 true
} // 结束 hasRole

export function isViewerOnly(roles: string[]) { // 是否纯只读且无写角色
  return hasRole(roles, 'viewer') && !hasRole(roles, 'admin', 'warehouse_manager', 'warehouse_operator') // 有 viewer 且无管理/操作
} // 结束 isViewerOnly

function matchesPrefix(path: string, prefix: string) { // 路径是否等于或位于前缀下
  return path === prefix || path.startsWith(`${prefix}/`) // 精确或子路径
} // 结束 matchesPrefix

export function canAccessPath(path: string, roles: string[]): boolean { // 前端路径权限
  if (hasRole(roles, 'admin')) return true // 管理员全放行
  if (ADMIN_ONLY_PREFIXES.some((prefix) => matchesPrefix(path, prefix))) return false // 系统类路径拦截
  if (isViewerOnly(roles) && WRITE_PREFIXES.some((prefix) => matchesPrefix(path, prefix))) return false // 只读拦截写路径
  return true // 其余放行
} // 结束 canAccessPath

export function canPerformAction(action: string, roles: string[]): boolean { // 前端按钮权限
  if (hasRole(roles, 'admin')) return true // 管理员全放行
  if (ADMIN_ONLY_ACTIONS.has(action)) return false // 管理员专属按钮
  if (isViewerOnly(roles)) return !WRITE_ACTIONS.has(action) // 只读只能点非写按钮
  if (!hasRole(roles, 'warehouse_manager') && MASTER_WRITE_ACTIONS.has(action)) return false // 非仓管不能改主数据
  return true // 其余放行
} // 结束 canPerformAction

export function visibleMenuGroupsFor(roles: string[]) { // 按角色过滤侧栏
  if (hasRole(roles, 'admin')) return menuGroups // 管理员看全部
  const hidden = new Set(['系统管理']) // 默认藏系统管理
  if (isViewerOnly(roles)) { // 只读再藏作业类模块
    hidden.add('入库管理') // 藏入库
    hidden.add('出库管理') // 藏出库
    hidden.add('库存作业') // 藏盘点调拨
  } // 结束只读隐藏
  return menuGroups.filter((group) => !hidden.has(group.label)) // 过滤菜单
} // 结束 visibleMenuGroupsFor

export function visibleChildrenFor(path: string, roles: string[]) { // 分组页可见子入口
  return (pageConfigs[path]?.children ?? []).filter((child) => canAccessPath(child.path, roles)) // 按路径权限过滤
} // 结束 visibleChildrenFor
