/** 出库复核，复核通过后才完成扣账。 */
import { onMounted, ref } from 'vue' // 引入 Vue 生命周期与 ref
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { ApiError } from '../models/client' // API 错误类型
import { completeOutbound, listOutboundReviews, reviewOutbound, type OutboundReviewRow } from '../models/operations' // 复核与完成出库 API

export function useOutboundReviewController() { // 出库复核页控制器
  const config = pageConfigs['/outbound-review'] // 本页配置
  const rows = ref<OutboundReviewRow[]>([]) // 待复核/已复核行
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const keyword = ref('') // 搜索关键字
  const pendingId = ref<number | null>(null) // 正在操作的出库单 ID
  const statusText = (status: string) => ({ picked: '待复核', reviewed: '已复核' }[status] ?? status) // 状态中文
  const reviewQuantity = (row: OutboundReviewRow) => row.items.reduce((sum, item) => sum + item.quantity, 0) // 复核数量合计

  const loadData = async () => { // 加载复核列表
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求列表
      const page = await listOutboundReviews({ keyword: keyword.value.trim() || undefined }) // 按关键字查询
      rows.value = page.items // 写入表格
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      errorMessage.value = error instanceof Error ? error.message : '待复核记录加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const review = async (row: OutboundReviewRow) => { // 复核一张出库单
    pendingId.value = row.outbound_order_id // 标记进行中单据
    try { // 提交复核
      await reviewOutbound(row.outbound_order_id, '拣货数量与客户信息已核对') // 固定复核意见
      ElMessage.success('出库复核完成') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 复核失败
      ElMessage.error(error instanceof ApiError ? error.message : '复核失败') // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除进行中标记
    } // 结束 finally
  } // 结束 review

  const complete = async (row: OutboundReviewRow) => { // 复核后完成出库扣账
    pendingId.value = row.outbound_order_id // 标记进行中单据
    try { // 提交完成
      await completeOutbound(row.outbound_order_id) // 调用完成接口
      ElMessage.success('出库已完成') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 完成失败
      ElMessage.error(error instanceof ApiError ? error.message : '完成出库失败') // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除进行中标记
    } // 结束 finally
  } // 结束 complete

  onMounted(loadData) // 挂载时加载

  const search = () => { // 按关键字搜索
    loadData() // 重新加载
  } // 结束 search
  const reset = () => { // 重置筛选
    keyword.value = '' // 清空关键字
    loadData() // 重新加载
  } // 结束 reset

  return { // 暴露给视图
    config, // 页面配置
    rows, // 表格行
    loading, // 加载状态
    errorMessage, // 错误信息
    keyword, // 关键字
    pendingId, // 进行中单据
    statusText, // 状态文案
    reviewQuantity, // 复核数量
    loadData, // 刷新
    review, // 复核
    complete, // 完成出库
    search, // 搜索
    reset, // 重置
  } // 结束 return
} // 结束 useOutboundReviewController
