/** 审批列表、同意、驳回。 */
import { computed, onMounted, ref } from 'vue' // 引入 Vue 计算属性、生命周期与 ref
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { ApiError } from '../models/client' // API 错误类型
import { approveApproval, listApprovals, rejectApproval, type ApprovalTask } from '../models/warehouse-extensions' // 审批 API
import { useAppStore } from '../stores/app' // 当前用户与角色

export function useApprovalController() { // 审批中心控制器
  const config = pageConfigs['/approvals'] // 本页配置
  const app = useAppStore() // 应用仓库
  const rows = ref<ApprovalTask[]>([]) // 待审批任务
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const keyword = ref('') // 单号关键字
  const dialogVisible = ref(false) // 决策弹窗
  const current = ref<ApprovalTask | null>(null) // 当前处理的任务
  const pendingId = ref<number | null>(null) // 正在提交的任务 ID
  const canDecide = computed(() => { // 是否具备审批角色
    const roles = app.currentUser?.roles ?? [] // 当前角色
    return roles.includes('admin') || roles.includes('warehouse_manager') // 管理员或仓管可批
  }) // 结束 canDecide
  const canHandle = (row: ApprovalTask) => { // 不能自己批自己（管理员除外）
    const roles = app.currentUser?.roles ?? [] // 当前角色
    if (roles.includes('admin')) return true // 管理员可处理任意任务
    return row.requested_by !== app.currentUser?.user_id // 非本人申请才可处理
  } // 结束 canHandle
  const statusText = (status: string) => ({ pending: '待审批', approved: '已同意', rejected: '已驳回' }[status] ?? status) // 状态中文
  const typeText = (type: string) => ({ stock_count: '盘点差异', transfer: '调拨' }[type] ?? type) // 业务类型中文

  const loadData = async () => { // 加载待审批列表
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求列表
      const page = await listApprovals({ page: 1, pageSize: 50, status: 'pending', orderNo: keyword.value.trim() || undefined }) // 只拉待审批
      rows.value = page.items // 写入表格
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      errorMessage.value = error instanceof Error ? error.message : '审批任务加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const openDecision = (row: ApprovalTask) => { // 打开审批弹窗
    current.value = row // 记住当前任务
    dialogVisible.value = true // 显示弹窗
  } // 结束 openDecision

  const decide = async (payload: { action: 'approve' | 'reject'; comment: string }) => { // 同意或驳回
    if (!current.value) return // 没有选中任务则退出
    pendingId.value = current.value.approval_task_id // 标记进行中任务
    try { // 提交决策
      if (payload.action === 'approve') await approveApproval(current.value.approval_task_id, payload.comment || undefined) // 同意
      else await rejectApproval(current.value.approval_task_id, payload.comment) // 驳回需意见
      dialogVisible.value = false // 关闭弹窗
      ElMessage.success(payload.action === 'approve' ? '已同意' : '已驳回') // 结果提示
      await loadData() // 刷新列表
    } catch (error) { // 审批失败
      ElMessage.error(error instanceof ApiError ? error.message : '审批失败') // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除进行中标记
    } // 结束 finally
  } // 结束 decide

  onMounted(loadData) // 挂载时加载

  const search = () => { // 按单号搜索
    loadData() // 重新加载
  } // 结束 search
  const reset = () => { // 重置筛选
    keyword.value = '' // 清空关键字
    loadData() // 重新加载
  } // 结束 reset

  return { // 暴露给视图
    config, // 页面配置
    app, // 应用仓库
    rows, // 表格行
    loading, // 加载状态
    errorMessage, // 错误信息
    keyword, // 关键字
    dialogVisible, // 弹窗可见
    current, // 当前任务
    pendingId, // 进行中任务
    canDecide, // 是否可审批
    canHandle, // 单行是否可处理
    statusText, // 状态文案
    typeText, // 类型文案
    loadData, // 刷新
    openDecision, // 打开弹窗
    decide, // 提交决策
    search, // 搜索
    reset, // 重置
  } // 结束 return
} // 结束 useApprovalController
