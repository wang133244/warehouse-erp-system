<!-- 新建调拨弹窗。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入响应式对象、引用与侦听器。
import { reactive, ref, watch } from 'vue' // import { reactive, r
// 校验失败时弹出警告或错误。
import { ElMessage } from 'element-plus' // import { ElMessage }
// 远程搜索商品/库位，以及按 ID 取商品。
import { listLocations, listProducts, getProduct, type Location, type Product } from '../../models/catalog' // import { listLocatio
// 按商品查可用库存余额。
import { listBalances, type InventoryBalance } from '../../models/inventory' // import { listBalance
// 调拨单与保存载荷类型。
import type { TransferOrder, TransferUpsert } from '../../models/warehouse-extensions' // import type { Transf

// 商品下拉选项：主键 + 展示编码。
interface ProductOption { // interface ProductOpt
  // 商品主键。
  product_id: number // product_id: number
  // 用于展示的商品编码。
  code: string // code: string
} // 结束代码块

// 源库位选项：带可用量。
interface SourceOption { // interface SourceOpti
  // 库位主键。
  location_id: number // location_id: number
  // 库位编码。
  location_code: string // location_code: strin
  // 该库位该商品的可用数量。
  available_quantity: number // available_quantity: 
} // 结束代码块

// 目标库位选项。
interface TargetOption { // interface TargetOpti
  // 库位主键。
  location_id: number // location_id: number
  // 库位编码。
  location_code: string // location_code: strin
} // 结束代码块

// 一行调拨明细的表单结构。
interface LineForm { // interface LineForm {
  // 商品。
  product_id: number | undefined // product_id: number |
  // 源库位。
  source_location_id: number | undefined // source_location_id: 
  // 目标库位。
  target_location_id: number | undefined // target_location_id: 
  // 调拨数量。
  quantity: number // quantity: number
  // 该商品当前可选的源库位。
  sourceOptions: SourceOption[] // sourceOptions: Sourc
} // 结束代码块

// 弹窗显隐、主数据、编辑初值、提交中。
const props = defineProps<{ // const props = define
  // 是否显示弹窗。
  modelValue: boolean // modelValue: boolean
  // 父组件传入的商品缓存。
  products: Product[] // products: Product[]
  // 父组件传入的库位缓存。
  locations: Location[] // locations: Location[
  // 编辑已有调拨单时的初值。
  initialValue?: TransferOrder | null // initialValue?: Trans
  // 保存请求进行中。
  submitting?: boolean // submitting?: boolean
}>() // 结束类型实参调用
// 同步显隐，以及提交调拨明细。
const emit = defineEmits<{ // const emit = defineE
  // 回写弹窗开关。
  'update:modelValue': [value: boolean] // 'update:modelValue':
  // 把调拨保存载荷交给父组件。
  submit: [payload: TransferUpsert] // submit: [payload: Tr
}>() // 结束类型实参调用

// 远程搜索累积的商品选项。
const productOptions = ref<ProductOption[]>([]) // const productOptions
// 远程搜索累积的目标库位选项。
const targetOptions = ref<TargetOption[]>([]) // const targetOptions 
// 商品下拉加载中。
const productLoading = ref(false) // const productLoading
// 目标库位下拉加载中。
const targetLoading = ref(false) // const targetLoading 
// 备注与明细行。
const form = reactive({ // const form = reactiv
  // 调拨备注。
  note: '', // note: '',
  // 默认一行空明细。
  items: [emptyLine()] // items: [emptyLine()]
}) // 结束调用

// 构造一行空明细。
function emptyLine(): LineForm { // function emptyLine()
  // 返回未选择商品/库位、数量为 1 的行。
  return { // return {
    // 未选商品。
    product_id: undefined, // product_id: undefine
    // 未选源库位。
    source_location_id: undefined, // source_location_id: 
    // 未选目标库位。
    target_location_id: undefined, // target_location_id: 
    // 默认调拨 1。
    quantity: 1, // quantity: 1,
    // 源库位选项稍后按商品加载。
    sourceOptions: [] // sourceOptions: []
  } // 结束代码块
} // 结束代码块

// 优先用来源商品编码，否则去掉 SKU 品牌后缀。
function productCode(item: { source_product_code?: string | null; sku_code?: string | null }) { // function productCode
  // 来源编码去空白。
  const source = (item.source_product_code || '').trim() // const source = (item
  // 有来源编码就用它。
  if (source) return source // if (source) return s
  // 否则去掉「-品牌N」后缀后的 SKU。
  return (item.sku_code || '').replace(/-品牌\d+$/u, '').trim() // return (item.sku_cod
} // 结束代码块

// 商品选项去重追加。
function upsertProductOption(option: ProductOption) { // function upsertProdu
  // 缺主键或编码则忽略。
  if (!option.product_id || !option.code) return // if (!option.product_
  // 已存在则不重复插入。
  if (productOptions.value.some((item) => item.product_id === option.product_id)) return // if (productOptions.v
  // 追加到选项列表。
  productOptions.value = [...productOptions.value, option] // productOptions.value
} // 结束代码块

// 目标库位选项去重追加。
function upsertTargetOption(option: TargetOption) { // function upsertTarge
  // 缺主键或编码则忽略。
  if (!option.location_id || !option.location_code) return // if (!option.location
  // 已存在则不重复插入。
  if (targetOptions.value.some((item) => item.location_id === option.location_id)) return // if (targetOptions.va
  // 追加到选项列表。
  targetOptions.value = [...targetOptions.value, option] // targetOptions.value 
} // 结束代码块

// 取当前行所选源库位的可用量。
function availableOf(item: LineForm) { // function availableOf
  // 找不到则视为 0。
  return item.sourceOptions.find((row) => row.location_id === item.source_location_id)?.available_quantity ?? 0 // return item.sourceOp
} // 结束代码块

// 按商品加载有可用库存的源库位。
async function loadSourceOptions(item: LineForm) { // async function loadS
  // 未选商品则清空源库位。
  if (!item.product_id) { // if (!item.product_id
    // 无选项。
    item.sourceOptions = [] // item.sourceOptions =
    // 结束。
    return // return
  } // 结束代码块
  // 只查该商品的可用余额。
  const page = await listBalances({ productId: item.product_id, availableOnly: true, limit: 200 }) // const page = await l
  // 映射成源库位选项。
  item.sourceOptions = page.items // item.sourceOptions =
    .map((row) => ({ // .map((row) => ({
      // 库位主键。
      location_id: row.location_id, // location_id: row.loc
      // 缺编码时用编号占位。
      location_code: row.location_code || `库位#${row.location_id}`, // location_code: row.l
      // 可用数量。
      available_quantity: row.available_quantity // available_quantity: 
    })) // 结束调用
  // 原选中库位已不在可用列表则清空。
  if (item.source_location_id && !item.sourceOptions.some((row) => row.location_id === item.source_location_id)) { // if (item.source_loca
    // 失效选择。
    item.source_location_id = undefined // item.source_location
  } // 结束代码块
} // 结束代码块

// 把库存余额行里的商品并入下拉。
function mergeBalanceProducts(rows: InventoryBalance[]) { // function mergeBalanc
  // 同一商品只插一次。
  const seen = new Set<number>() // const seen = new Set
  // 遍历余额行。
  for (const row of rows) { // for (const row of ro
    // 无可用量或已见过则跳过。
    if (row.available_quantity <= 0 || seen.has(row.product_id)) continue // if (row.available_qu
    // 标记已见。
    seen.add(row.product_id) // seen.add(row.product
    // 写入商品选项。
    upsertProductOption({ // upsertProductOption(
      // 商品主键。
      product_id: row.product_id, // product_id: row.prod
      // 展示编码，缺省用编号。
      code: productCode(row) || `商品#${row.product_id}` // code: productCode(ro
    }) // 结束调用
  } // 结束代码块
} // 结束代码块

// 远程搜索商品：空关键字时用有库存商品。
async function searchProducts(keyword: string) { // async function searc
  // 开始加载。
  productLoading.value = true // productLoading.value
  try { // try {
    // 去掉首尾空白。
    const query = keyword.trim() // const query = keywor
    // 无关键字：列出有可用库存的商品。
    if (!query) { // if (!query) {
      // 拉取可用余额。
      const page = await listBalances({ availableOnly: true, limit: 200 }) // const page = await l
      // 合并进选项。
      mergeBalanceProducts(page.items) // mergeBalanceProducts
      // 空搜结束。
      return // return
    } // 结束代码块
    // 同时搜商品主数据与有库存余额。
    const [products, balances] = await Promise.all([ // const [products, bal
      // 按关键字搜商品。
      listProducts({ keyword: query, limit: 50 }), // listProducts({ keywo
      // 按关键字搜可用余额。
      listBalances({ keyword: query, availableOnly: true, limit: 50 }) // listBalances({ keywo
    ]) // ])
    // 先合并有库存的。
    mergeBalanceProducts(balances.items) // mergeBalanceProducts
    // 再补上主数据命中。
    for (const product of products.items) { // for (const product o
      // 写入选项。
      upsertProductOption({ // upsertProductOption(
        // 商品主键。
        product_id: product.product_id, // product_id: product.
        // 展示编码。
        code: productCode(product) || String(product.product_id) // code: productCode(pr
      }) // 结束调用
    } // 结束代码块
  } finally { // } finally {
    // 无论成败结束加载。
    productLoading.value = false // productLoading.value
  } // 结束代码块
} // 结束代码块

// 远程搜索目标库位。
async function searchTargets(keyword: string) { // async function searc
  // 开始加载。
  targetLoading.value = true // targetLoading.value 
  try { // try {
    // 去掉首尾空白。
    const query = keyword.trim() // const query = keywor
    // 无关键字：拉一页库位。
    if (!query) { // if (!query) {
      // 默认前 50 个库位。
      const page = await listLocations({ limit: 50 }) // const page = await l
      // 写入选项。
      for (const location of page.items) { // for (const location 
        // 追加目标库位。
        upsertTargetOption({ location_id: location.location_id, location_code: location.location_code }) // upsertTargetOption({
      } // 结束代码块
      // 空搜结束。
      return // return
    } // 结束代码块
    // 按关键字搜库位。
    const page = await listLocations({ keyword: query, limit: 50 }) // const page = await l
    // 写入选项。
    for (const location of page.items) { // for (const location 
      // 追加目标库位。
      upsertTargetOption({ location_id: location.location_id, location_code: location.location_code }) // upsertTargetOption({
    } // 结束代码块
  } finally { // } finally {
    // 无论成败结束加载。
    targetLoading.value = false // targetLoading.value 
  } // 结束代码块
} // 结束代码块

// 切换商品时重置源库位并检查库存。
const onProductChange = async (item: LineForm) => { // const onProductChang
  // 清空源库位。
  item.source_location_id = undefined // item.source_location
  // 数量回到 1。
  item.quantity = 1 // item.quantity = 1
  // 加载该商品可用源库位。
  await loadSourceOptions(item) // await loadSourceOpti
  // 没有任何可用库位则报库存不足。
  if (!item.sourceOptions.length) { // if (!item.sourceOpti
    // 错误提示。
    ElMessage.error('库存不足') // ElMessage.error('库存不
  } // 结束代码块
} // 结束代码块

// 切换源库位时把数量压到可用上限。
const onSourceChange = (item: LineForm) => { // const onSourceChange
  // 当前可用量。
  const available = availableOf(item) // const available = av
  // 已填数量超过可用则下调。
  if (available > 0 && item.quantity > available) item.quantity = available // if (available > 0 &&
} // 结束代码块

// 打开弹窗时回填表单并补齐下拉选项。
async function hydrate() { // async function hydra
  // 回填备注。
  form.note = props.initialValue?.note ?? '' // form.note = props.in
  // 有明细则映射，否则一行空记录。
  const rows = props.initialValue?.items?.length // const rows = props.i
    // 把已有明细映射成表单行。
    ? props.initialValue.items.map((item) => ({ // ? props.initialValue
        // 商品。
        product_id: item.product_id, // product_id: item.pro
        // 源库位。
        source_location_id: item.source_location_id, // source_location_id: 
        // 目标库位。
        target_location_id: item.target_location_id, // target_location_id: 
        // 数量。
        quantity: item.quantity, // quantity: item.quant
        // 源库位选项稍后加载。
        sourceOptions: [] as SourceOption[] // sourceOptions: [] as
      })) // 结束调用
    // 无明细时放空行。
    : [emptyLine()] // : [emptyLine()]
  // 写入表单。
  form.items = rows // form.items = rows
  // 清空商品选项，随后重新搜。
  productOptions.value = [] // productOptions.value
  // 清空目标库位选项。
  targetOptions.value = [] // targetOptions.value 
  // 并行：默认商品、默认目标库位、以及每行补齐。
  await Promise.all([ // await Promise.all([
    // 预加载有库存商品。
    searchProducts(''), // searchProducts(''),
    // 预加载目标库位。
    searchTargets(''), // searchTargets(''),
    // 每一行补源库位、商品名、目标库位。
    ...form.items.map(async (item) => { // ...form.items.map(as
      // 已选商品则加载源库位并保证选项存在。
      if (item.product_id) { // if (item.product_id)
        // 加载可用源库位。
        await loadSourceOptions(item) // await loadSourceOpti
        // 先从父组件缓存找商品。
        const known = props.products.find((product) => product.product_id === item.product_id) // const known = props.
        // 缓存命中则直接写入选项。
        if (known) { // if (known) {
          // 用缓存商品编码。
          upsertProductOption({ // upsertProductOption(
            // 商品主键。
            product_id: item.product_id, // product_id: item.pro
            // 展示编码。
            code: productCode(known) || String(item.product_id) // code: productCode(kn
          }) // 结束调用
        } else { // } else {
          // 缓存没有则按 ID 拉商品。
          try { // try {
            // 请求商品详情。
            const product = await getProduct(item.product_id) // const product = awai
            // 写入选项。
            upsertProductOption({ // upsertProductOption(
              // 商品主键。
              product_id: product.product_id, // product_id: product.
              // 展示编码。
              code: productCode(product) || String(product.product_id) // code: productCode(pr
            }) // 结束调用
          } catch { // } catch {
            // 详情失败时至少用 ID 占位。
            upsertProductOption({ product_id: item.product_id, code: String(item.product_id) }) // upsertProductOption(
          } // 结束代码块
        } // 结束代码块
      } // 结束代码块
      // 源库位不在可用列表时，用父组件库位缓存补一条（可用量记 0）。
      if (item.source_location_id && !item.sourceOptions.some((row) => row.location_id === item.source_location_id)) { // if (item.source_loca
        // 从缓存找库位。
        const location = props.locations.find((row) => row.location_id === item.source_location_id) // const location = pro
        // 找到则追加，避免下拉空白。
        if (location) { // if (location) {
          // 拼到源库位选项末尾。
          item.sourceOptions = [ // item.sourceOptions =
            // 保留已有可用库位。
            ...item.sourceOptions, // ...item.sourceOption
            // 补一条当前选中库位。
            { location_id: location.location_id, location_code: location.location_code, available_quantity: 0 } // { location_id: locat
          ] // ]
        } // 结束代码块
      } // 结束代码块
      // 已选目标库位时保证选项存在。
      if (item.target_location_id) { // if (item.target_loca
        // 从缓存取编码。
        const location = props.locations.find((row) => row.location_id === item.target_location_id) // const location = pro
        // 写入目标选项。
        upsertTargetOption({ // upsertTargetOption({
          // 目标库位主键。
          location_id: item.target_location_id, // location_id: item.ta
          // 缺编码时用编号占位。
          location_code: location?.location_code || `库位#${item.target_location_id}` // location_code: locat
        }) // 结束调用
      } // 结束代码块
    }) // 结束调用
  ]) // ])
} // 结束代码块

// 弹窗打开时执行回填。
watch( // watch(
  // 侦听显隐。
  () => props.modelValue, // () => props.modelVal
  // 打开时异步 hydrate。
  (visible) => { // (visible) => {
    // 可见才回填。
    if (visible) void hydrate() // if (visible) void hy
  } // 结束代码块
) // 结束括号

// 追加一行空明细。
const addRow = () => { // const addRow = () =>
  // 推入空行。
  form.items.push(emptyLine()) // form.items.push(empt
} // 结束代码块
// 按索引删除一行。
const removeRow = (index: number) => { // const removeRow = (i
  // 从明细数组移除。
  form.items.splice(index, 1) // form.items.splice(in
} // 结束代码块
// 校验并提交调拨明细。
const submit = () => { // const submit = () =>
  // 只保留商品、源、目标都选了的行。
  const items = form.items.filter((item) => item.product_id && item.source_location_id && item.target_location_id) // const items = form.i
  // 至少要有一行有效明细。
  if (!items.length) { // if (!items.length) {
    // 提示补录。
    ElMessage.warning('请至少录入一行调拨明细') // ElMessage.warning('请
    // 中止。
    return // return
  } // 结束代码块
  // 源与目标不能相同。
  if (items.some((item) => item.source_location_id === item.target_location_id)) { // if (items.some((item
    // 提示库位相同。
    ElMessage.warning('源库位和目标库位不能相同') // ElMessage.warning('源
    // 中止。
    return // return
  } // 结束代码块
  // 用「商品-源-目标」拼成去重键。
  const keys = items.map((item) => `${item.product_id}-${item.source_location_id}-${item.target_location_id}`) // const keys = items.m
  // 存在重复行则拒绝。
  if (new Set(keys).size !== keys.length) { // if (new Set(keys).si
    // 提示重复。
    ElMessage.warning('调拨明细中存在重复行') // ElMessage.warning('调
    // 中止。
    return // return
  } // 结束代码块
  // 数量必须在 1 到可用量之间。
  if (items.some((item) => Number(item.quantity) > availableOf(item) || Number(item.quantity) < 1)) { // if (items.some((item
    // 库存不足。
    ElMessage.error('库存不足') // ElMessage.error('库存不
    // 中止。
    return // return
  } // 结束代码块
  // 把表单转成后端载荷。
  emit('submit', { // emit('submit', {
    // 空备注写成 null。
    note: form.note || null, // note: form.note || n
    // 主键与数量转成数字。
    items: items.map((item) => ({ // items: items.map((it
      // 商品。
      product_id: Number(item.product_id), // product_id: Number(i
      // 源库位。
      source_location_id: Number(item.source_location_id), // source_location_id: 
      // 目标库位。
      target_location_id: Number(item.target_location_id), // target_location_id: 
      // 调拨数量。
      quantity: Number(item.quantity) // quantity: Number(ite
    })) // 结束调用
  }) // 结束调用
} // 结束代码块
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 调拨单弹窗。 -->
  <el-dialog :model-value="modelValue" title="调拨单" width="980px" @update:model-value="emit('update:modelValue', $event)"> <!-- <el-dialog :model-va -->
    <!-- 审批流程与选品说明。 -->
    <p class="hint">提交后需要审批中心审核，通过后才能执行。请先选有库存的商品编码，源库位只列出可用库存。</p> <!-- <p class="hint">提交后需 -->
    <!-- 调拨表单。 -->
    <el-form label-width="80px"> <!-- <el-form label-width -->
      <!-- 备注。 -->
      <el-form-item label="备注"><el-input v-model="form.note" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 每一行明细：商品、源库位、目标库位、数量、删除。 -->
      <div v-for="(item, index) in form.items" :key="index" class="line"> <!-- <div v-for="(item, i -->
        <!-- 远程搜索有库存的商品编码。 -->
        <el-select
          v-model="item.product_id"
          placeholder="商品编码"
          filterable
          remote
          :remote-method="searchProducts"
          :loading="productLoading"
          @change="onProductChange(item)"
        > <!-- > -->
          <!-- 商品选项。 -->
          <el-option v-for="product in productOptions" :key="product.product_id" :label="product.code" :value="product.product_id" /> <!-- <el-option v-for="pr -->
        </el-select> <!-- 结束 el-select -->
        <!-- 源库位，标签带可用量。 -->
        <el-select v-model="item.source_location_id" placeholder="源库位" filterable @change="onSourceChange(item)"> <!-- <el-select v-model=" -->
          <!-- 每个可用源库位一个选项。 -->
          <el-option
            v-for="location in item.sourceOptions"
            :key="location.location_id"
            :label="`${location.location_code}（可用 ${location.available_quantity}）`"
            :value="location.location_id"
          /> <!-- /> -->
        </el-select> <!-- 结束 el-select -->
        <!-- 远程搜索目标库位。 -->
        <el-select
          v-model="item.target_location_id"
          placeholder="目标库位"
          filterable
          remote
          :remote-method="searchTargets"
          :loading="targetLoading"
        > <!-- > -->
          <!-- 目标库位选项，key 加 t- 前缀避免与源库位冲突。 -->
          <el-option v-for="location in targetOptions" :key="`t-${location.location_id}`" :label="location.location_code" :value="location.location_id" /> <!-- <el-option v-for="lo -->
        </el-select> <!-- 结束 el-select -->
        <!-- 数量上限为当前可用量。 -->
        <el-input-number v-model="item.quantity" :min="1" :max="Math.max(availableOf(item), 1)" /> <!-- <el-input-number v-m -->
        <!-- 删除当前行。 -->
        <el-button text @click="removeRow(index)">删除</el-button> <!-- <el-button text @cli -->
      </div> <!-- 结束 div -->
      <!-- 追加明细行。 -->
      <el-button @click="addRow">增加明细</el-button> <!-- <el-button @click="a -->
    </el-form> <!-- 结束 el-form -->
    <!-- 底部操作槽。 -->
    <template #footer> <!-- 页面模板 -->
      <!-- 关闭弹窗。 -->
      <el-button @click="emit('update:modelValue', false)">取消</el-button> <!-- <el-button @click="e -->
      <!-- 保存调拨单。 -->
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button> <!-- <el-button type="pri -->
    </template> <!-- 结束 template -->
  </el-dialog> <!-- 结束 el-dialog -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 流程说明小号灰色。 */
.hint { color: var(--muted); font-size: 12px; margin: 0 0 12px; } /* .hint { color: var(- */
/* 明细行五列网格：商品、源、目标、数量、删除。 */
.line { display: grid; grid-template-columns: 1.2fr 1.4fr 1fr 120px auto; gap: 8px; margin-bottom: 8px; align-items: center; } /* .line { display: gri */
</style> <!-- 结束 style -->
