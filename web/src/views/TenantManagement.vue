<template>
  <el-card class="page-card tenant-page">
    <template #header>
      <div class="page-header">
        <div class="page-title">租户管理</div>
        <div class="page-actions">
          <el-input
            v-model="query"
            class="tenant-search"
            placeholder="搜索租户 ID 或名称"
            clearable
            @keyup.enter="onSearch"
          />
          <el-button @click="onSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button type="primary" @click="openCreate">新建租户</el-button>
        </div>
      </div>
    </template>

    <div class="table-wrap">
      <el-table :data="items" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="租户 ID" min-width="160" />
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="状态" width="110">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'active' ? 'success' : 'info'" size="small">
              {{ scope.row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="scope">
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="scope.row.id === 'default' || scope.row.status === 'disabled'"
              @click="disableTenant(scope.row)"
            >
              停用
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchTenants"
        @current-change="fetchTenants"
      />
    </div>

    <el-dialog v-model="createVisible" title="新建租户" width="420px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="租户 ID">
          <el-input v-model="form.id" placeholder="例如 acme" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="租户显示名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createTenant">创建</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { http } from '../api/http'
import { notifyError, notifySuccess, resolveErrorMessage } from '../utils/notify'

const items = ref([])
const loading = ref(false)
const saving = ref(false)
const createVisible = ref(false)
const query = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const form = reactive({ id: '', name: '' })
let fetchAbort = null

const fetchTenants = async () => {
  if (fetchAbort) fetchAbort.abort()
  fetchAbort = new AbortController()
  loading.value = true
  try {
    const res = await http.get('/tenants/page', {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        q: query.value?.trim() || undefined,
      },
      signal: fetchAbort.signal,
    })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    if (e?.code !== 'ERR_CANCELED') {
      notifyError(resolveErrorMessage(e, '获取租户列表失败'))
    }
  } finally {
    loading.value = false
  }
}

const onSearch = () => {
  page.value = 1
  fetchTenants()
}

const resetSearch = () => {
  query.value = ''
  page.value = 1
  fetchTenants()
}

const openCreate = () => {
  form.id = ''
  form.name = ''
  createVisible.value = true
}

const createTenant = async () => {
  const id = form.id.trim()
  const name = form.name.trim()
  if (!id || !name) {
    notifyError('租户 ID 和名称不能为空')
    return
  }
  saving.value = true
  try {
    await http.post('/tenants', { id, name })
    notifySuccess('租户已创建')
    createVisible.value = false
    page.value = 1
    await fetchTenants()
  } catch (e) {
    notifyError(resolveErrorMessage(e, '创建租户失败'))
  } finally {
    saving.value = false
  }
}

const disableTenant = async (tenant) => {
  try {
    await ElMessageBox.confirm(
      `停用租户 ${tenant.name || tenant.id} 后，该租户下的账号不应再继续使用，确认停用吗？`,
      '停用租户',
      { type: 'warning', confirmButtonText: '停用', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await http.patch(`/tenants/${tenant.id}`, { status: 'disabled' })
    notifySuccess('租户已停用')
    await fetchTenants()
  } catch (e) {
    notifyError(resolveErrorMessage(e, '停用租户失败'))
  }
}

onMounted(fetchTenants)
</script>

<style scoped>
.tenant-search {
  width: 220px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
@media (max-width: 768px) {
  .tenant-search {
    width: 100%;
  }
}
</style>
