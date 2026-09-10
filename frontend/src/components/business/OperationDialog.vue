<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Location, Product } from '../../api/catalog'
import type { OperationSubmission } from '../../api/operations'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    action: string
    pageTitle: string
    products?: Product[]
    locations?: Location[]
  }>(),
  {
    products: () => [],
    locations: () => []
  }
)
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [submission: OperationSubmission]
}>()

const isInboundForm = computed(() => props.action.includes('入库'))
const isOutboundForm = computed(() => props.action.includes('出库'))
const isWriteAction = computed(() => isInboundForm.value || isOutboundForm.value)

const inboundForm = reactive({
  order_no: '',
  product_id: undefined as number | undefined,
  location_id: undefined as number | undefined,
  quantity: 1,
  note: ''
})

const outboundForm = reactive({
  order_no: '',
  customer_id: undefined as number | undefined,
  product_id: undefined as number | undefined,
  quantity: 1,
  note: ''
})

const productOptions = computed(() =>
  props.products.map((product) => ({
    value: product.product_id,
    label: `${product.sku_code} · ${product.product_name}`
  }))
)
const locationOptions = computed(() =>
  props.locations.map((location) => ({
    value: location.location_id,
    label: location.location_code
  }))
)

const defaultOrderNo = (prefix: string) => `${prefix}-${Date.now().toString(36).toUpperCase()}`

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    inboundForm.order_no = defaultOrderNo('IN')
    inboundForm.product_id = undefined
    inboundForm.location_id = undefined
    inboundForm.quantity = 1
    inboundForm.note = ''
    outboundForm.order_no = defaultOrderNo('OUT')
    outboundForm.customer_id = undefined
    outboundForm.product_id = undefined
    outboundForm.quantity = 1
    outboundForm.note = ''
  }
)

const close = () => emit('update:modelValue', false)

const submit = () => {
  if (isInboundForm.value) {
    if (!inboundForm.order_no.trim() || !inboundForm.product_id || !inboundForm.location_id || inboundForm.quantity <= 0) {
      ElMessage.warning('请完整填写入库单号、商品、库位和数量')
      return
    }
    emit('submit', {
      type: 'inbound',
      payload: {
        order_no: inboundForm.order_no.trim(),
        note: inboundForm.note.trim() || null,
        items: [
          {
            product_id: inboundForm.product_id,
            location_id: inboundForm.location_id,
            quantity: inboundForm.quantity
          }
        ]
      }
    })
    return
  }

  if (isOutboundForm.value) {
    if (!outboundForm.order_no.trim() || !outboundForm.product_id || outboundForm.quantity <= 0) {
      ElMessage.warning('请完整填写出库单号、商品和数量')
      return
    }
    emit('submit', {
      type: 'outbound',
      payload: {
        order_no: outboundForm.order_no.trim(),
        customer_id: outboundForm.customer_id ?? null,
        note: outboundForm.note.trim() || null,
        items: [
          {
            product_id: outboundForm.product_id,
            quantity: outboundForm.quantity
          }
        ]
      }
    })
  }
}
</script>

<template>
  <el-dialog :model-value="modelValue" :title="`${action} · ${pageTitle}`" width="560px" :teleported="false" @update:model-value="emit('update:modelValue', $event)">
    <template v-if="isInboundForm">
      <el-alert title="提交后将生成草稿入库单，确认收货后写入库存。" type="info" show-icon :closable="false" class="dialog-notice" />
      <el-form label-position="top" class="operation-form">
        <el-form-item label="入库单号" required><el-input v-model="inboundForm.order_no" placeholder="请输入入库单号" /></el-form-item>
        <el-row :gutter="14">
          <el-col :span="12"><el-form-item label="系统 SKU" required><el-select v-model="inboundForm.product_id" filterable placeholder="请选择商品" style="width:100%"><el-option v-for="option in productOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="收货库位" required><el-select v-model="inboundForm.location_id" filterable placeholder="请选择库位" style="width:100%"><el-option v-for="option in locationOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="收货数量" required><el-input-number v-model="inboundForm.quantity" :min="1" :precision="0" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="inboundForm.note" type="textarea" :rows="3" placeholder="选填" /></el-form-item>
      </el-form>
    </template>

    <template v-else-if="isOutboundForm">
      <el-alert title="提交后将生成草稿出库单，分配库存会按库位锁定库存。" type="info" show-icon :closable="false" class="dialog-notice" />
      <el-form label-position="top" class="operation-form">
        <el-form-item label="出库单号" required><el-input v-model="outboundForm.order_no" placeholder="请输入出库单号" /></el-form-item>
        <el-row :gutter="14">
          <el-col :span="12"><el-form-item label="客户编号"><el-input-number v-model="outboundForm.customer_id" :min="1" :precision="0" placeholder="选填" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="系统 SKU" required><el-select v-model="outboundForm.product_id" filterable placeholder="请选择商品" style="width:100%"><el-option v-for="option in productOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="需求数量" required><el-input-number v-model="outboundForm.quantity" :min="1" :precision="0" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="outboundForm.note" type="textarea" :rows="3" placeholder="选填" /></el-form-item>
      </el-form>
    </template>

    <template v-else><div class="read-only-tip">{{ isWriteAction ? '请在业务列表中选择具体记录执行该操作。' : '此功能需要真实业务记录，接口接入后可查看完整详情或导出数据。' }}</div></template>

    <template #footer><el-button @click="close">关闭</el-button><el-button v-if="isWriteAction" type="primary" @click="submit">提交{{ action }}</el-button></template>
  </el-dialog>
</template>

<style scoped>
.dialog-notice { margin-bottom: 18px; }.operation-form { width: 100%; }.read-only-tip { color: var(--muted); padding: 24px 0; line-height: 1.8; }
</style>
