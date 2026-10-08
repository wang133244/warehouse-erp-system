<!-- 审批同意/驳回弹窗。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入响应式引用与侦听器。
import { ref, watch } from 'vue' // import { ref, watch 
// 引入消息提示，驳回未填意见时告警。
import { ElMessage } from 'element-plus' // import { ElMessage }
// 引入审批任务类型。
import type { ApprovalTask } from '../../models/warehouse-extensions' // import type { Approv

// 弹窗显隐、当前任务、提交中状态。
const props = defineProps<{ // const props = define
  // 是否显示弹窗。
  modelValue: boolean // modelValue: boolean
  // 正在审批的任务，可为空。
  task: ApprovalTask | null // task: ApprovalTask |
  // 提交请求进行中。
  submitting?: boolean // submitting?: boolean
}>() // 结束类型实参调用
// 同步显隐，以及提交同意/驳回。
const emit = defineEmits<{ // const emit = defineE
  // 回写弹窗开关。
  'update:modelValue': [value: boolean] // 'update:modelValue':
  // 把审批动作与意见交给父组件。
  submit: [payload: { action: 'approve' | 'reject'; comment: string }] // submit: [payload: { 
}>() // 结束类型实参调用

// 审批意见文本。
const comment = ref('') // const comment = ref(
// 弹窗每次打开时清空上次意见。
watch( // watch(
  // 侦听显隐变化。
  () => props.modelValue, // () => props.modelVal
  // 打开时重置意见。
  (visible) => { // (visible) => {
    // 仅在打开时清空。
    if (visible) comment.value = '' // if (visible) comment
  } // 结束代码块
) // 结束括号

// 同意：意见可空。
const approve = () => { // const approve = () =
  // 发出同意事件并带上修剪后的意见。
  emit('submit', { action: 'approve', comment: comment.value.trim() }) // emit('submit', { act
} // 结束代码块
// 驳回：意见必填。
const reject = () => { // const reject = () =>
  // 未填意见则提示并中止。
  if (!comment.value.trim()) { // if (!comment.value.t
    // 警告必须填写驳回原因。
    ElMessage.warning('驳回时必须填写审批意见') // ElMessage.warning('驳
    // 不继续提交。
    return // return
  } // 结束代码块
  // 发出驳回事件。
  emit('submit', { action: 'reject', comment: comment.value.trim() }) // emit('submit', { act
} // 结束代码块
</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 审批弹窗，标题固定为审批申请。 -->
  <el-dialog :model-value="modelValue" title="审批申请" width="520px" @update:model-value="emit('update:modelValue', $event)"> <!-- <el-dialog :model-va -->
    <!-- 展示业务单号与业务类型。 -->
    <p v-if="task">{{ task.business_summary?.order_no ?? task.business_id }} · {{ task.business_type }}</p> <!-- <p v-if="task">{{ ta -->
    <!-- 审批意见多行输入，驳回必填。 -->
    <el-input v-model="comment" type="textarea" :rows="4" placeholder="审批意见；驳回时必填" /> <!-- <el-input v-model="c -->
    <!-- 底部操作槽。 -->
    <template #footer> <!-- 页面模板 -->
      <!-- 关闭弹窗。 -->
      <el-button @click="emit('update:modelValue', false)">取消</el-button> <!-- <el-button @click="e -->
      <!-- 驳回当前申请。 -->
      <el-button :loading="submitting" @click="reject">驳回</el-button> <!-- <el-button :loading= -->
      <!-- 同意当前申请。 -->
      <el-button type="primary" :loading="submitting" @click="approve">同意</el-button> <!-- <el-button type="pri -->
    </template> <!-- 结束 template -->
  </el-dialog> <!-- 结束 el-dialog -->
</template> <!-- 结束 template -->
