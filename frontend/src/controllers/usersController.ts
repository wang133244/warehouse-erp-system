/** 管理员创建用户。 */
import { computed, onMounted, reactive, ref } from 'vue' // 引入 Vue 计算属性、生命周期与响应式
import { ElMessage, ElMessageBox } from 'element-plus' // 引入提示与确认框
import { pageConfigs } from '../config/pages' // 引入页面配置
import { listWarehouses, type Warehouse } from '../models/catalog' // 仓库列表
import { ApiError } from '../models/client' // API 错误类型
import { createUser, deleteUser, listRoles, listUsers, updateUser, type SystemRole, type SystemUser } from '../models/followup' // 用户与角色 API
import { useAppStore } from '../stores/app' // 当前用户角色

const FALLBACK_ROLES: SystemRole[] = [ // 接口失败时的角色兜底
  { role_id: 1, role_code: 'admin', role_name: '系统管理员' }, // 系统管理员
  { role_id: 2, role_code: 'warehouse_manager', role_name: '仓库管理员' }, // 仓库管理员
  { role_id: 3, role_code: 'warehouse_operator', role_name: '仓库操作员' }, // 仓库操作员
  { role_id: 4, role_code: 'viewer', role_name: '只读' } // 只读
] // 结束 FALLBACK_ROLES

export function useUsersController() { // 用户管理页控制器
  const config = pageConfigs['/users'] // 本页配置
  const app = useAppStore() // 应用仓库
  const rows = ref<SystemUser[]>([]) // 用户列表
  const warehouses = ref<Warehouse[]>([]) // 仓库选项
  const roleOptions = ref<SystemRole[]>(FALLBACK_ROLES) // 角色选项
  const loading = ref(false) // 加载中
  const errorMessage = ref('') // 列表错误
  const formError = ref('') // 表单错误
  const keyword = ref('') // 搜索关键字
  const dialogVisible = ref(false) // 新建/编辑弹窗
  const submitting = ref(false) // 弹窗提交中
  const editing = ref<SystemUser | null>(null) // 正在编辑的用户
  const isAdmin = computed(() => (app.currentUser?.roles ?? []).includes('admin')) // 是否管理员
  const form = reactive({ // 用户表单
    username: '', // 账户名
    password: '', // 密码
    display_name: '', // 显示名
    roles: ['warehouse_operator'] as string[], // 默认操作员
    warehouse_ids: [] as number[], // 仓库范围
    is_active: true // 是否启用
  }) // 结束 form
  const warehouseName = (warehouseId: number) => // 仓库 ID 转名称
    warehouses.value.find((item) => item.warehouse_id === warehouseId)?.warehouse_name ?? String(warehouseId) // 找不到则显示 ID
  const roleName = (roleCode: string) => // 角色编码转名称
    roleOptions.value.find((item) => item.role_code === roleCode)?.role_name ?? roleCode // 找不到则显示编码

  const loadData = async () => { // 加载用户列表
    if (!isAdmin.value) { // 非管理员不拉用户
      rows.value = [] // 清空列表
      return // 直接返回
    } // 结束非管理员分支
    loading.value = true // 开始加载
    errorMessage.value = '' // 清空错误
    try { // 请求列表
      const page = await listUsers({ keyword: keyword.value.trim() || undefined }) // 按关键字查询
      rows.value = page.items // 写入表格
    } catch (error) { // 加载失败
      rows.value = [] // 清空表格
      errorMessage.value = error instanceof Error ? error.message : '用户加载失败' // 记录错误
    } finally { // 无论成败
      loading.value = false // 结束加载
    } // 结束 finally
  } // 结束 loadData

  const resetForm = () => { // 重置表单为默认值
    form.username = '' // 清空账户名
    form.password = '' // 清空密码
    form.display_name = '' // 清空显示名
    form.roles = ['warehouse_operator'] // 默认操作员
    form.warehouse_ids = [] // 清空仓库
    form.is_active = true // 默认启用
    formError.value = '' // 清空表单错误
  } // 结束 resetForm

  const openCreate = () => { // 打开新建弹窗
    editing.value = null // 非编辑
    resetForm() // 重置表单
    dialogVisible.value = true // 显示弹窗
  } // 结束 openCreate

  const openEdit = (row: SystemUser) => { // 打开编辑弹窗并回填
    editing.value = row // 记住用户
    form.username = row.username // 回填账户名
    form.password = '' // 密码留空表示不改
    form.display_name = row.display_name // 回填显示名
    form.roles = [...row.roles] // 拷贝角色
    form.warehouse_ids = [...row.warehouse_ids] // 拷贝仓库范围
    form.is_active = row.is_active // 回填启用状态
    formError.value = '' // 清空表单错误
    dialogVisible.value = true // 显示弹窗
  } // 结束 openEdit

  const validateForm = () => { // 校验表单，返回错误文案
    if (!form.username.trim()) return '请填写账户名' // 账户名必填
    if (!form.display_name.trim()) return '请填写显示名' // 显示名必填
    if (!editing.value && form.password.trim().length < 6) return '新建用户密码至少 6 位' // 新建密码长度
    if (editing.value && form.password && form.password.trim().length < 6) return '新密码至少 6 位' // 改密长度
    if (!form.roles.length) return '请至少选择一个角色' // 角色必选
    if (!form.roles.includes('admin') && !form.warehouse_ids.length) return '非管理员请选择仓库范围' // 非管理员需仓库
    return '' // 校验通过
  } // 结束 validateForm

  const removeUser = async (row: SystemUser) => { // 停用/删除用户
    try { // 确认后调用删除
      await ElMessageBox.confirm(`确定停用账号 ${row.username}？停用后无法登录。`, '删除用户', { // 二次确认
        type: 'warning', // 警告样式
        confirmButtonText: '停用', // 确认文案
        cancelButtonText: '取消' // 取消文案
      }) // 结束 confirm
      await deleteUser(row.user_id) // 调删除接口
      ElMessage.success('用户已停用') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 取消或失败
      if (error === 'cancel' || error === 'close') return // 用户取消不提示错误
      ElMessage.error(error instanceof ApiError ? error.message : '删除失败') // 真正失败才提示
    } // 结束 catch
  } // 结束 removeUser

  const submit = async () => { // 保存用户
    formError.value = validateForm() // 先校验
    if (formError.value) return // 校验失败则退出
    submitting.value = true // 开始提交
    try { // 更新或新建
      if (editing.value) { // 编辑模式
        await updateUser(editing.value.user_id, { // 更新用户
          display_name: form.display_name.trim(), // 显示名
          password: form.password.trim() || undefined, // 空密码表示不改
          roles: form.roles, // 角色
          warehouse_ids: form.warehouse_ids, // 仓库范围
          is_active: form.is_active // 启用状态
        }) // 结束 updateUser
      } else { // 新建模式
        await createUser({ // 创建用户
          username: form.username.trim(), // 账户名
          password: form.password.trim(), // 密码
          display_name: form.display_name.trim(), // 显示名
          roles: form.roles, // 角色
          warehouse_ids: form.warehouse_ids, // 仓库范围
          is_active: form.is_active // 启用状态
        }) // 结束 createUser
      } // 结束编辑/新建分支
      dialogVisible.value = false // 关闭弹窗
      ElMessage.success('用户已保存') // 成功提示
      await loadData() // 刷新列表
    } catch (error) { // 保存失败
      formError.value = error instanceof ApiError ? error.message : '保存失败' // 写入表单错误
      ElMessage.error(formError.value) // 弹出错误
    } finally { // 无论成败
      submitting.value = false // 结束提交
    } // 结束 finally
  } // 结束 submit

  onMounted(async () => { // 挂载时拉仓库、角色和用户
    if (isAdmin.value) { // 仅管理员拉选项
      warehouses.value = (await listWarehouses().catch(() => ({ items: [] as Warehouse[], total: 0 }))).items // 仓库失败则空
      const roles = await listRoles().catch(() => ({ items: FALLBACK_ROLES })) // 角色失败用兜底
      const seen = new Set<string>() // 去重已见编码
      const mapped: SystemRole[] = [] // 规范化后的角色
      for (const role of roles.items.length ? roles.items : FALLBACK_ROLES) { // 接口空则用兜底
        const role_code = role.role_code === 'operator' ? 'warehouse_operator' : role.role_code // operator 归一
        const role_name = role.role_code === 'operator' ? '仓库操作员' : role.role_name // 同步显示名
        if (seen.has(role_code)) continue // 跳过重复编码
        seen.add(role_code) // 记录已见
        mapped.push({ ...role, role_code, role_name }) // 推入规范化角色
      } // 结束 for
      roleOptions.value = mapped.length ? mapped : FALLBACK_ROLES // 空映射再兜底
    } // 结束管理员分支
    await loadData() // 加载用户列表
  }) // 结束 onMounted

  const search = () => { // 搜索
    loadData() // 重新加载
  } // 结束 search
  const reset = () => { // 重置
    keyword.value = '' // 清空关键字
    loadData() // 重新加载
  } // 结束 reset

  return { // 暴露给视图
    config, // 页面配置
    app, // 应用仓库
    rows, // 表格行
    warehouses, // 仓库
    roleOptions, // 角色选项
    loading, // 加载状态
    errorMessage, // 列表错误
    formError, // 表单错误
    keyword, // 关键字
    dialogVisible, // 弹窗可见
    submitting, // 提交中
    editing, // 编辑中用户
    isAdmin, // 是否管理员
    form, // 表单
    warehouseName, // 仓库名
    roleName, // 角色名
    loadData, // 刷新
    openCreate, // 新建
    openEdit, // 编辑
    removeUser, // 停用
    submit, // 保存
    search, // 搜索
    reset, // 重置
  } // 结束 return
} // 结束 useUsersController
