import { defineStore } from 'pinia'

const TOKEN_KEY = 'user_auth_token'
const PHONE_KEY = 'user_auth_phone'
const USER_ID_KEY = 'user_auth_user_id'

const readUserId = () => {
  const value = localStorage.getItem(USER_ID_KEY)
  if (!value) return ''
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : value
}

export const useUserAuthStore = defineStore('userAuth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    phone: localStorage.getItem(PHONE_KEY) || '',
    userId: readUserId(),
  }),
  getters: {
    isAuthed: (s) => !!s.token,
  },
  actions: {
    setAuth(token, phone, userId) {
      this.token = token || ''
      this.phone = phone || ''
      this.userId = userId || ''
      if (this.token) localStorage.setItem(TOKEN_KEY, this.token)
      else localStorage.removeItem(TOKEN_KEY)
      if (this.phone) localStorage.setItem(PHONE_KEY, this.phone)
      else localStorage.removeItem(PHONE_KEY)
      if (this.userId !== '' && this.userId !== null && this.userId !== undefined) {
        localStorage.setItem(USER_ID_KEY, String(this.userId))
      } else {
        localStorage.removeItem(USER_ID_KEY)
      }
    },
    logout() {
      this.setAuth('', '', '')
    },
  },
})
