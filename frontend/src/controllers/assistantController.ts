/** 助手会话；换用户清空；草稿带路由跳转业务页。 */
import { computed, nextTick, onMounted, ref, watch } from 'vue' // 引入 Vue 组合式 API
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { ApiError } from '../models/client' // API 错误类型
import { // 助手会话 API
  clearAgentSession, // 清空会话消息
  createAgentSession, // 新建会话
  deleteAgentSession, // 删除会话
  getSystemRuntime, // 运行时信息（LLM 提供方）
  listAgentMessages, // 消息列表
  listAgentSessions, // 会话列表
  sendAgentMessage, // 发送提问
  type AgentMessage, // 消息类型
  type AgentSession // 会话类型
} from '../models/followup' // 来自 followup 模型
import { useAppStore, type OperationDraft } from '../stores/app' // 草稿与当前用户
import router from '../router' // 用于草稿跳转业务页

export function useAssistantController() { // AI 工作台控制器
  const config = pageConfigs['/ai-workbench'] // 本页配置
  const app = useAppStore() // 应用仓库
  const sessions = ref<AgentSession[]>([]) // 会话列表
  const messages = ref<AgentMessage[]>([]) // 当前会话消息
  const activeId = ref<number | null>(null) // 当前会话 ID
  const question = ref('') // 输入框内容
  const sending = ref(false) // 发送中
  const errorMessage = ref('') // 错误文案
  const llmProvider = ref('none') // LLM 提供方
  const engineLabel = computed(() => // 引擎展示文案
    llmProvider.value === 'deepseek' ? 'LangGraph 多智能体 · DeepSeek' : 'LangGraph 多智能体' // DeepSeek 时加后缀
  ) // 结束 engineLabel
  const activeSession = computed(() => sessions.value.find((item) => item.session_id === activeId.value) ?? null) // 当前会话对象
  const citations = computed(() => // 助手调用过的工具名
    messages.value.filter((item) => item.role === 'assistant').flatMap((item) => item.tool_calls.map((call) => call.name)) // 展平工具名
  ) // 结束 citations
  const userInitial = computed(() => (app.currentUser?.display_name || app.currentUser?.username || '我').slice(0, 1)) // 头像首字
  const wechatBody = ref<HTMLElement | null>(null) // 消息滚动容器

  const loadSessions = async () => { // 加载会话列表
    try { // 请求列表
      const page = await listAgentSessions() // 拉取会话
      sessions.value = page.items // 写入列表
      const stillMine = page.items.some((item) => item.session_id === activeId.value) // 当前会话是否仍存在
      if (!stillMine) { // 当前会话已不在列表
        activeId.value = page.items[0]?.session_id ?? null // 切到第一条或空
        if (!activeId.value) messages.value = [] // 无会话则清空消息
      } // 结束会话失效分支
    } catch (error) { // 加载失败
      errorMessage.value = error instanceof Error ? error.message : '会话加载失败' // 记录错误
    } // 结束 catch
  } // 结束 loadSessions

  const loadMessages = async (sessionId: number) => { // 加载某会话消息
    try { // 请求消息
      const page = await listAgentMessages(sessionId) // 按会话拉消息
      messages.value = page.items // 写入消息
    } catch (error) { // 加载失败
      messages.value = [] // 清空消息
      errorMessage.value = error instanceof Error ? error.message : '消息加载失败' // 记录错误
    } // 结束 catch
  } // 结束 loadMessages

  const createSession = async () => { // 新建会话
    try { // 调用创建
      const session = await createAgentSession() // 创建接口
      sessions.value = [session, ...sessions.value] // 插到列表头部
      activeId.value = session.session_id // 切到新会话
      messages.value = [] // 新会话无消息
    } catch (error) { // 创建失败
      ElMessage.error(error instanceof ApiError ? error.message : '新建会话失败') // 错误提示
    } // 结束 catch
  } // 结束 createSession

  const clearSession = async () => { // 清空当前会话消息
    if (!activeId.value) { // 没有当前会话
      ElMessage.info('当前没有会话可清空') // 提示
      return // 退出
    } // 结束无会话分支
    try { // 调用清空
      const session = await clearAgentSession(activeId.value) // 清空接口
      messages.value = [] // 本地清空消息
      question.value = '' // 清空输入框
      sessions.value = sessions.value.map((item) => // 用返回结果更新列表项
        item.session_id === session.session_id ? { ...item, ...session } : item // 匹配则合并
      ) // 结束 map
      ElMessage.success('已清空当前会话') // 成功提示
    } catch (error) { // 清空失败
      ElMessage.error(error instanceof ApiError ? error.message : '清空会话失败') // 错误提示
    } // 结束 catch
  } // 结束 clearSession

  const deletingId = ref<number | null>(null) // 正在删除的会话 ID，防重复点

  const removeSessionFromList = (sessionId: number) => { // 从本地列表移除会话
    const remaining = sessions.value.filter((item) => Number(item.session_id) !== Number(sessionId)) // 过滤掉目标
    sessions.value = remaining // 写回列表
    errorMessage.value = '' // 清错误
    if (Number(activeId.value) === Number(sessionId)) { // 删的是当前会话
      question.value = '' // 清空输入
      activeId.value = remaining[0]?.session_id ?? null // 切到下一条
      if (!activeId.value) messages.value = [] // 没有会话则清空消息
    } // 结束当前会话被删分支
  } // 结束 removeSessionFromList

  const deleteSession = async (session: AgentSession) => { // 删除会话
    if (deletingId.value === session.session_id) return // 正在删则忽略重复点击
    deletingId.value = session.session_id // 标记删除中
    try { // 调删除接口
      await deleteAgentSession(session.session_id) // 删除
      removeSessionFromList(session.session_id) // 本地移除
      ElMessage.success('已删除会话') // 成功提示
    } catch (error) { // 删除失败
      if (error instanceof ApiError && error.status === 404) { // 已不存在视为成功
        removeSessionFromList(session.session_id) // 仍从列表移除
        ElMessage.success('已删除会话') // 成功提示
        return // 提前结束
      } // 结束 404 分支
      ElMessage.error(error instanceof ApiError ? error.message : '删除会话失败') // 其他错误
    } finally { // 无论成败
      deletingId.value = null // 清除删除中标记
    } // 结束 finally
  } // 结束 deleteSession

  const send = async () => { // 发送提问
    if (!question.value.trim()) return // 空内容不发
    if (!activeId.value) await createSession() // 无会话先创建
    const sessionId = activeId.value // 锁定本次会话 ID
    if (!sessionId) return // 创建失败则退出
    sending.value = true // 开始发送
    const content = question.value.trim() // 取出问题
    question.value = '' // 立刻清空输入框
    messages.value = [...messages.value, { message_id: Date.now(), session_id: sessionId, role: 'user', content, tool_calls: [], draft: null }] // 乐观插入用户消息
    try { // 请求助手回复
      const reply = await sendAgentMessage(sessionId, content) // 发送接口
      if (activeId.value !== sessionId) return // 期间已切会话则丢弃回复
      messages.value = [...messages.value, reply] // 追加助手消息
    } catch (error) { // 提问失败
      ElMessage.error(error instanceof ApiError ? error.message : '提问失败') // 错误提示
    } finally { // 无论成败
      sending.value = false // 结束发送状态
    } // 结束 finally
  } // 结束 send

  const applyDraft = async (draft: OperationDraft) => { // 把草稿带到业务页
    app.setPendingDraft(draft) // 写入待消费草稿
    const path = draft.type === 'outbound' ? '/outbounds' : draft.type === 'counting' ? '/counting' : '/inbounds' // 按类型选目标页
    ElMessage.success('已带入单据草稿，请人工确认后保存。') // 提示人工确认
    await router.push(path) // 跳转业务页
  } // 结束 applyDraft

  watch(activeId, async (sessionId) => { // 切换会话时拉消息
    if (!sessionId) { // 没有当前会话
      messages.value = [] // 清空消息
      return // 退出
    } // 结束空会话分支
    await loadMessages(sessionId) // 加载该会话消息
  }) // 结束 watch activeId

  watch( // 切换登录用户时清空助手状态
    () => app.currentUser?.user_id ?? null, // 监听用户 ID
    async (userId, previousId) => { // 用户变化回调
      if (previousId == null || userId === previousId) return // 首次填充或未变化则忽略
      sessions.value = [] // 清空会话
      messages.value = [] // 清空消息
      activeId.value = null // 清空当前会话
      question.value = '' // 清空输入
      errorMessage.value = '' // 清空错误
      if (userId) await loadSessions() // 新用户存在则重拉会话
    } // 结束回调
  ) // 结束 watch 用户

  watch( // 新消息后滚到底部
    messages, // 监听消息数组
    async () => { // 变化后滚动
      await nextTick() // 等 DOM 更新
      if (wechatBody.value) wechatBody.value.scrollTop = wechatBody.value.scrollHeight // 滚到最底
    }, // 结束回调
    { deep: true } // 深度监听消息内容
  ) // 结束 watch messages

  onMounted(async () => { // 挂载时读运行时再拉会话
    try { // 拉 LLM 提供方
      const runtime = await getSystemRuntime() // 运行时接口
      llmProvider.value = runtime.llm_provider ?? 'none' // 写入提供方
    } catch { // 失败视为无 LLM
      llmProvider.value = 'none' // 回退 none
    } // 结束 catch
    await loadSessions() // 加载会话列表
  }) // 结束 onMounted

  return { // 暴露给视图
    config, // 页面配置
    router, // 路由器
    app, // 应用仓库
    sessions, // 会话列表
    messages, // 消息
    activeId, // 当前会话
    question, // 输入内容
    sending, // 发送中
    errorMessage, // 错误信息
    llmProvider, // LLM 提供方
    engineLabel, // 引擎文案
    activeSession, // 当前会话对象
    citations, // 工具引用
    userInitial, // 用户首字
    wechatBody, // 滚动容器
    loadSessions, // 加载会话
    loadMessages, // 加载消息
    createSession, // 新建会话
    clearSession, // 清空会话
    deletingId, // 删除中 ID
    removeSessionFromList, // 本地移除
    deleteSession, // 删除会话
    send, // 发送
    applyDraft, // 应用草稿
  } // 结束 return
} // 结束 useAssistantController
