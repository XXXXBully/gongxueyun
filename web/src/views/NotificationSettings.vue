<template>
  <el-card class="page-card">
    <template #header>
      <div class="page-header">
        <div class="page-title">通知设置</div>
        <div class="page-actions">
          <el-button @click="goBack">返回</el-button>
        </div>
      </div>
    </template>

    <el-form :model="form" label-width="120px" v-loading="loading">
      <el-alert
        title="QQ 邮箱 SMTP 由管理员统一配置。测试发送会直接使用当前表单值，并发送到当前填写的 QQ 邮箱自己。"
        type="info"
        :closable="false"
        style="margin-bottom: 16px;"
      />

      <el-form-item label="启用 SMTP">
        <el-switch v-model="form.enabled" />
      </el-form-item>
      <el-form-item label="QQ 邮箱">
        <el-input v-model="form.username" placeholder="例如：demo@qq.com" />
      </el-form-item>
      <el-form-item label="授权码">
        <el-input v-model="form.password" placeholder="请输入 QQ 邮箱授权码" />
      </el-form-item>
      <el-form-item label="发件人名称">
        <el-input v-model="form.from" placeholder="例如：工学云签到通知" />
      </el-form-item>

      <el-form-item>
        <div class="settings-actions">
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button :loading="testing" @click="testSmtp">测试发送</el-button>
        </div>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../api/http'
import { notifyError, notifyInfo, notifySuccess, notifyWarning, resolveErrorMessage } from '../utils/notify'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const form = reactive({
  enabled: true,
  username: '',
  password: '',
  from: '工学云签到通知',
})

const loadSettings = async () => {
  loading.value = true
  try {
    const res = await http.get('/settings/notifications')
    const smtp = res.data?.smtp || {}
    form.enabled = !!smtp.enabled
    form.username = String(smtp.username || '')
    form.password = String(smtp.password || '')
    form.from = String(smtp.from || '工学云签到通知')
  } catch (error) {
    notifyError(`加载失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    loading.value = false
  }
}

const buildPayload = () => ({
  smtp: {
    enabled: !!form.enabled,
    username: String(form.username || '').trim(),
    password: String(form.password || '').trim(),
    from: String(form.from || '').trim(),
  },
})

const validateForTest = () => {
  if (!String(form.username || '').trim()) {
    notifyWarning('请先填写 QQ 邮箱')
    return false
  }
  if (!String(form.password || '').trim()) {
    notifyWarning('测试发送前请先填写授权码')
    return false
  }
  if (!String(form.from || '').trim()) {
    notifyWarning('请先填写发件人名称')
    return false
  }
  return true
}

const flushUiMessage = async () => {
  await nextTick()
  await new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

const goBack = () => {
  notifyInfo('正在返回上一页')
  router.back()
}

const save = async () => {
  saving.value = true
  try {
    notifyInfo('正在保存通知设置')
    await flushUiMessage()
    await http.patch('/settings/notifications', buildPayload())
    notifySuccess('保存成功')
    await loadSettings()
  } catch (error) {
    notifyError(`保存失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    saving.value = false
  }
}

const testSmtp = async () => {
  if (!validateForTest()) return
  testing.value = true
  try {
    notifyInfo('正在发送测试邮件')
    await flushUiMessage()
    const res = await http.post('/settings/notifications/smtp/test', buildPayload())
    notifySuccess(`测试发送成功：已发送到 ${res.data?.to || form.username}`)
  } catch (error) {
    notifyError(`测试发送失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    testing.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
