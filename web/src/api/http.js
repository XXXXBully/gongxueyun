import axios from 'axios'
import router from '../router'
import { useAuthStore } from '../stores/auth'

const TOKEN_KEY = 'auth_token'

export const http = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      if (router.currentRoute.value.path !== '/login') {
        router.replace('/login')
      }
    }
    const message = error?.response?.data?.detail || error?.message || '请求失败'
    return Promise.reject({ ...error, friendlyMessage: message })
  }
)
