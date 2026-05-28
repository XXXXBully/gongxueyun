<template>
  <div class="login-page">
    <div class="login-card-wrap">
      <el-card class="login-card page-card">
        <template #header>
          <div class="login-header">
            <div class="login-title">工学云管理平台</div>
            <div class="login-subtitle">后台登录</div>
          </div>
        </template>
        <el-form :model="form" @keyup.enter="submit">
          <el-form-item label="租户">
            <el-input v-model="form.tenant_id" autocomplete="organization" />
          </el-form-item>
          <el-form-item label="账号">
            <el-input v-model="form.username" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
          </el-form-item>
          <el-form-item label="MFA">
            <el-input v-model="form.mfa_code" inputmode="numeric" maxlength="6" autocomplete="one-time-code" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" style="width: 100%" @click="submit">登录</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'
import { notifyWarning, notifyError, resolveErrorMessage } from '../utils/notify'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  tenant_id: 'default',
  username: '',
  password: '',
  mfa_code: ''
})

const loading = ref(false)

const submit = async () => {
  if (!form.username || !form.password) {
    notifyWarning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const res = await http.post('/auth/login', {
      username: form.username,
      password: form.password,
      tenant_id: form.tenant_id,
      mfa_code: form.mfa_code || undefined,
    })
    if (!res.data?.role) throw new Error('login response missing role')
    auth.setAuth(res.data?.token || 'cookie', res.data?.username, res.data?.role, res.data?.tenant_id || form.tenant_id)
    router.replace('/')
  } catch (e) {
    notifyError(resolveErrorMessage(e, '登录失败'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(900px 360px at 20% 10%, rgba(64, 158, 255, 0.14), transparent 60%),
    radial-gradient(900px 360px at 80% 0%, rgba(103, 194, 58, 0.1), transparent 55%),
    radial-gradient(600px 300px at 50% 100%, rgba(230, 162, 60, 0.1), transparent 60%),
    var(--el-bg-color-page);
}
.login-card-wrap {
  width: 100%;
  max-width: 420px;
}
.login-card {
  width: 100%;
}
.login-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.login-title {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.2px;
}
.login-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
:global(html.dark) .login-page {
  background:
    radial-gradient(900px 360px at 20% 10%, rgba(64, 158, 255, 0.16), transparent 60%),
    radial-gradient(900px 360px at 80% 0%, rgba(103, 194, 58, 0.12), transparent 55%),
    radial-gradient(600px 300px at 50% 100%, rgba(230, 162, 60, 0.12), transparent 60%),
    var(--el-bg-color-page);
}
</style>
