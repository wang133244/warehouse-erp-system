<!-- 用户与权限（仅 admin）。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入筛选条。
import FilterPanel from '../components/business/FilterPanel.vue' // import FilterPanel f
// 引入用户页控制器。
import { useUsersController } from '../controllers/usersController' // import { useUsersCon

// 从控制器取出用户列表、表单与增删改方法。
const { // const {
  // 页面文案配置。
  config, // config,
  // 用户行。
  rows, // rows,
  // 仓库选项。
  warehouses, // warehouses,
  // 角色选项。
  roleOptions, // roleOptions,
  // 加载中。
  loading, // loading,
  // 列表错误文案。
  errorMessage, // errorMessage,
  // 表单错误文案。
  formError, // formError,
  // 筛选关键字。
  keyword, // keyword,
  // 用户弹窗是否打开。
  dialogVisible, // dialogVisible,
  // 保存中。
  submitting, // submitting,
  // 正在编辑的用户。
  editing, // editing,
  // 当前登录者是否为管理员。
  isAdmin, // isAdmin,
  // 新建/编辑表单。
  form, // form,
  // 仓库 ID 转名称。
  warehouseName, // warehouseName,
  // 角色码转名称。
  roleName, // roleName,
  // 打开新建。
  openCreate, // openCreate,
  // 打开编辑。
  openEdit, // openEdit,
  // 删除用户。
  removeUser, // removeUser,
  // 保存用户。
  submit, // submit,
  // 按关键字查询。
  search, // search,
  // 重置筛选。
  reset // reset
} = useUsersController() // } = useUsersControll

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 用户管理页主容器。 -->
  <main class="workspace-page" data-testid="users-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 表格卡片。 -->
    <el-card shadow="never" class="table-card"> <!-- <el-card shadow="nev -->
      <!-- 非管理员只显示提示。 -->
      <p v-if="!isAdmin" class="hint">仅系统管理员可以维护用户账号</p> <!-- <p v-if="!isAdmin" c -->
      <!-- 管理员可见的新建按钮。 -->
      <div v-else class="toolbar"> <!-- <div v-else class="t -->
        <!-- 打开新建用户弹窗。 -->
        <el-button type="primary" data-testid="create-user" @click="openCreate">新建用户</el-button> <!-- <el-button type="pri -->
      </div> <!-- 结束 div -->
      <!-- 管理员可见的筛选条。 -->
      <FilterPanel v-if="isAdmin" v-model="keyword" :filters="config.filters" @search="search" @reset="reset" /> <!-- <FilterPanel v-if="i -->
      <!-- 接口错误警告。 -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" show-icon :closable="false" class="table-error" /> <!-- <el-alert v-if="erro -->
      <!-- 管理员可见的用户表。 -->
      <el-table v-if="isAdmin" v-loading="loading" :data="rows" class="data-table" height="420"> <!-- <el-table v-if="isAd -->
        <!-- 登录账号列。 -->
        <el-table-column prop="username" label="账户名" min-width="140" /> <!-- <el-table-column pro -->
        <!-- 显示名列。 -->
        <el-table-column prop="display_name" label="显示名" min-width="140" /> <!-- <el-table-column pro -->
        <!-- 角色列。 -->
        <el-table-column label="角色" min-width="180"> <!-- <el-table-column lab -->
          <!-- 多个角色码转中文后用斜杠拼接。 -->
          <template #default="{ row }">{{ row.roles.map(roleName).join(' / ') }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 仓库范围列。 -->
        <el-table-column label="仓库范围" min-width="180"> <!-- <el-table-column lab -->
          <!-- 无仓库表示全部仓库。 -->
          <template #default="{ row }">{{ row.warehouse_ids.length ? row.warehouse_ids.map(warehouseName).join('、') : '全部仓库' }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 启用状态列。 -->
        <el-table-column label="状态" min-width="100"> <!-- <el-table-column lab -->
          <!-- 布尔转启用/停用。 -->
          <template #default="{ row }">{{ row.is_active ? '启用' : '停用' }}</template> <!-- 页面模板 -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 右侧操作列。 -->
        <el-table-column label="操作" fixed="right" width="160"> <!-- <el-table-column lab -->
          <!-- 编辑与删除。 -->
          <template #default="{ row }"> <!-- 页面模板 -->
            <!-- 打开编辑弹窗。 -->
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button> <!-- <el-button text type -->
            <!-- 删除该用户。 -->
            <el-button :data-testid="`delete-user-${row.user_id}`" text type="danger" @click="removeUser(row)">删除</el-button> <!-- <el-button :data-tes -->
          </template> <!-- 结束 template -->
        </el-table-column> <!-- 结束 el-table-column -->
        <!-- 表格空状态。 -->
        <template #empty> <!-- 页面模板 -->
          <!-- 无用户时的占位。 -->
          <EmptyDataState title="暂无用户" :description="errorMessage || config.emptyDescription" /> <!-- <EmptyDataState titl -->
        </template> <!-- 结束 template -->
      </el-table> <!-- 结束 el-table -->
    </el-card> <!-- 结束 el-card -->
    <!-- 新建/编辑用户弹窗。 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新建用户'" width="520px"> <!-- <el-dialog v-model=" -->
      <!-- 表单校验错误。 -->
      <p v-if="formError" class="hint" data-testid="user-form-error">{{ formError }}</p> <!-- <p v-if="formError"  -->
      <!-- 用户表单。 -->
      <el-form label-width="90px"> <!-- <el-form label-width -->
        <!-- 登录账号，编辑时不可改。 -->
        <el-form-item label="账户名" required> <!-- <el-form-item label= -->
          <!-- 账号输入。 -->
          <el-input v-model="form.username" :disabled="Boolean(editing)" placeholder="登录账号" /> <!-- <el-input v-model="f -->
        </el-form-item> <!-- 结束 el-form-item -->
        <!-- 密码，新建必填，编辑可留空。 -->
        <el-form-item label="密码" :required="!editing"> <!-- <el-form-item label= -->
          <!-- 密码输入，可显示明文。 -->
          <el-input v-model="form.password" type="password" show-password :placeholder="editing ? '留空则不修改' : '至少 6 位'" /> <!-- <el-input v-model="f -->
        </el-form-item> <!-- 结束 el-form-item -->
        <!-- 界面显示名。 -->
        <el-form-item label="显示名" required> <!-- <el-form-item label= -->
          <!-- 显示名输入。 -->
          <el-input v-model="form.display_name" placeholder="界面显示名称" /> <!-- <el-input v-model="f -->
        </el-form-item> <!-- 结束 el-form-item -->
        <!-- 角色多选。 -->
        <el-form-item label="角色" required> <!-- <el-form-item label= -->
          <!-- 角色下拉。 -->
          <el-select v-model="form.roles" multiple placeholder="请选择角色"> <!-- <el-select v-model=" -->
            <!-- 每个角色一个选项。 -->
            <el-option v-for="item in roleOptions" :key="item.role_code" :label="item.role_name" :value="item.role_code" /> <!-- <el-option v-for="it -->
          </el-select> <!-- 结束 el-select -->
        </el-form-item> <!-- 结束 el-form-item -->
        <!-- 非管理员必须指定仓库。 -->
        <el-form-item label="仓库范围" :required="!form.roles.includes('admin')"> <!-- <el-form-item label= -->
          <!-- 仓库多选。 -->
          <el-select v-model="form.warehouse_ids" multiple placeholder="非管理员必须指定仓库"> <!-- <el-select v-model=" -->
            <!-- 每个仓库一个选项。 -->
            <el-option v-for="item in warehouses" :key="item.warehouse_id" :label="item.warehouse_name" :value="item.warehouse_id" /> <!-- <el-option v-for="it -->
          </el-select> <!-- 结束 el-select -->
        </el-form-item> <!-- 结束 el-form-item -->
        <!-- 启用开关。 -->
        <el-form-item label="状态"> <!-- <el-form-item label= -->
          <!-- 启用/停用切换。 -->
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /> <!-- <el-switch v-model=" -->
        </el-form-item> <!-- 结束 el-form-item -->
      </el-form> <!-- 结束 el-form -->
      <!-- 底部操作槽。 -->
      <template #footer> <!-- 页面模板 -->
        <!-- 关闭弹窗。 -->
        <el-button @click="dialogVisible = false">取消</el-button> <!-- <el-button @click="d -->
        <!-- 保存用户。 -->
        <el-button type="primary" data-testid="save-user" :loading="submitting" @click="submit">保存</el-button> <!-- <el-button type="pri -->
      </template> <!-- 结束 template -->
    </el-dialog> <!-- 结束 el-dialog -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台页边距与最大宽度。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; } /* .workspace-page { pa */
/* 工具条内边距。 */
.toolbar { padding: 16px 16px 0; } /* .toolbar { padding:  */
/* 提示文字内边距与次要色。 */
.hint { padding: 18px; color: var(--muted); } /* .hint { padding: 18p */
/* 表格上方错误条间距。 */
.table-error { margin: 16px; } /* .table-error { margi */
/* 表格通栏并带顶部分割线。 */
.data-table { width: 100%; border-top: 1px solid var(--line); } /* .data-table { width: */
</style> <!-- 结束 style -->
