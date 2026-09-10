import { ElMessage } from 'element-plus'

export function useBackendUnavailable() {
  const notify = (action: string) => {
    ElMessage({
      type: 'info',
      message: `${action}：后端接口尚未接入，当前仅展示界面原型。`,
      duration: 3200,
      showClose: true
    })
  }
  return { notify }
}
