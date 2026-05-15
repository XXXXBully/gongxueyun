<template>
  <div class="login-page">
    <div class="login-card-wrap">
      <el-card class="login-card page-card">
        <template #header>
          <div class="login-header">
            <div class="login-title">注册用户端账号</div>
            <div class="login-subtitle">注册后即可进入 /u 工作台</div>
          </div>
        </template>
        <el-form :model="form" @keyup.enter="submit">
          <el-form-item label="手机号/账号">
            <el-input v-model="form.phone" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input v-model="form.confirmPassword" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" style="width: 100%" @click="submit">注册并进入</el-button>
          </el-form-item>
          <div class="login-footer">
            <span>已有账号？</span>
            <el-button link type="primary" @click="router.push('/u/login')">去登录</el-button>
          </div>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { userHttp } from '../../api/userHttp'
import { useUserAuthStore } from '../../stores/userAuth'
import { notifyError, notifyWarning, resolveErrorMessage } from '../../utils/notify'

const router = useRouter()
const route = useRoute()
const auth = useUserAuthStore()
const loading = ref(false)
const form = reactive({
  phone: '',
  password: '',
  confirmPassword: '',
})

const resolveUserRedirect = () => {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && (redirect === '/u' || redirect.startsWith('/u/')) ? redirect : '/u'
}

const submit = async () => {
  if (!form.phone || !form.password || !form.confirmPassword) {
    notifyWarning('请完整填写注册信息')
    return
  }
  if (form.password.length < 6) {
    notifyWarning('密码至少 6 位')
    return
  }
  if (form.password !== form.confirmPassword) {
    notifyWarning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    const res = await userHttp.post('/app/auth/register', {
      phone: form.phone,
      password: form.password,
    })
    const token = res.data?.token
    if (!token) throw new Error('no token')
    auth.setAuth(token, res.data?.phone, res.data?.user_id)
    router.replace(resolveUserRedirect())
  } catch (e) {
    notifyError(resolveErrorMessage(e, '注册失败'))
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
.login-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  font-size: 13px;
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
