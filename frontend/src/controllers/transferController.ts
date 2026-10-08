/** 调拨页；可消费助手草稿。 */
import { computed, onMounted, ref } from 'vue' // 引入 Vue 计算属性、生命周期与 ref
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { listLocations, listProducts, type Location, type Product } from '../models/catalog' // 商品与库位主数据
import { ApiError } from '../models/client' // API 错误类型
import { // 调拨 API
  createTransfer, // 新建调拨单
  executeTransfer, // 执行调拨
  listTransfers, // 列表
  saveTransfer, // 保存
  submitTransfer, // 提交审批
  type TransferOrder, // 调拨单类型
  type TransferUpsert // 保存载荷
} from '../models/warehouse-extensions' // 来自仓库扩展模型
import { useAppStore } from '../stores/app' // 角色与登录态

export function useTransferController() { // 调拨页控制器
  const PENDING_STATUSES = 'draft,pending_approval,executable' // 待处理状态集合
  const HISTORY_STATUSES = 'completed,rejected' // 历史状态集合
  const config = pageConfigs['/transfer'] // 本页配置
  const app = useAppStore() // 应用仓库
  const rows = ref<TransferOrder[]>([]) // 调拨单列表
  const products = ref<Product[]>([]) // 商品缓存
  const locations = ref<Location[]>([]) // 库位缓存
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const keyword = ref('') // 单号关键字
  const listView = ref<'pending' | 'history'>('pending') // 待处理/历史视图
  const dialogVisible = ref(false) // 新建/编辑弹窗
  const editing = ref<TransferOrder | null>(null) // 正在编辑的单据
  const submitting = ref(false) // 弹窗提交中
  const pendingId = ref<number | null>(null) // 行操作进行中 ID
  const canWrite = computed(() => { // 是否可写调拨
    const roles = app.currentUser?.roles ?? [] // 当前角色
    return roles.includes('admin') || roles.includes('warehouse_operator') // 管理员或操作员可写
  }) // 结束 canWrite
  const statusText = (status: string) => // 状态中文
    ({ // 状态字典
      draft: '草稿', // 草稿
      pending_approval: '待审批', // 待审批
      executable: '可执行', // 可执行
      completed: '已完成', // 已完成
      rejected: '已驳回' // 已驳回
    }[status] ?? status) // 未知状态原样返回
  const locationName = (id: number) => locations.value.find((item) => item.location_id === id)?.location_code ?? `库位#${id}` // 库位编码
  const lineText = (row: TransferOrder) => // 明细摘要
    (row.items ?? []).map((item) => `${locationName(item.source_location_id)} → ${locationName(item.target_location_id)} × ${item.quantity}`).join('；') || '-' // 源→目标×数量

  const loadData = async () => { // 按当前视图加载调拨单
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求列表
      const page = await listTransfers({ // 查询参数
        page: 1, // 第一页
        pageSize: 50, // 每页 50
        orderNo: keyword.value.trim() || undefined, // 单号过滤
        status: listView.value === 'history' ? HISTORY_STATUSES : PENDING_STATUSES // 按视图选状态
      }) // 结束 listTransfers
      rows.value = page.items // 写入表格
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      errorMessage.value = error instanceof Error ? error.message : '调拨单加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const switchView = (view: 'pending' | 'history') => { // 切换待处理/历史
    listView.value = view // 更新视图
    loadData() // 重新加载
  } // 结束 switchView

  const openCreate = () => { // 打开新建弹窗
    editing.value = null // 非编辑
    dialogVisible.value = true // 显示弹窗
  } // 结束 openCreate

  const openEdit = (row: TransferOrder) => { // 打开编辑弹窗
    editing.value = row // 记住单据
    dialogVisible.value = true // 显示弹窗
  } // 结束 openEdit

  const submitDialog = async (payload: TransferUpsert) => { // 保存弹窗
    submitting.value = true // 开始提交
    try { // 新建或更新
      if (editing.value) await saveTransfer(editing.value.transfer_order_id, payload) // 更新
      else await createTransfer(payload) // 新建
      dialogVisible.value = false // 关闭弹窗
      ElMessage.success('调拨单已保存') // 成功提示
      await loadData() // 刷新
    } catch (error) { // 保存失败
      ElMessage.error(inventoryErrorText(error, '保存失败')) // 库存不足等友好文案
    } finally { // 无论成败
      submitting.value = false // 结束提交
    } // 结束 finally
  } // 结束 submitDialog

  const submitRow = async (row: TransferOrder) => { // 提交审批
    pendingId.value = row.transfer_order_id // 标记进行中
    try { // 调用提交
      await submitTransfer(row.transfer_order_id) // 提交接口
      ElMessage.success('调拨单已提交，请到审批中心审核') // 引导去审批
      await loadData() // 刷新
    } catch (error) { // 提交失败
      ElMessage.error(inventoryErrorText(error, '提交失败')) // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除标记
    } // 结束 finally
  } // 结束 submitRow

  const inventoryErrorText = (error: unknown, fallback: string) => { // 把库存不足转成中文
    if (error instanceof ApiError && error.code === 'INVENTORY_INSUFFICIENT') return '库存不足' // 专用错误码
    return error instanceof ApiError ? error.message : fallback // 其他走接口消息或回退
  } // 结束 inventoryErrorText

  const executeRow = async (row: TransferOrder) => { // 审批通过后执行调拨
    pendingId.value = row.transfer_order_id // 标记进行中
    try { // 调用执行
      await executeTransfer(row.transfer_order_id) // 执行接口
      ElMessage.success('调拨已执行') // 成功提示
      await loadData() // 刷新
    } catch (error) { // 执行失败
      ElMessage.error(inventoryErrorText(error, '执行失败')) // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除标记
    } // 结束 finally
  } // 结束 executeRow

  onMounted(async () => { // 挂载时拉主数据再拉列表
    const [productPage, locationPage] = await Promise.all([ // 并行请求
      listProducts({ limit: 200 }).catch(() => ({ items: [] as Product[] })), // 商品失败则空
      listLocations({ limit: 200 }).catch(() => ({ items: [] as Location[] })) // 库位失败则空
    ]) // 结束 Promise.all
    products.value = productPage.items // 写入商品
    locations.value = locationPage.items // 写入库位
    await loadData() // 加载调拨单
  }) // 结束 onMounted

  const search = () => { // 搜索
    loadData() // 重新加载
  } // 结束 search
  const reset = () => { // 重置
    keyword.value = '' // 清空关键字
    loadData() // 重新加载
  } // 结束 reset

  return { // 暴露给视图
    PENDING_STATUSES, // 待处理状态
    HISTORY_STATUSES, // 历史状态
    config, // 页面配置
    app, // 应用仓库
    rows, // 表格行
    products, // 商品
    locations, // 库位
    loading, // 加载状态
    errorMessage, // 错误信息
    keyword, // 关键字
    listView, // 当前视图
    dialogVisible, // 弹窗可见
    editing, // 编辑中单据
    submitting, // 弹窗提交中
    pendingId, // 行操作 ID
    canWrite, // 是否可写
    statusText, // 状态文案
    locationName, // 库位名
    lineText, // 明细摘要
    loadData, // 刷新
    switchView, // 切换视图
    openCreate, // 新建
    openEdit, // 编辑
    submitDialog, // 保存弹窗
    submitRow, // 提交行
    inventoryErrorText, // 错误文案
    executeRow, // 执行调拨
    search, // 搜索
    reset, // 重置
  } // 结束 return
} // 结束 useTransferController
