/** 某一导入批次的校验明细。 */
import { computed, onMounted, ref } from 'vue' // 引入 Vue 组合式 API
import { useRoute, useRouter } from 'vue-router' // 引入路由与路由器
import { ElMessage } from 'element-plus' // 引入消息提示（本页暂未直接调用）
import { getImport, type ImportBatch } from '../models/catalog' // 引入导入批次查询与类型
import { ApiError } from '../models/client' // 引入 API 错误类型

export function useImportDetailController() { // 导入详情页控制器
  const route = useRoute() // 当前路由
  const router = useRouter() // 路由器实例
  const loading = ref(false) // 加载中标志
  const errorMessage = ref('') // 错误文案
  const batch = ref<ImportBatch | null>(null) // 当前批次数据
  const batchId = computed(() => Number(route.params.batchId)) // 从路由解析批次 ID

  const load = async () => { // 加载批次详情
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求批次
      batch.value = await getImport(batchId.value) // 按 ID 拉取导入批次
    } catch (error) { // 加载失败
      batch.value = null // 清空批次
      errorMessage.value = error instanceof ApiError ? error.message : '导入批次加载失败' // 记录错误信息
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 load

  onMounted(load) // 挂载时自动加载

  return { // 暴露给视图
    route, // 路由对象
    router, // 路由器
    loading, // 加载状态
    errorMessage, // 错误信息
    batch, // 批次详情
    batchId, // 批次 ID
    load, // 手动刷新
  } // 结束 return
} // 结束 useImportDetailController
