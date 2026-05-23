<template>
  <el-card class="page-card">
    <template #header>
      <div class="page-header">
        <div class="page-title">系统设置</div>
        <div class="page-actions">
          <el-button @click="goBack">返回</el-button>
        </div>
      </div>
    </template>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="通知" name="notifications">
        <el-form :model="smtpForm" label-width="120px" v-loading="notificationLoading">
          <el-alert
            title="QQ 邮箱 SMTP 由管理员统一配置。测试发送会直接使用当前表单值，并发送到当前填写的 QQ 邮箱自己。"
            type="info"
            :closable="false"
            style="margin-bottom: 16px;"
          />

          <el-form-item label="启用 SMTP">
            <el-switch v-model="smtpForm.enabled" />
          </el-form-item>
          <el-form-item label="QQ 邮箱">
            <el-input v-model="smtpForm.username" placeholder="例如：demo@qq.com" />
          </el-form-item>
          <el-form-item label="授权码">
            <el-input v-model="smtpForm.password" placeholder="请输入 QQ 邮箱授权码" />
          </el-form-item>
          <el-form-item label="发件人名称">
            <el-input v-model="smtpForm.from" placeholder="例如：工学云签到通知" />
          </el-form-item>

          <el-form-item>
            <div class="settings-actions">
              <el-button type="primary" :loading="notificationSaving" @click="saveNotifications">保存</el-button>
              <el-button :loading="smtpTesting" @click="testSmtp">测试发送</el-button>
            </div>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="工学云代理" name="proxy">
        <el-form :model="proxyForm" label-width="140px" v-loading="proxyLoading">
          <el-alert
            title="代理仅用于手动补卡请求；正常定时打卡、报告提交、缺卡查询和登录不会使用代理。"
            type="info"
            :closable="false"
            style="margin-bottom: 16px;"
          />

          <el-form-item label="启用代理">
            <el-switch v-model="proxyForm.enabled" />
          </el-form-item>
          <el-form-item label="动态代理接口">
            <el-input
              v-model="proxyForm.apiUrl"
              type="textarea"
              :rows="4"
              resize="vertical"
              placeholder="http://capi.51daili.com/traffic/getip?...&accessName=...&accessPassword=..."
            />
          </el-form-item>
          <el-form-item label="缓存秒数">
            <el-input-number v-model="proxyForm.ttlSeconds" :min="0" :max="600" :step="1" />
          </el-form-item>
          <el-form-item label="接口超时秒数">
            <el-input-number v-model="proxyForm.apiTimeoutSeconds" :min="0" :max="30" :step="1" />
          </el-form-item>
          <el-form-item label="静态代理列表">
            <el-input
              v-model="proxyForm.proxyUrls"
              type="textarea"
              :rows="4"
              resize="vertical"
              placeholder="http://user:pass@1.2.3.4:8080"
            />
          </el-form-item>

          <el-form-item>
            <div class="settings-actions">
              <el-button type="primary" :loading="proxySaving" @click="saveProxy">保存</el-button>
            </div>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../api/http'
import { notifyError, notifyInfo, notifySuccess, notifyWarning, resolveErrorMessage } from '../utils/notify'

const router = useRouter()
const activeTab = ref('notifications')
const notificationLoading = ref(false)
const notificationSaving = ref(false)
const smtpTesting = ref(false)
const proxyLoading = ref(false)
const proxySaving = ref(false)

const smtpForm = reactive({
  enabled: true,
  username: '',
  password: '',
  from: '工学云签到通知',
})

const proxyForm = reactive({
  enabled: false,
  apiUrl: '',
  ttlSeconds: 55,
  apiTimeoutSeconds: 10,
  proxyUrls: '',
})

const loadNotificationSettings = async () => {
  notificationLoading.value = true
  try {
    const res = await http.get('/settings/notifications')
    const smtp = res.data?.smtp || {}
    smtpForm.enabled = !!smtp.enabled
    smtpForm.username = String(smtp.username || '')
    smtpForm.password = String(smtp.password || '')
    smtpForm.from = String(smtp.from || '工学云签到通知')
  } catch (error) {
    notifyError(`加载通知设置失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    notificationLoading.value = false
  }
}

const loadProxySettings = async () => {
  proxyLoading.value = true
  try {
    const res = await http.get('/settings/proxy')
    const proxy = res.data?.proxy || {}
    proxyForm.enabled = !!proxy.enabled
    proxyForm.apiUrl = String(proxy.apiUrl || '')
    proxyForm.ttlSeconds = Number(proxy.ttlSeconds ?? 55)
    proxyForm.apiTimeoutSeconds = Number(proxy.apiTimeoutSeconds ?? 10)
    proxyForm.proxyUrls = String(proxy.proxyUrls || '')
  } catch (error) {
    notifyError(`加载代理设置失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    proxyLoading.value = false
  }
}

const buildNotificationPayload = () => ({
  smtp: {
    enabled: !!smtpForm.enabled,
    username: String(smtpForm.username || '').trim(),
    password: String(smtpForm.password || '').trim(),
    from: String(smtpForm.from || '').trim(),
  },
})

const buildProxyPayload = () => ({
  proxy: {
    enabled: !!proxyForm.enabled,
    apiUrl: String(proxyForm.apiUrl || '').trim(),
    ttlSeconds: Number(proxyForm.ttlSeconds || 0),
    apiTimeoutSeconds: Number(proxyForm.apiTimeoutSeconds || 0),
    proxyUrls: String(proxyForm.proxyUrls || '').trim(),
  },
})

const validateForTest = () => {
  if (!String(smtpForm.username || '').trim()) {
    notifyWarning('请先填写 QQ 邮箱')
    return false
  }
  if (!String(smtpForm.password || '').trim()) {
    notifyWarning('测试发送前请先填写授权码')
    return false
  }
  if (!String(smtpForm.from || '').trim()) {
    notifyWarning('请先填写发件人名称')
    return false
  }
  return true
}

const validateProxy = () => {
  if (!proxyForm.enabled) return true
  if (String(proxyForm.apiUrl || '').trim() || String(proxyForm.proxyUrls || '').trim()) return true
  notifyWarning('启用代理时请填写动态代理接口或静态代理列表')
  return false
}

const flushUiMessage = async () => {
  await nextTick()
  await new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

const goBack = () => {
  notifyInfo('正在返回上一页')
  router.back()
}

const saveNotifications = async () => {
  notificationSaving.value = true
  try {
    notifyInfo('正在保存通知设置')
    await flushUiMessage()
    await http.patch('/settings/notifications', buildNotificationPayload())
    notifySuccess('保存成功')
    await loadNotificationSettings()
  } catch (error) {
    notifyError(`保存失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    notificationSaving.value = false
  }
}

const saveProxy = async () => {
  if (!validateProxy()) return
  proxySaving.value = true
  try {
    notifyInfo('正在保存代理设置')
    await flushUiMessage()
    await http.patch('/settings/proxy', buildProxyPayload())
    notifySuccess('保存成功')
    await loadProxySettings()
  } catch (error) {
    notifyError(`保存失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    proxySaving.value = false
  }
}

const testSmtp = async () => {
  if (!validateForTest()) return
  smtpTesting.value = true
  try {
    notifyInfo('正在发送测试邮件')
    await flushUiMessage()
    const res = await http.post('/settings/notifications/smtp/test', buildNotificationPayload())
    notifySuccess(`测试发送成功：已发送到 ${res.data?.to || smtpForm.username}`)
  } catch (error) {
    notifyError(`测试发送失败：${resolveErrorMessage(error, '请求失败')}`)
  } finally {
    smtpTesting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadNotificationSettings(), loadProxySettings()])
})
</script>

<style scoped>
.settings-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
