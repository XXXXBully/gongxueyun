<template>
  <el-card class="page-card security-page">
    <template #header>
      <div class="page-header">
        <div class="page-title">账号安全</div>
        <div class="page-actions">
          <el-tag :type="status.mfa_enabled ? 'success' : 'warning'">
            {{ status.mfa_enabled ? 'MFA 已启用' : 'MFA 未启用' }}
          </el-tag>
          <el-button :loading="loading" @click="loadStatus">刷新</el-button>
        </div>
      </div>
    </template>

    <div class="security-grid">
      <section class="security-section">
        <div class="section-title">TOTP MFA</div>
        <div class="security-actions">
          <el-button type="primary" :loading="setupLoading" @click="setupVisible = true">生成密钥</el-button>
          <el-button
            type="danger"
            plain
            :disabled="!status.mfa_enabled"
            @click="disableVisible = true"
          >
            停用
          </el-button>
        </div>

        <el-form v-if="setup.secret" class="mfa-form" label-width="90px">
          <el-form-item label="密钥">
            <el-input v-model="setup.secret" readonly>
              <template #append>
                <el-button @click="copySecret">复制</el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="URI">
            <el-input v-model="setup.otpauth_uri" type="textarea" :rows="3" readonly />
          </el-form-item>
          <el-form-item label="验证码">
            <el-input v-model="enableCode" inputmode="numeric" maxlength="6" autocomplete="one-time-code" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="enableLoading" @click="enableMfa">启用 MFA</el-button>
          </el-form-item>
        </el-form>
      </section>
    </div>

    <el-dialog v-model="setupVisible" title="生成 MFA 密钥" width="420px">
      <el-form label-width="90px">
        <el-form-item label="密码">
          <el-input v-model="setupForm.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeSetupDialog">取消</el-button>
        <el-button type="primary" :loading="setupLoading" @click="setupMfa">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="disableVisible" title="停用 MFA" width="420px">
      <el-form label-width="90px">
        <el-form-item label="密码">
          <el-input v-model="disableForm.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item label="验证码">
          <el-input v-model="disableForm.code" inputmode="numeric" maxlength="6" autocomplete="one-time-code" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="disableVisible = false">取消</el-button>
        <el-button type="danger" :loading="disableLoading" @click="disableMfa">停用</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'
import { notifyError, notifySuccess, resolveErrorMessage } from '../utils/notify'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const setupLoading = ref(false)
const enableLoading = ref(false)
const disableLoading = ref(false)
const setupVisible = ref(false)
const disableVisible = ref(false)
const enableCode = ref('')
const status = reactive({ mfa_enabled: false, mfa_pending_setup: false })
const setup = reactive({ secret: '', otpauth_uri: '' })
const setupForm = reactive({ password: '' })
const disableForm = reactive({ password: '', code: '' })

const forceReauth = () => {
  auth.logout()
  router.replace('/login')
}

const loadStatus = async () => {
  loading.value = true
  try {
    const res = await http.get('/auth/mfa/status')
    status.mfa_enabled = !!res.data?.mfa_enabled
    status.mfa_pending_setup = !!res.data?.mfa_pending_setup
  } catch (e) {
    notifyError(resolveErrorMessage(e, '加载安全状态失败'))
  } finally {
    loading.value = false
  }
}

const closeSetupDialog = () => {
  setupVisible.value = false
  setupForm.password = ''
}

const setupMfa = async () => {
  if (!setupForm.password.trim()) {
    notifyError('请输入当前密码')
    return
  }
  setupLoading.value = true
  try {
    const res = await http.post('/auth/mfa/setup', { password: setupForm.password })
    setup.secret = String(res.data?.secret || '')
    setup.otpauth_uri = String(res.data?.otpauth_uri || '')
    enableCode.value = ''
    closeSetupDialog()
  } catch (e) {
    notifyError(resolveErrorMessage(e, '生成 MFA 密钥失败'))
  } finally {
    setupLoading.value = false
  }
}

const enableMfa = async () => {
  if (!enableCode.value.trim()) {
    notifyError('请输入 MFA 验证码')
    return
  }
  enableLoading.value = true
  try {
    await http.post('/auth/mfa/enable', { code: enableCode.value.trim() })
    notifySuccess('MFA 已启用，请重新登录')
    setup.secret = ''
    setup.otpauth_uri = ''
    enableCode.value = ''
    forceReauth()
  } catch (e) {
    notifyError(resolveErrorMessage(e, '启用 MFA 失败'))
  } finally {
    enableLoading.value = false
  }
}

const disableMfa = async () => {
  if (!disableForm.password.trim()) {
    notifyError('请输入当前密码')
    return
  }
  disableLoading.value = true
  try {
    await http.post('/auth/mfa/disable', {
      password: disableForm.password,
      code: disableForm.code || undefined,
    })
    notifySuccess('MFA 已停用，请重新登录')
    disableVisible.value = false
    disableForm.password = ''
    disableForm.code = ''
    forceReauth()
  } catch (e) {
    notifyError(resolveErrorMessage(e, '停用 MFA 失败'))
  } finally {
    disableLoading.value = false
  }
}

const copySecret = async () => {
  try {
    await navigator.clipboard?.writeText(setup.secret)
    notifySuccess('密钥已复制')
  } catch {
    notifyError('复制失败')
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.security-grid {
  display: grid;
  gap: 16px;
}
.security-section {
  display: grid;
  gap: 14px;
  max-width: 760px;
}
.section-title {
  font-size: 15px;
  font-weight: 700;
}
.security-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.mfa-form {
  max-width: 680px;
}
</style>
