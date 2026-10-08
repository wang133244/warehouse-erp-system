<!-- 新建入出库等作业弹窗。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入计算属性、响应式对象与侦听器。
import { computed, reactive, watch } from 'vue' // import { computed, r
// 校验失败时弹出警告。
import { ElMessage } from 'element-plus' // import { ElMessage }
// 商品与库位类型。
import type { Location, Product } from '../../models/catalog' // import type { Locati
// 作业提交载荷类型。
import type { OperationSubmission } from '../../models/operations' // import type { Operat
// 助手草稿类型。
import type { OperationDraft } from '../../stores/app' // import type { Operat

// 弹窗显隐、动作名、页面标题、主数据与可选草稿。
const props = withDefaults( // const props = withDe
  defineProps<{ // 声明组件入参类型
    // 是否显示弹窗。
    modelValue: boolean // modelValue: boolean
    // 当前动作文案，如「新建入库」。
    action: string // action: string
    // 所属页面标题。
    pageTitle: string // pageTitle: string
    // 可选商品。
    products?: Product[] // products?: Product[]
    // 可选库位。
    locations?: Location[] // locations?: Location
    // 助手带入的草稿。
    draft?: OperationDraft | null // draft?: OperationDra
  }>(), // 结束类型实参调用
  { // 开始对象
    // 商品默认空数组。
    products: () => [], // products: () => [],
    // 库位默认空数组。
    locations: () => [], // locations: () => [],
    // 默认无草稿。
    draft: null // draft: null
  } // 结束代码块
) // 结束括号
// 同步显隐，以及提交入出库。
const emit = defineEmits<{ // const emit = defineE
  // 回写弹窗开关。
  'update:modelValue': [value: boolean] // 'update:modelValue':
  // 把作业载荷交给父组件。
  submit: [submission: OperationSubmission] // submit: [submission:
}>() // 结束类型实参调用

// 动作名包含「入库」则渲染入库表单。
const isInboundForm = computed(() => props.action.includes('入库')) // const isInboundForm 
// 动作名包含「出库」则渲染出库表单。
const isOutboundForm = computed(() => props.action.includes('出库')) // const isOutboundForm
// 入出库都属于可写操作。
const isWriteAction = computed(() => isInboundForm.value || isOutboundForm.value) // const isWriteAction 

// 入库表单。
const inboundForm = reactive({ // const inboundForm = 
  // 入库单号。
  order_no: '', // order_no: '',
  // 商品。
  product_id: undefined as number | undefined, // product_id: undefine
  // 收货库位。
  location_id: undefined as number | undefined, // location_id: undefin
  // 数量。
  quantity: 1, // quantity: 1,
  // 备注。
  note: '' // note: ''
}) // 结束调用

// 出库表单。
const outboundForm = reactive({ // const outboundForm =
  // 出库单号。
  order_no: '', // order_no: '',
  // 客户编号。
  customer_id: undefined as number | undefined, // customer_id: undefin
  // 商品。
  product_id: undefined as number | undefined, // product_id: undefine
  // 需求数量。
  quantity: 1, // quantity: 1,
  // 备注。
  note: '' // note: ''
}) // 结束调用

// 启用商品转成下拉选项。
const productOptions = computed(() => // const productOptions
  props.products // props.products
    // 过滤停用商品。
    .filter((product) => product.is_active !== false) // .filter((product) =>
    // SKU + 名称作为标签。
    .map((product) => ({ // .map((product) => ({
      // 商品主键。
      value: product.product_id, // value: product.produ
      // 展示文案。
      label: `${product.sku_code} · ${product.product_name}` // label: `${product.sk
    })) // 结束调用
) // 结束括号
// 启用库位转成下拉选项。
const locationOptions = computed(() => // const locationOption
  props.locations // props.locations
    // 过滤停用库位。
    .filter((location) => location.is_active !== false) // .filter((location) =
    // 库位编码作为标签。
    .map((location) => ({ // .map((location) => (
      // 库位主键。
      value: location.location_id, // value: location.loca
      // 展示文案。
      label: location.location_code // label: location.loca
    })) // 结束调用
) // 结束括号

// 用时间戳生成默认单号。
const defaultOrderNo = (prefix: string) => `${prefix}-${Date.now().toString(36).toUpperCase()}` // const defaultOrderNo

// 把助手草稿填入对应表单。
const applyDraft = () => { // const applyDraft = (
  // 只取草稿第一行。
  const item = props.draft?.items?.[0] // const item = props.d
  // 无明细则跳过。
  if (!item) return // if (!item) return
  // 按 SKU 匹配商品。
  const product = props.products.find((row) => row.sku_code === item.sku_code) // const product = prop
  // 按库位编码匹配库位。
  const location = props.locations.find((row) => row.location_code === item.location_code) // const location = pro
  // 入库草稿。
  if (props.draft?.type === 'inbound') { // if (props.draft?.typ
    // 回填商品。
    inboundForm.product_id = product?.product_id // inboundForm.product_
    // 回填库位。
    inboundForm.location_id = location?.location_id // inboundForm.location
    // 数量至少为 1。
    inboundForm.quantity = item.quantity && item.quantity > 0 ? item.quantity : 1 // inboundForm.quantity
    // 标注来源，提醒人工确认。
    inboundForm.note = '来自智能助手草稿，请人工确认后保存。' // inboundForm.note = '
  } // 结束代码块
  // 出库草稿。
  if (props.draft?.type === 'outbound') { // if (props.draft?.typ
    // 回填商品。
    outboundForm.product_id = product?.product_id // outboundForm.product
    // 数量至少为 1。
    outboundForm.quantity = item.quantity && item.quantity > 0 ? item.quantity : 1 // outboundForm.quantit
    // 标注来源。
    outboundForm.note = '来自智能助手草稿，请人工确认后保存。' // outboundForm.note = 
  } // 结束代码块
} // 结束代码块

// 每次打开弹窗重置表单并尝试套用草稿。
watch( // watch(
  // 侦听显隐。
  () => props.modelValue, // () => props.modelVal
  // 打开时重置。
  (visible) => { // (visible) => {
    // 关闭时不处理。
    if (!visible) return // if (!visible) return
    // 生成入库单号。
    inboundForm.order_no = defaultOrderNo('IN') // inboundForm.order_no
    // 清空入库商品。
    inboundForm.product_id = undefined // inboundForm.product_
    // 清空入库库位。
    inboundForm.location_id = undefined // inboundForm.location
    // 数量重置为 1。
    inboundForm.quantity = 1 // inboundForm.quantity
    // 清空入库备注。
    inboundForm.note = '' // inboundForm.note = '
    // 生成出库单号。
    outboundForm.order_no = defaultOrderNo('OUT') // outboundForm.order_n
    // 清空客户。
    outboundForm.customer_id = undefined // outboundForm.custome
    // 清空出库商品。
    outboundForm.product_id = undefined // outboundForm.product
    // 数量重置为 1。
    outboundForm.quantity = 1 // outboundForm.quantit
    // 清空出库备注。
    outboundForm.note = '' // outboundForm.note = 
    // 套用助手草稿。
    applyDraft() // applyDraft()
  }, // },
  // 首次也执行一次，避免漏填草稿。
  { immediate: true } // { immediate: true }
) // 结束括号

// 关闭弹窗。
const close = () => emit('update:modelValue', false) // const close = () => 

// 校验并提交入出库。
const submit = () => { // const submit = () =>
  // 入库提交。
  if (isInboundForm.value) { // if (isInboundForm.va
    // 单号、商品、库位、数量都必须有效。
    if (!inboundForm.order_no.trim() || !inboundForm.product_id || !inboundForm.location_id || inboundForm.quantity <= 0) { // if (!inboundForm.ord
      // 提示补全。
      ElMessage.warning('请完整填写入库单号、商品、库位和数量') // ElMessage.warning('请
      // 中止。
      return // return
    } // 结束代码块
    // 发出入库载荷。
    emit('submit', { // emit('submit', {
      // 作业类型。
      type: 'inbound', // type: 'inbound',
      // 后端入库结构。
      payload: { // payload: {
        // 修剪后的单号。
        order_no: inboundForm.order_no.trim(), // order_no: inboundFor
        // 空备注写成 null。
        note: inboundForm.note.trim() || null, // note: inboundForm.no
        // 单行明细。
        items: [ // items: [
          { // 开始对象
            // 商品。
            product_id: inboundForm.product_id, // product_id: inboundF
            // 库位。
            location_id: inboundForm.location_id, // location_id: inbound
            // 数量。
            quantity: inboundForm.quantity // quantity: inboundFor
          } // 结束代码块
        ] // ]
      } // 结束代码块
    }) // 结束调用
    // 入库提交流程结束。
    return // return
  } // 结束代码块

  // 出库提交。
  if (isOutboundForm.value) { // if (isOutboundForm.v
    // 单号、商品、数量必须有效。
    if (!outboundForm.order_no.trim() || !outboundForm.product_id || outboundForm.quantity <= 0) { // if (!outboundForm.or
      // 提示补全。
      ElMessage.warning('请完整填写出库单号、商品和数量') // ElMessage.warning('请
      // 中止。
      return // return
    } // 结束代码块
    // 发出出库载荷。
    emit('submit', { // emit('submit', {
      // 作业类型。
      type: 'outbound', // type: 'outbound',
      // 后端出库结构。
      payload: { // payload: {
        // 修剪后的单号。
        order_no: outboundForm.order_no.trim(), // order_no: outboundFo
        // 未填客户写成 null。
        customer_id: outboundForm.customer_id ?? null, // customer_id: outboun
        // 空备注写成 null。
        note: outboundForm.note.trim() || null, // note: outboundForm.n
        // 单行明细。
        items: [ // items: [
          { // 开始对象
            // 商品。
            product_id: outboundForm.product_id, // product_id: outbound
            // 需求数量。
            quantity: outboundForm.quantity // quantity: outboundFo
          } // 结束代码块
        ] // ]
      } // 结束代码块
    }) // 结束调用
  } // 结束代码块
} // 结束代码块
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 作业弹窗，标题拼接动作与页面名。 -->
  <el-dialog :model-value="modelValue" :title="`${action} · ${pageTitle}`" width="560px" :teleported="false" @update:model-value="emit('update:modelValue', $event)"> <!-- <el-dialog :model-va -->
    <!-- 入库表单。 -->
    <template v-if="isInboundForm"> <!-- 页面模板 -->
      <!-- 入库流程说明。 -->
      <el-alert title="提交后将生成草稿入库单，确认收货后写入库存。" type="info" show-icon :closable="false" class="dialog-notice" /> <!-- <el-alert title="提交后 -->
      <!-- 入库字段。 -->
      <el-form label-position="top" class="operation-form"> <!-- <el-form label-posit -->
        <!-- 入库单号。 -->
        <el-form-item label="入库单号" required><el-input v-model="inboundForm.order_no" placeholder="请输入入库单号" /></el-form-item> <!-- <el-form-item label= -->
        <!-- 商品与库位并排。 -->
        <el-row :gutter="14"> <!-- <el-row :gutter="14" -->
          <!-- 选择系统 SKU。 -->
          <el-col :span="12"><el-form-item label="系统 SKU" required><el-select v-model="inboundForm.product_id" filterable placeholder="请选择商品" style="width:100%"><el-option v-for="option in productOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></el-col> <!-- <el-col :span="12">< -->
          <!-- 选择收货库位。 -->
          <el-col :span="12"><el-form-item label="收货库位" required><el-select v-model="inboundForm.location_id" filterable placeholder="请选择库位" style="width:100%"><el-option v-for="option in locationOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></el-col> <!-- <el-col :span="12">< -->
        </el-row> <!-- 结束 el-row -->
        <!-- 收货数量。 -->
        <el-form-item label="收货数量" required><el-input-number v-model="inboundForm.quantity" :min="1" :precision="0" style="width:100%" /></el-form-item> <!-- <el-form-item label= -->
        <!-- 备注。 -->
        <el-form-item label="备注"><el-input v-model="inboundForm.note" type="textarea" :rows="3" placeholder="选填" /></el-form-item> <!-- <el-form-item label= -->
      </el-form> <!-- 结束 el-form -->
    </template> <!-- 结束 template -->

    <!-- 出库表单。 -->
    <template v-else-if="isOutboundForm"> <!-- 页面模板 -->
      <!-- 出库流程说明。 -->
      <el-alert title="提交后将生成草稿出库单，分配库存会按库位锁定库存。" type="info" show-icon :closable="false" class="dialog-notice" /> <!-- <el-alert title="提交后 -->
      <!-- 出库字段。 -->
      <el-form label-position="top" class="operation-form"> <!-- <el-form label-posit -->
        <!-- 出库单号。 -->
        <el-form-item label="出库单号" required><el-input v-model="outboundForm.order_no" placeholder="请输入出库单号" /></el-form-item> <!-- <el-form-item label= -->
        <!-- 客户与商品并排。 -->
        <el-row :gutter="14"> <!-- <el-row :gutter="14" -->
          <!-- 客户编号选填。 -->
          <el-col :span="12"><el-form-item label="客户编号"><el-input-number v-model="outboundForm.customer_id" :min="1" :precision="0" placeholder="选填" style="width:100%" /></el-form-item></el-col> <!-- <el-col :span="12">< -->
          <!-- 选择系统 SKU。 -->
          <el-col :span="12"><el-form-item label="系统 SKU" required><el-select v-model="outboundForm.product_id" filterable placeholder="请选择商品" style="width:100%"><el-option v-for="option in productOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></el-col> <!-- <el-col :span="12">< -->
        </el-row> <!-- 结束 el-row -->
        <!-- 需求数量。 -->
        <el-form-item label="需求数量" required><el-input-number v-model="outboundForm.quantity" :min="1" :precision="0" style="width:100%" /></el-form-item> <!-- <el-form-item label= -->
        <!-- 备注。 -->
        <el-form-item label="备注"><el-input v-model="outboundForm.note" type="textarea" :rows="3" placeholder="选填" /></el-form-item> <!-- <el-form-item label= -->
      </el-form> <!-- 结束 el-form -->
    </template> <!-- 结束 template -->

    <!-- 非入出库动作只给只读提示。 -->
    <template v-else><div class="read-only-tip">{{ isWriteAction ? '请在业务列表中选择具体记录执行该操作。' : '此功能需要真实业务记录，接口接入后可查看完整详情或导出数据。' }}</div></template> <!-- 页面模板 -->

    <!-- 底部关闭与提交。 -->
    <template #footer><el-button @click="close">关闭</el-button><el-button v-if="isWriteAction" type="primary" @click="submit">提交{{ action }}</el-button></template> <!-- 页面模板 -->
  </el-dialog> <!-- 结束 el-dialog -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 说明条间距、表单宽度与只读提示样式。 */
.dialog-notice { margin-bottom: 18px; }.operation-form { width: 100%; }.read-only-tip { color: var(--muted); padding: 24px 0; line-height: 1.8; } /* .dialog-notice { mar */
</style> <!-- 结束 style -->
