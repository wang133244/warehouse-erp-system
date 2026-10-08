/** 拉取 ABC、周转、日报周报、拣货效率。 */
import { computed, onMounted, ref } from 'vue' // 引入 Vue 计算属性、生命周期与 ref
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { // 引入报表 API 与类型
  getAbcReport, // ABC 分类报表
  getDailyReport, // 日报
  getPickingEfficiency, // 拣货效率
  getTurnoverReport, // 周转报表
  getWeeklyReport, // 周报
  type AbcReportItem, // ABC 行类型
  type MovementReportItem, // 出入库日报/周报行
  type PickingEfficiency, // 拣货效率结构
  type TurnoverReportItem // 周转行类型
} from '../models/followup' // 来自 followup 模型

export function useReportsController() { // 报表页控制器
  const config = pageConfigs['/reports'] // 本页配置
  const abcItems = ref<AbcReportItem[]>([]) // ABC 数据
  const turnoverItems = ref<TurnoverReportItem[]>([]) // 周转数据
  const dailyItems = ref<MovementReportItem[]>([]) // 日报
  const weeklyItems = ref<MovementReportItem[]>([]) // 周报
  const picking = ref<PickingEfficiency | null>(null) // 拣货效率
  const basis = ref('') // ABC 计算口径
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const keyword = ref('') // 前端过滤关键字
  const days = ref(7) // 日报天数
  const weeks = ref(4) // 周报周数
  const emptyDescription = config.emptyDescription // 空态说明

  const matchesKeyword = (value: string | number | undefined) => { // 关键字是否匹配某字段
    const needle = keyword.value.trim().toLowerCase() // 规范化关键字
    if (!needle) return true // 空关键字视为全匹配
    return String(value ?? '').toLowerCase().includes(needle) // 包含即命中
  } // 结束 matchesKeyword
  const visibleAbc = computed(() => // 过滤后的 ABC
    abcItems.value.filter((item) => matchesKeyword(item.sku_code) || matchesKeyword(item.class)) // SKU 或分类匹配
  ) // 结束 visibleAbc
  const visibleTurnover = computed(() => // 过滤后的周转
    turnoverItems.value.filter((item) => matchesKeyword(item.sku_code)) // 按 SKU 过滤
  ) // 结束 visibleTurnover
  const visibleDaily = computed(() => dailyItems.value.filter((item) => matchesKeyword(item.date))) // 按日期过滤日报
  const visibleWeekly = computed(() => weeklyItems.value.filter((item) => matchesKeyword(item.week))) // 按周过滤周报

  const loadData = async () => { // 并行拉取全部报表
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求五类报表
      const [abc, turnover, daily, weekly, efficiency] = await Promise.all([ // 并行请求
        getAbcReport(), // ABC
        getTurnoverReport(), // 周转
        getDailyReport(days.value), // 日报
        getWeeklyReport(weeks.value), // 周报
        getPickingEfficiency() // 拣货效率
      ]) // 结束 Promise.all
      abcItems.value = abc.items // 写入 ABC
      basis.value = abc.basis // 写入口径
      turnoverItems.value = turnover.items // 写入周转
      dailyItems.value = daily.items // 写入日报
      weeklyItems.value = weekly.items // 写入周报
      picking.value = efficiency // 写入效率
    } catch (error) { // 任一失败则清空
      errorMessage.value = error instanceof Error ? error.message : '报表加载失败' // 记录错误
      abcItems.value = [] // 清空 ABC
      turnoverItems.value = [] // 清空周转
      dailyItems.value = [] // 清空日报
      weeklyItems.value = [] // 清空周报
      picking.value = null // 清空效率
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const refresh = async () => { // 手动刷新并提示
    await loadData() // 重新加载
    if (errorMessage.value) { // 加载出错
      ElMessage.error(errorMessage.value) // 弹出错误
      return // 不再提示成功
    } // 结束错误分支
    ElMessage.success('报表已刷新') // 成功提示
  } // 结束 refresh

  onMounted(loadData) // 挂载时加载

  const search = () => undefined // 关键字由 computed 即时过滤，搜索按钮无额外请求
  const reset = () => { // 重置筛选并重拉
    keyword.value = '' // 清空关键字
    days.value = 7 // 恢复日报天数
    weeks.value = 4 // 恢复周报周数
    loadData() // 重新加载
  } // 结束 reset

  return { // 暴露给视图
    config, // 页面配置
    abcItems, // ABC 原始数据
    turnoverItems, // 周转原始数据
    dailyItems, // 日报原始数据
    weeklyItems, // 周报原始数据
    picking, // 拣货效率
    basis, // ABC 口径
    loading, // 加载状态
    errorMessage, // 错误信息
    keyword, // 关键字
    days, // 日报天数
    weeks, // 周报周数
    emptyDescription, // 空态说明
    matchesKeyword, // 匹配函数
    visibleAbc, // 可见 ABC
    visibleTurnover, // 可见周转
    visibleDaily, // 可见日报
    visibleWeekly, // 可见周报
    loadData, // 刷新数据
    refresh, // 带提示刷新
    search, // 搜索占位
    reset, // 重置
  } // 结束 return
} // 结束 useReportsController
