import axios from 'axios'
import router from '../router'
import { useUserAuthStore } from '../stores/userAuth'

export const userHttp = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

const isUserPublicRoute = (path) => path === '/u/login' || path === '/u/register'
const resolveUserRedirect = (value) => {
  if (typeof value !== 'string') return '/u'
  return value === '/u' || value.startsWith('/u/') ? value : '/u'
}

userHttp.interceptors.request.use((config) => {
  const auth = useUserAuthStore()
  if (auth.token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

userHttp.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401) {
      const auth = useUserAuthStore()
      auth.logout()
      const currentPath = router.currentRoute.value.path
      const currentFullPath = resolveUserRedirect(router.currentRoute.value.fullPath)
      if (!isUserPublicRoute(currentPath)) {
        router.replace({ path: '/u/login', query: { redirect: currentFullPath } })
      }
    }
    const message = error?.response?.data?.detail || error?.message || '请求失败'
    return Promise.reject({ ...error, friendlyMessage: message })
  }
)
