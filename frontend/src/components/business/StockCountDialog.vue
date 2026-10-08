<!-- 盘点新建与实盘弹窗。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入响应式对象与侦听器。
import { reactive, watch } from 'vue' // import { reactive, w
// 校验失败时弹出警告。
import { ElMessage } from 'element-plus' // import { ElMessage }
// 商品与库位类型。
import type { Location, Product } from '../../models/catalog' // import type { Locati
// 盘点单与保存载荷类型。
import type { StockCountOrder, StockCountUpsert } from '../../models/warehouse-extensions' // import type { StockC

// 弹窗显隐、主数据、编辑初值、提交中。
const props = defineProps<{ // const props = define
  // 是否显示弹窗。
  modelValue: boolean // modelValue: boolean
  // 可选商品列表。
  products: Product[] // products: Product[]
  // 可选库位列表。
  locations: Location[] // locations: Location[
  // 编辑已有盘点单时的初值。
  initialValue?: StockCountOrder | null // initialValue?: Stock
  // 保存请求进行中。
  submitting?: boolean // submitting?: boolean
}>() // 结束类型实参调用
// 同步显隐，以及提交盘点明细。
const emit = defineEmits<{ // const emit = defineE
  // 回写弹窗开关。
  'update:modelValue': [value: boolean] // 'update:modelValue':
  // 把盘点保存载荷交给父组件。
  submit: [payload: StockCountUpsert] // submit: [payload: St
}>() // 结束类型实参调用

// 备注与明细行表单。
const form = reactive({ // const form = reactiv
  // 盘点备注。
  note: '', // note: '',
  // 默认一行空明细。
  items: [{ product_id: undefined as number | undefined, location_id: undefined as number | undefined, counted_quantity: 0 }] // items: [{ product_id
}) // 结束调用

// 打开弹窗时用初值或空行填充表单。
watch( // watch(
  // 侦听显隐。
  () => props.modelValue, // () => props.modelVal
  // 可见时回填。
  (visible) => { // (visible) => {
    // 关闭时不处理。
    if (!visible) return // if (!visible) return
    // 回填备注。
    form.note = props.initialValue?.note ?? '' // form.note = props.in
    // 有明细则映射，否则给一行空记录。
    form.items = (props.initialValue?.items?.length // form.items = (props.
      // 把已有明细映射成表单行。
      ? props.initialValue.items.map((item) => ({ // ? props.initialValue
          // 商品主键。
          product_id: item.product_id, // product_id: item.pro
          // 库位主键。
          location_id: item.location_id, // location_id: item.lo
          // 实盘数量。
          counted_quantity: item.counted_quantity // counted_quantity: it
        })) // 结束调用
      // 无明细时放一行空输入。
      : [{ product_id: undefined, location_id: undefined, counted_quantity: 0 }]) as typeof form.items // : [{ product_id: und
  } // 结束代码块
) // 结束括号

// 追加一行空明细。
const addRow = () => { // const addRow = () =>
  // 推入默认空行。
  form.items.push({ product_id: undefined, location_id: undefined, counted_quantity: 0 }) // form.items.push({ pr
} // 结束代码块
// 按索引删除一行。
const removeRow = (index: number) => { // const removeRow = (i
  // 从明细数组移除。
  form.items.splice(index, 1) // form.items.splice(in
} // 结束代码块
// 校验并提交盘点明细。
const submit = () => { // const submit = () =>
  // 只保留已选商品和库位的行。
  const items = form.items.filter((item) => item.product_id && item.location_id) // const items = form.i
  // 至少要有一行有效明细。
  if (!items.length) { // if (!items.length) {
    // 提示用户补录。
    ElMessage.warning('请至少录入一行盘点明细') // ElMessage.warning('请
    // 中止提交。
    return // return
  } // 结束代码块
  // 用「商品-库位」拼成去重键。
  const keys = items.map((item) => `${item.product_id}-${item.location_id}`) // const keys = items.m
  // 存在重复组合则拒绝。
  if (new Set(keys).size !== keys.length) { // if (new Set(keys).si
    // 提示重复。
    ElMessage.warning('盘点明细中存在重复的商品/库位组合') // ElMessage.warning('盘
    // 中止提交。
    return // return
  } // 结束代码块
  // 把表单转成后端载荷。
  emit('submit', { // emit('submit', {
    // 空备注写成 null。
    note: form.note || null, // note: form.note || n
    // 主键与数量转成数字。
    items: items.map((item) => ({ // items: items.map((it
      // 商品 ID。
      product_id: Number(item.product_id), // product_id: Number(i
      // 库位 ID。
      location_id: Number(item.location_id), // location_id: Number(
      // 实盘数量。
      counted_quantity: Number(item.counted_quantity) // counted_quantity: Nu
    })) // 结束调用
  }) // 结束调用
} // 结束代码块
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 盘点单弹窗。 -->
  <el-dialog :model-value="modelValue" title="盘点单" width="720px" @update:model-value="emit('update:modelValue', $event)"> <!-- <el-dialog :model-va -->
    <!-- 盘点表单。 -->
    <el-form label-width="80px"> <!-- <el-form label-width -->
      <!-- 备注输入。 -->
      <el-form-item label="备注"><el-input v-model="form.note" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 每一行明细：商品、库位、数量、删除。 -->
      <div v-for="(item, index) in form.items" :key="index" class="line"> <!-- <div v-for="(item, i -->
        <!-- 选择盘点商品，可搜索。 -->
        <el-select v-model="item.product_id" placeholder="商品" filterable> <!-- <el-select v-model=" -->
          <!-- 商品下拉项用 SKU 展示。 -->
          <el-option v-for="product in products" :key="product.product_id" :label="product.sku_code" :value="product.product_id" /> <!-- <el-option v-for="pr -->
        </el-select> <!-- 结束 el-select -->
        <!-- 选择盘点库位，可搜索。 -->
        <el-select v-model="item.location_id" placeholder="库位" filterable> <!-- <el-select v-model=" -->
          <!-- 库位下拉项用库位编码展示。 -->
          <el-option v-for="location in locations" :key="location.location_id" :label="location.location_code" :value="location.location_id" /> <!-- <el-option v-for="lo -->
        </el-select> <!-- 结束 el-select -->
        <!-- 实盘数量，最小为 0。 -->
        <el-input-number v-model="item.counted_quantity" :min="0" /> <!-- <el-input-number v-m -->
        <!-- 删除当前明细行。 -->
        <el-button text @click="removeRow(index)">删除</el-button> <!-- <el-button text @cli -->
      </div> <!-- 结束 div -->
      <!-- 追加明细行。 -->
      <el-button @click="addRow">增加明细</el-button> <!-- <el-button @click="a -->
    </el-form> <!-- 结束 el-form -->
    <!-- 底部操作槽。 -->
    <template #footer> <!-- 页面模板 -->
      <!-- 关闭弹窗。 -->
      <el-button @click="emit('update:modelValue', false)">取消</el-button> <!-- <el-button @click="e -->
      <!-- 保存盘点单。 -->
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button> <!-- <el-button type="pri -->
    </template> <!-- 结束 template -->
  </el-dialog> <!-- 结束 el-dialog -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 明细行四列网格：商品、库位、数量、删除。 */
.line { display: grid; grid-template-columns: 1fr 1fr 140px auto; gap: 8px; margin-bottom: 8px; align-items: center; } /* .line { display: gri */
</style> <!-- 结束 style -->
