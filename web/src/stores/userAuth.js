import { defineStore } from 'pinia'

const META_KEY = 'user_auth_meta'

const readMeta = () => {
  try {
    return JSON.parse(sessionStorage.getItem(META_KEY) || '{}')
  } catch {
    return {}
  }
}

export const useUserAuthStore = defineStore('userAuth', {
  state: () => {
    const meta = readMeta()
    return {
      authed: meta.authed === true,
      phone: meta.phone || '',
      userId: meta.userId || '',
      tenantId: meta.tenantId || 'default',
      sessionChecked: false,
    }
  },
  getters: {
    isAuthed: (s) => !!s.authed,
  },
  actions: {
    setAuth(_token, phone, userId, tenantId = 'default') {
      this.authed = !!(_token || phone || userId)
      this.phone = phone || ''
      this.userId = userId || ''
      this.tenantId = tenantId || 'default'
      this.sessionChecked = false
      if (this.authed) {
        sessionStorage.setItem(META_KEY, JSON.stringify({
          authed: true,
          phone: this.phone,
          userId: this.userId,
          tenantId: this.tenantId,
        }))
      } else {
        sessionStorage.removeItem(META_KEY)
      }
    },
    logout() {
      this.authed = false
      this.phone = ''
      this.userId = ''
      this.tenantId = 'default'
      this.sessionChecked = false
      sessionStorage.removeItem(META_KEY)
    },
    async validateSession() {
      try {
        const response = await fetch('/api/app/me', { credentials: 'include' })
        if (!response.ok) throw new Error('session invalid')
        const data = await response.json()
        this.authed = true
        this.phone = data.app_phone || ''
        this.userId = data.task_user?.id || this.userId || ''
        this.tenantId = data.tenant_id || 'default'
        this.sessionChecked = true
        sessionStorage.setItem(META_KEY, JSON.stringify({
          authed: true,
          phone: this.phone,
          userId: this.userId,
          tenantId: this.tenantId,
        }))
        return true
      } catch {
        this.authed = false
        this.phone = ''
        this.userId = ''
        this.tenantId = 'default'
        this.sessionChecked = true
        sessionStorage.removeItem(META_KEY)
        return false
      }
    },
  },
})
