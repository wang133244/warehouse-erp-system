/** 登录表单、记住用户名、跳转。 */
import { onMounted, reactive, ref } from 'vue' // 引入 Vue 响应式与生命周期
import { useRoute, useRouter } from 'vue-router' // 引入路由用于登录后跳转
import { ElMessage } from 'element-plus' // 引入提示消息
import { useAppStore } from '../stores/app' // 引入登录态仓库
import { ApiError } from '../models/client' // 引入 API 错误类型

export const REMEMBERED_USERNAME_KEY = 'erp.remembered-username' // 本地记住用户名的存储键

export function useLoginController() { // 登录页控制器
  const form = reactive({ username: '', password: '' }) // 登录表单
  const rememberUsername = ref(false) // 是否记住用户名
  const loading = ref(false) // 提交中标志
  const router = useRouter() // 路由器
  const route = useRoute() // 当前路由（读取 redirect）
  const app = useAppStore() // 应用登录态

  onMounted(() => { // 挂载时回填记住的用户名
    const saved = window.localStorage.getItem(REMEMBERED_USERNAME_KEY) // 读取本地缓存
    if (saved) { // 有缓存用户名
      form.username = saved // 填入表单
      rememberUsername.value = true // 勾选记住
    } // 结束缓存分支
  }) // 结束 onMounted

  const submit = async () => { // 提交登录
    if (!form.username.trim() || !form.password) { // 账号或密码为空
      ElMessage.warning('请输入账号和密码') // 提示补全
      return // 中止提交
    } // 结束空表单判断
    loading.value = true // 开始提交
    try { // 调用登录
      await app.login(form.username.trim(), form.password) // 走仓库登录并拉用户
      if (rememberUsername.value) { // 需要记住用户名
        window.localStorage.setItem(REMEMBERED_USERNAME_KEY, form.username.trim()) // 写入本地
      } else { // 不记住
        window.localStorage.removeItem(REMEMBERED_USERNAME_KEY) // 清除缓存
      } // 结束记住分支
      ElMessage.success('登录成功') // 成功提示
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard' // 回跳原路径或看板
      await router.push(redirect) // 跳转目标页
    } catch (error) { // 登录失败
      ElMessage.error(error instanceof ApiError ? error.message : '登录失败，请稍后重试') // 展示错误
    } finally { // 无论成败
      loading.value = false // 结束提交状态
    } // 结束 finally
  } // 结束 submit

  return { // 暴露给视图
    form, // 表单
    rememberUsername, // 记住选项
    loading, // 加载状态
    router, // 路由器
    route, // 当前路由
    app, // 应用仓库
    submit, // 提交方法
  } // 结束 return
} // 结束 useLoginController
