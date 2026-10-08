/** 盘点页；可消费助手 pendingDraft。 */
import { computed, onMounted, ref } from 'vue' // 引入 Vue 计算属性、生命周期与 ref
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { listLocations, listProducts, type Location, type Product } from '../models/catalog' // 商品与库位主数据
import { ApiError } from '../models/client' // API 错误类型
import { // 盘点 API
  createStockCount, // 新建盘点单
  listStockCounts, // 列表
  saveStockCount, // 保存
  submitStockCount, // 提交审批
  type StockCountOrder, // 盘点单类型
  type StockCountUpsert // 保存载荷
} from '../models/warehouse-extensions' // 来自仓库扩展模型
import { useAppStore } from '../stores/app' // 角色与助手草稿

export function useStockCountController() { // 盘点页控制器
  const config = pageConfigs['/counting'] // 本页配置
  const app = useAppStore() // 应用仓库
  const rows = ref<StockCountOrder[]>([]) // 盘点单列表
  const products = ref<Product[]>([]) // 商品缓存
  const locations = ref<Location[]>([]) // 库位缓存
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const keyword = ref('') // 单号关键字
  const dialogVisible = ref(false) // 新建/编辑弹窗
  const editing = ref<StockCountOrder | null>(null) // 正在编辑的单据
  const submitting = ref(false) // 弹窗提交中
  const pendingId = ref<number | null>(null) // 行操作进行中 ID
  const canWrite = computed(() => { // 是否可写盘点
    const roles = app.currentUser?.roles ?? [] // 当前角色
    return roles.includes('admin') || roles.includes('warehouse_manager') || roles.includes('warehouse_operator') || roles.includes('operator') // 管理或操作员可写
  }) // 结束 canWrite
  const statusText = (status: string) => // 状态中文映射
    ({ // 状态字典
      draft: '草稿', // 草稿
      counting: '盘点中', // 盘点中
      pending_approval: '待审批', // 待审批
      completed: '已完成', // 已完成
      applied: '已过账', // 已过账
      rejected: '已驳回' // 已驳回
    }[status] ?? status) // 未知状态原样返回
  const productName = (id: number) => products.value.find((item) => item.product_id === id)?.sku_code ?? `商品#${id}` // SKU 或回退
  const locationName = (id: number) => locations.value.find((item) => item.location_id === id)?.location_code ?? `库位#${id}` // 库位或回退
  const lineText = (row: StockCountOrder) => // 明细摘要
    (row.items ?? []).map((item) => `${productName(item.product_id)} / ${locationName(item.location_id)} 实盘 ${item.counted_quantity}`).join('；') || '-' // 无明细显示横杠

  const loadData = async () => { // 加载盘点单
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求列表
      const page = await listStockCounts({ page: 1, pageSize: 50, orderNo: keyword.value.trim() || undefined }) // 按单号查询
      rows.value = page.items // 写入表格
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      errorMessage.value = error instanceof Error ? error.message : '盘点单加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const openCreate = () => { // 打开新建弹窗
    editing.value = null // 非编辑模式
    dialogVisible.value = true // 显示弹窗
  } // 结束 openCreate

  const openEdit = (row: StockCountOrder) => { // 打开编辑弹窗
    editing.value = row // 记住当前单据
    dialogVisible.value = true // 显示弹窗
  } // 结束 openEdit

  const submitDialog = async (payload: StockCountUpsert) => { // 保存弹窗内容
    submitting.value = true // 开始提交
    try { // 新建或更新
      if (editing.value) await saveStockCount(editing.value.stock_count_order_id, payload) // 更新已有单
      else await createStockCount(payload) // 新建
      dialogVisible.value = false // 关闭弹窗
      ElMessage.success('盘点单已保存') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 保存失败
      ElMessage.error(error instanceof ApiError ? error.message : '保存失败') // 错误提示
    } finally { // 无论成败
      submitting.value = false // 结束提交
    } // 结束 finally
  } // 结束 submitDialog

  const submitRow = async (row: StockCountOrder) => { // 提交盘点单去审批
    pendingId.value = row.stock_count_order_id // 标记进行中单据
    try { // 调用提交
      await submitStockCount(row.stock_count_order_id) // 提交接口
      ElMessage.success('盘点单已提交') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 提交失败
      ElMessage.error(error instanceof ApiError ? error.message : '提交失败') // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除进行中标记
    } // 结束 finally
  } // 结束 submitRow

  onMounted(async () => { // 挂载时拉主数据、列表，并消费草稿
    const [productPage, locationPage] = await Promise.all([ // 并行拉商品库位
      listProducts({ limit: 200 }).catch(() => ({ items: [] as Product[] })), // 商品失败则空
      listLocations({ limit: 200 }).catch(() => ({ items: [] as Location[] })) // 库位失败则空
    ]) // 结束 Promise.all
    products.value = productPage.items // 写入商品
    locations.value = locationPage.items // 写入库位
    await loadData() // 加载盘点单
    const draft = app.pendingDraft // 读取助手草稿
    if (draft?.type === 'counting') { // 盘点类草稿
      app.consumePendingDraft() // 消费以免重复打开
      dialogVisible.value = true // 打开新建弹窗
      ElMessage.success('已打开盘点单草稿，请核对后保存。') // 提示用户核对
    } // 结束草稿分支
  }) // 结束 onMounted

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
    products, // 商品
    locations, // 库位
    loading, // 加载状态
    errorMessage, // 错误信息
    keyword, // 关键字
    dialogVisible, // 弹窗可见
    editing, // 编辑中单据
    submitting, // 弹窗提交中
    pendingId, // 行操作 ID
    canWrite, // 是否可写
    statusText, // 状态文案
    productName, // 商品名
    locationName, // 库位名
    lineText, // 明细摘要
    loadData, // 刷新
    openCreate, // 新建
    openEdit, // 编辑
    submitDialog, // 保存弹窗
    submitRow, // 提交行
    search, // 搜索
    reset, // 重置
  } // 结束 return
} // 结束 useStockCountController
