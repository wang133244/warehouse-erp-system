/** 收货确认页：待收列表与实收数量。 */
import { onMounted, ref } from 'vue' // 引入 Vue 生命周期与 ref
import { ElMessage } from 'element-plus' // 引入提示消息
import { pageConfigs } from '../config/pages' // 引入页面配置
import { listLocations, listProducts, type Location, type Product } from '../models/catalog' // 商品与库位主数据
import { ApiError } from '../models/client' // API 错误类型
import { confirmReceiving, listReceivings, type ReceivingOrder } from '../models/operations' // 收货 API

export function useReceivingController() { // 收货确认页控制器
  const config = pageConfigs['/receiving'] // 本页配置
  const rows = ref<ReceivingOrder[]>([]) // 待收货单据
  const products = ref<Product[]>([]) // 商品缓存
  const locations = ref<Location[]>([]) // 库位缓存
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 错误文案
  const pendingId = ref<number | null>(null) // 正在确认的单据 ID
  const productName = (id: number) => products.value.find((item) => item.product_id === id)?.sku_code ?? `商品#${id}` // SKU 或回退编号
  const locationName = (id: number) => locations.value.find((item) => item.location_id === id)?.location_code ?? `库位#${id}` // 库位编码或回退
  const lineText = (row: ReceivingOrder) => // 拼明细摘要
    row.items.map((item) => `${productName(item.product_id)} / ${locationName(item.location_id)} × ${item.quantity}`).join('；') // 商品/库位×数量

  const loadData = async () => { // 加载待收货列表
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求列表
      const page = await listReceivings() // 拉取待收货
      rows.value = page.items // 写入表格
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      errorMessage.value = error instanceof Error ? error.message : '待收货记录加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const confirm = async (row: ReceivingOrder) => { // 确认一张收货单
    pendingId.value = row.inbound_order_id // 标记进行中单据
    try { // 提交确认
      await confirmReceiving(row.inbound_order_id, { // 按计划数量确认实收
        items: row.items.map((item) => ({ inbound_item_id: item.inbound_item_id, received_quantity: item.quantity })) // 明细实收量
      }) // 结束 confirmReceiving
      ElMessage.success('收货已确认') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 确认失败
      ElMessage.error(error instanceof ApiError ? error.message : '收货确认失败') // 错误提示
    } finally { // 无论成败
      pendingId.value = null // 清除进行中标记
    } // 结束 finally
  } // 结束 confirm

  onMounted(async () => { // 挂载时先拉主数据再拉列表
    const [productPage, locationPage] = await Promise.all([ // 并行拉商品和库位
      listProducts({ limit: 200 }).catch(() => ({ items: [] as Product[] })), // 商品失败则空列表
      listLocations({ limit: 200 }).catch(() => ({ items: [] as Location[] })) // 库位失败则空列表
    ]) // 结束 Promise.all
    products.value = productPage.items // 写入商品
    locations.value = locationPage.items // 写入库位
    await loadData() // 再拉待收货
  }) // 结束 onMounted

  return { // 暴露给视图
    config, // 页面配置
    rows, // 表格行
    products, // 商品
    locations, // 库位
    loading, // 加载状态
    errorMessage, // 错误信息
    pendingId, // 进行中单据
    productName, // 商品名映射
    locationName, // 库位名映射
    lineText, // 明细摘要
    loadData, // 刷新
    confirm, // 确认收货
  } // 结束 return
} // 结束 useReceivingController
