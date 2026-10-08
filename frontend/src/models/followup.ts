/** 助手会话、用户、报表、runtime API。 */
import { createIdempotencyKey, request, type QueryParams } from './client' // 引入请求封装与查询类型

export interface SystemUser { // 系统用户
  user_id: number // 用户主键
  username: string // 登录账号
  display_name: string // 显示名
  is_active: boolean // 是否启用
  roles: string[] // 角色编码
  warehouse_ids: number[] // 仓库数据范围
} // 结束 SystemUser

export interface UserUpsert { // 创建/更新用户载荷
  username?: string // 账号（更新时可省略）
  password?: string // 密码（空表示不改）
  display_name?: string // 显示名
  roles: string[] // 角色
  warehouse_ids: number[] // 仓库范围
  is_active?: boolean // 启用状态
} // 结束 UserUpsert

export interface AgentSession { // 助手会话
  session_id: number // 会话主键
  title: string // 标题
  created_at: string | null // 创建时间
} // 结束 AgentSession

export interface AgentMessage { // 助手消息
  message_id: number // 消息主键
  session_id: number // 所属会话
  role: 'user' | 'assistant' | string // 角色
  content: string // 正文
  tool_calls: { name: string; arguments?: unknown }[] // 工具调用
  draft: Record<string, unknown> | null // 单据草稿
} // 结束 AgentMessage

export function listUsers(params: { keyword?: string } = {}) { // 用户列表
  return request<{ total: number; items: SystemUser[] }>('/api/v1/users', { params: params as QueryParams }) // GET 用户
} // 结束 listUsers

export function createUser(payload: UserUpsert & { username: string; password: string; display_name: string }) { // 新建用户
  return request<SystemUser>('/api/v1/users', { // POST 用户
    method: 'POST', // POST
    body: payload, // 用户字段
    idempotencyKey: createIdempotencyKey('user') // 幂等键
  }) // 结束 request
} // 结束 createUser

export function updateUser(userId: number, payload: UserUpsert) { // 更新用户
  return request<SystemUser>(`/api/v1/users/${userId}`, { // PATCH 用户
    method: 'PATCH', // PATCH
    body: payload, // 可变字段
    idempotencyKey: createIdempotencyKey('user-update') // 幂等键
  }) // 结束 request
} // 结束 updateUser

export function deleteUser(userId: number) { // 停用/删除用户
  return request<{ user_id: number; deleted: boolean }>(`/api/v1/users/${userId}`, { // DELETE 用户
    method: 'DELETE', // DELETE
    idempotencyKey: createIdempotencyKey('user-delete') // 幂等键
  }) // 结束 request
} // 结束 deleteUser

export interface SystemRole { // 系统角色
  role_id: number // 角色主键
  role_code: string // 角色编码
  role_name: string // 角色名称
} // 结束 SystemRole

export function listRoles() { // 角色列表
  return request<{ items: SystemRole[] }>('/api/v1/roles') // GET 角色
} // 结束 listRoles

export function createAgentSession() { // 新建助手会话
  return request<AgentSession>('/api/v1/agents/sessions', { // POST 会话
    method: 'POST', // POST
    idempotencyKey: createIdempotencyKey('agent-session') // 幂等键
  }) // 结束 request
} // 结束 createAgentSession

export function listAgentSessions() { // 会话列表
  return request<{ items: AgentSession[] }>('/api/v1/agents/sessions') // GET 会话
} // 结束 listAgentSessions

export function sendAgentMessage(sessionId: number, content: string) { // 发送助手消息
  return request<AgentMessage>(`/api/v1/agents/sessions/${sessionId}/messages`, { // POST 消息
    method: 'POST', // POST
    body: { content }, // 用户提问
    idempotencyKey: createIdempotencyKey('agent-message') // 幂等键
  }) // 结束 request
} // 结束 sendAgentMessage

export function listAgentMessages(sessionId: number) { // 会话消息列表
  return request<{ items: AgentMessage[] }>(`/api/v1/agents/sessions/${sessionId}/messages`) // GET 消息
} // 结束 listAgentMessages

export function clearAgentSession(sessionId: number) { // 清空会话消息
  return request<AgentSession>(`/api/v1/agents/sessions/${sessionId}/clear`, { // POST 清空
    method: 'POST', // POST
    idempotencyKey: createIdempotencyKey('agent-clear') // 幂等键
  }) // 结束 request
} // 结束 clearAgentSession

export function deleteAgentSession(sessionId: number) { // 删除会话
  return request<{ session_id: number; deleted: boolean }>(`/api/v1/agents/sessions/${sessionId}`, { // DELETE 会话
    method: 'DELETE', // DELETE
    idempotencyKey: createIdempotencyKey('agent-delete') // 幂等键
  }) // 结束 request
} // 结束 deleteAgentSession

export interface AbcReportItem { // ABC 分类行
  product_id: number // 商品 ID
  sku_code: string // SKU
  product_name: string // 商品名
  score: number // 得分
  share: number // 份额
  class: 'A' | 'B' | 'C' | string // 分类
  basis: string // 计算口径
} // 结束 AbcReportItem

export interface TurnoverReportItem { // 周转行
  product_id: number // 商品 ID
  sku_code: string // SKU
  product_name: string // 商品名
  outbound_quantity: number // 出库量
  on_hand_quantity: number // 现存量
  turnover_rate: number // 周转率
} // 结束 TurnoverReportItem

export function getAbcReport(days?: number) { // ABC 报表
  return request<{ items: AbcReportItem[]; basis: string }>('/api/v1/reports/abc', { // GET ABC
    params: { days } // 统计天数
  }) // 结束 request
} // 结束 getAbcReport

export function getTurnoverReport() { // 周转报表
  return request<{ items: TurnoverReportItem[] }>('/api/v1/reports/turnover') // GET 周转
} // 结束 getTurnoverReport

export interface MovementReportItem { // 出入库日报/周报行
  date?: string // 日期（日报）
  week?: string // 周（周报）
  inbound_quantity: number // 入库量
  outbound_quantity: number // 出库量
} // 结束 MovementReportItem

export interface PickingEfficiency { // 拣货效率
  total_tasks: number // 任务总数
  completed_tasks: number // 已完成数
  completion_rate: number // 完成率
  average_confirm_seconds: number // 平均确认秒数
} // 结束 PickingEfficiency

export function getDailyReport(days?: number) { // 库存日报
  return request<{ items: MovementReportItem[]; days: number }>('/api/v1/reports/daily', { // GET 日报
    params: { days } // 天数
  }) // 结束 request
} // 结束 getDailyReport

export function getWeeklyReport(weeks?: number) { // 库存周报
  return request<{ items: MovementReportItem[]; weeks: number }>('/api/v1/reports/weekly', { // GET 周报
    params: { weeks } // 周数
  }) // 结束 request
} // 结束 getWeeklyReport

export function getPickingEfficiency() { // 拣货效率报表
  return request<PickingEfficiency>('/api/v1/reports/picking-efficiency') // GET 效率
} // 结束 getPickingEfficiency

export interface SystemRuntime { // 系统运行时
  cache_backend: string // 缓存后端
  graph_engine: string // 图引擎
  llm_provider?: string // LLM 提供方
  inventory_source: string // 库存数据源
} // 结束 SystemRuntime

export function getSystemRuntime() { // 读取运行时配置
  return request<SystemRuntime>('/api/v1/system/runtime') // GET runtime
} // 结束 getSystemRuntime
