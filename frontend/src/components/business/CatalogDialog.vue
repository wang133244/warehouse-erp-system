<!-- 新建商品/仓库/库位弹窗。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入计算属性、响应式对象与侦听器。
import { computed, reactive, watch } from 'vue' // import { computed, r
// 引入商品、库位、仓库类型。
import type { Location, Product, Warehouse } from '../../models/catalog' // import type { Locati

// 弹窗显隐、种类、仓库选项、编辑对象与提交中。
const props = defineProps<{ // const props = define
  // 是否显示弹窗。
  modelValue: boolean // modelValue: boolean
  // 当前维护的主数据种类。
  kind: 'product' | 'location' | 'warehouse' // kind: 'product' | 'l
  // 库位表单用的仓库列表。
  warehouses: Warehouse[] // warehouses: Warehous
  // 保存请求进行中。
  submitting?: boolean // submitting?: boolean
  // 编辑商品时的初值。
  product?: Product | null // product?: Product | 
  // 编辑库位时的初值。
  location?: Location | null // location?: Location 
}>() // 结束类型实参调用
// 同步显隐，以及提交主数据载荷。
const emit = defineEmits<{ // const emit = defineE
  // 回写弹窗开关。
  'update:modelValue': [value: boolean] // 'update:modelValue':
  // 把表单字段交给父组件保存。
  submit: [payload: Record<string, string | number | boolean>] // submit: [payload: Re
}>() // 结束类型实参调用

// 是否处于编辑模式（仓库只支持新建）。
const isEdit = computed(() => { // const isEdit = compu
  // 商品有传入对象即为编辑。
  if (props.kind === 'product') return Boolean(props.product) // if (props.kind === '
  // 库位有传入对象即为编辑。
  if (props.kind === 'location') return Boolean(props.location) // if (props.kind === '
  // 仓库一律视为新建。
  return false // return false
}) // 结束调用
// 按种类与编辑态生成弹窗标题。
const title = computed(() => { // const title = comput
  // 商品标题。
  if (props.kind === 'product') return isEdit.value ? '编辑商品' : '新建商品' // if (props.kind === '
  // 仓库标题。
  if (props.kind === 'warehouse') return '新建仓库' // if (props.kind === '
  // 库位标题。
  return isEdit.value ? '编辑库位' : '新建库位' // return isEdit.value 
}) // 结束调用

// 商品表单默认值。
const product = reactive({ // const product = reac
  // 系统 SKU。
  sku_code: '', // sku_code: '',
  // 来源商品编码。
  source_product_code: '', // source_product_code:
  // 品牌。
  brand: '', // brand: '',
  // 商品名称。
  product_name: '', // product_name: '',
  // 品类。
  category: '通用', // category: '通用',
  // 规格尺寸。
  size: '标准', // size: '标准',
  // 功能特征。
  function_feature: '普通', // function_feature: '普
  // 颜色。
  color: '默认', // color: '默认',
  // 托盘规格。
  pallet_spec: '箱', // pallet_spec: '箱',
  // 托盘容量。
  pallet_capacity: 10, // pallet_capacity: 10,
  // 是否启用。
  is_active: true // is_active: true
}) // 结束调用
// 库位表单默认值。
const location = reactive({ // const location = rea
  // 所属仓库。
  warehouse_id: undefined as number | undefined, // warehouse_id: undefi
  // 库位编码。
  location_code: '', // location_code: '',
  // 库区。
  zone_code: 'A', // zone_code: 'A',
  // 巷道。
  aisle_code: '01', // aisle_code: '01',
  // 货架。
  rack_code: '01', // rack_code: '01',
  // 货位。
  position_code: '01', // position_code: '01',
  // 是否启用。
  is_active: true // is_active: true
}) // 结束调用
// 仓库表单默认值。
const warehouse = reactive({ // const warehouse = re
  // 仓库编码。
  warehouse_code: '', // warehouse_code: '',
  // 仓库名称。
  warehouse_name: '' // warehouse_name: ''
}) // 结束调用

// 打开弹窗或切换种类时回填表单。
watch( // watch(
  // 侦听显隐、编辑对象与种类。
  () => [props.modelValue, props.product, props.location, props.kind] as const, // () => [props.modelVa
  // 仅在打开时填充。
  ([visible]) => { // ([visible]) => {
    // 关闭时不处理。
    if (!visible) return // if (!visible) return
    // 回填商品字段。
    if (props.kind === 'product') { // if (props.kind === '
      // SKU。
      product.sku_code = props.product?.sku_code ?? '' // product.sku_code = p
      // 来源编码。
      product.source_product_code = props.product?.source_product_code ?? '' // product.source_produ
      // 品牌。
      product.brand = props.product?.brand ?? '' // product.brand = prop
      // 名称。
      product.product_name = props.product?.product_name ?? '' // product.product_name
      // 品类缺省「通用」。
      product.category = props.product?.category ?? '通用' // product.category = p
      // 尺寸缺省「标准」。
      product.size = props.product?.size ?? '标准' // product.size = props
      // 功能缺省「普通」。
      product.function_feature = props.product?.function_feature ?? '普通' // product.function_fea
      // 颜色缺省「默认」。
      product.color = props.product?.color ?? '默认' // product.color = prop
      // 托盘规格缺省「箱」。
      product.pallet_spec = props.product?.pallet_spec ?? '箱' // product.pallet_spec 
      // 托盘容量缺省 10。
      product.pallet_capacity = props.product?.pallet_capacity ?? 10 // product.pallet_capac
      // 未显式停用则视为启用。
      product.is_active = props.product?.is_active !== false // product.is_active = 
      // 商品回填结束。
      return // return
    } // 结束代码块
    // 仓库只支持新建，打开时清空。
    if (props.kind === 'warehouse') { // if (props.kind === '
      // 清空编码。
      warehouse.warehouse_code = '' // warehouse.warehouse_
      // 清空名称。
      warehouse.warehouse_name = '' // warehouse.warehouse_
      // 仓库回填结束。
      return // return
    } // 结束代码块
    // 库位：优先用编辑对象，否则默认第一个仓库。
    location.warehouse_id = props.location?.warehouse_id ?? props.warehouses[0]?.warehouse_id // location.warehouse_i
    // 库位编码。
    location.location_code = props.location?.location_code ?? '' // location.location_co
    // 库区。
    location.zone_code = props.location?.zone_code ?? 'A' // location.zone_code =
    // 巷道。
    location.aisle_code = props.location?.aisle_code ?? '01' // location.aisle_code 
    // 货架。
    location.rack_code = props.location?.rack_code ?? '01' // location.rack_code =
    // 货位。
    location.position_code = props.location?.position_code ?? '01' // location.position_co
    // 未显式停用则视为启用。
    location.is_active = props.location?.is_active !== false // location.is_active =
  } // 结束代码块
) // 结束括号

// 按种类组装载荷并提交。
const submit = () => { // const submit = () =>
  // 提交商品。
  if (props.kind === 'product') { // if (props.kind === '
    // 可编辑字段（SKU 仅新建时带上）。
    const payload: Record<string, string | number | boolean> = { // const payload: Recor
      // 来源商品编码。
      source_product_code: product.source_product_code, // source_product_code:
      // 品牌。
      brand: product.brand, // brand: product.brand
      // 名称。
      product_name: product.product_name, // product_name: produc
      // 品类。
      category: product.category, // category: product.ca
      // 尺寸。
      size: product.size, // size: product.size,
      // 功能特征。
      function_feature: product.function_feature, // function_feature: pr
      // 颜色。
      color: product.color, // color: product.color
      // 托盘规格。
      pallet_spec: product.pallet_spec, // pallet_spec: product
      // 托盘容量。
      pallet_capacity: product.pallet_capacity, // pallet_capacity: pro
      // 启用状态。
      is_active: product.is_active // is_active: product.i
    } // 结束代码块
    // 新建时才允许提交 SKU。
    if (!isEdit.value) { // if (!isEdit.value) {
      // 写入系统 SKU。
      payload.sku_code = product.sku_code // payload.sku_code = p
    } // 结束代码块
    // 交给父组件。
    emit('submit', payload) // emit('submit', paylo
    // 商品提交流程结束。
    return // return
  } // 结束代码块
  // 提交仓库。
  if (props.kind === 'warehouse') { // if (props.kind === '
    // 编码与名称。
    emit('submit', { // emit('submit', {
      // 仓库编码。
      warehouse_code: warehouse.warehouse_code, // warehouse_code: ware
      // 仓库名称。
      warehouse_name: warehouse.warehouse_name // warehouse_name: ware
    }) // 结束调用
    // 仓库提交流程结束。
    return // return
  } // 结束代码块
  // 提交库位：库区结构字段始终可改。
  const payload: Record<string, string | number | boolean> = { // const payload: Recor
    // 库区。
    zone_code: location.zone_code, // zone_code: location.
    // 巷道。
    aisle_code: location.aisle_code, // aisle_code: location
    // 货架。
    rack_code: location.rack_code, // rack_code: location.
    // 货位。
    position_code: location.position_code, // position_code: locat
    // 启用状态。
    is_active: location.is_active // is_active: location.
  } // 结束代码块
  // 新建时才允许改仓库与库位编码。
  if (!isEdit.value) { // if (!isEdit.value) {
    // 所属仓库。
    payload.warehouse_id = Number(location.warehouse_id) // payload.warehouse_id
    // 库位编码。
    payload.location_code = location.location_code // payload.location_cod
  } // 结束代码块
  // 交给父组件。
  emit('submit', payload) // emit('submit', paylo
} // 结束代码块
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 主数据弹窗，标题随种类变化。 -->
  <el-dialog :model-value="modelValue" :title="title" width="520px" @close="emit('update:modelValue', false)"> <!-- <el-dialog :model-va -->
    <!-- 商品表单。 -->
    <el-form v-if="kind === 'product'" label-width="110px"> <!-- <el-form v-if="kind  -->
      <!-- 系统 SKU，编辑时只读。 -->
      <el-form-item label="系统 SKU"><el-input v-model="product.sku_code" :disabled="isEdit" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 来源商品编码。 -->
      <el-form-item label="商品编码"><el-input v-model="product.source_product_code" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 商品名称。 -->
      <el-form-item label="商品名称"><el-input v-model="product.product_name" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 品牌。 -->
      <el-form-item label="品牌"><el-input v-model="product.brand" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 托盘容量，最小 1。 -->
      <el-form-item label="托盘容量"><el-input-number v-model="product.pallet_capacity" :min="1" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 启用开关。 -->
      <el-form-item label="启用状态"><el-switch v-model="product.is_active" /></el-form-item> <!-- <el-form-item label= -->
    </el-form> <!-- 结束 el-form -->
    <!-- 仓库表单。 -->
    <el-form v-else-if="kind === 'warehouse'" label-width="110px"> <!-- <el-form v-else-if=" -->
      <!-- 仓库编码。 -->
      <el-form-item label="仓库编码"><el-input v-model="warehouse.warehouse_code" placeholder="如 WH-03" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 仓库显示名。 -->
      <el-form-item label="仓库名称"><el-input v-model="warehouse.warehouse_name" placeholder="仓库显示名" /></el-form-item> <!-- <el-form-item label= -->
    </el-form> <!-- 结束 el-form -->
    <!-- 库位表单。 -->
    <el-form v-else label-width="110px"> <!-- <el-form v-else labe -->
      <!-- 所属仓库，编辑时不可改。 -->
      <el-form-item label="仓库"> <!-- <el-form-item label= -->
        <!-- 仓库下拉。 -->
        <el-select v-model="location.warehouse_id" style="width: 100%" :disabled="isEdit"> <!-- <el-select v-model=" -->
          <!-- 每个仓库一个选项。 -->
          <el-option v-for="item in warehouses" :key="item.warehouse_id" :label="item.warehouse_name" :value="item.warehouse_id" /> <!-- <el-option v-for="it -->
        </el-select> <!-- 结束 el-select -->
      </el-form-item> <!-- 结束 el-form-item -->
      <!-- 库位编码，编辑时只读。 -->
      <el-form-item label="库位编码"><el-input v-model="location.location_code" :disabled="isEdit" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 库区。 -->
      <el-form-item label="库区"><el-input v-model="location.zone_code" /></el-form-item> <!-- <el-form-item label= -->
      <!-- 启用开关。 -->
      <el-form-item label="启用状态"><el-switch v-model="location.is_active" /></el-form-item> <!-- <el-form-item label= -->
    </el-form> <!-- 结束 el-form -->
    <!-- 底部操作槽。 -->
    <template #footer> <!-- 页面模板 -->
      <!-- 关闭弹窗。 -->
      <el-button @click="emit('update:modelValue', false)">取消</el-button> <!-- <el-button @click="e -->
      <!-- 保存主数据。 -->
      <el-button type="primary" :loading="submitting" data-testid="catalog-save" @click="submit">保存</el-button> <!-- <el-button type="pri -->
    </template> <!-- 结束 template -->
  </el-dialog> <!-- 结束 el-dialog -->
</template> <!-- 结束 template -->
