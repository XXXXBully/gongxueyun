import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUserAuthStore } from '../stores/userAuth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true, area: 'admin' } },
  { path: '/u/login', component: () => import('../views/user/UserLogin.vue'), meta: { public: true, area: 'user' } },
  { path: '/u/register', component: () => import('../views/user/UserRegister.vue'), meta: { public: true, area: 'user' } },
  {
    path: '/u',
    component: () => import('../views/user/UserLayout.vue'),
    meta: { area: 'user' },
    children: [
      { path: '', component: () => import('../views/user/UserHome.vue'), meta: { area: 'user' } },
    ],
  },
  {
    path: '/u/settings',
    component: () => import('../views/user/UserLayout.vue'),
    meta: { area: 'user' },
    children: [
      { path: '', component: () => import('../views/user/UserSettings.vue'), meta: { area: 'user' } },
    ],
  },
  { path: '/', component: () => import('../views/UserList.vue'), meta: { roles: ['admin', 'operator', 'viewer'] } },
  { path: '/audit', component: () => import('../views/AuditLogs.vue'), meta: { roles: ['admin'] } },
  { path: '/settings', component: () => import('../views/NotificationSettings.vue'), meta: { roles: ['admin'] } },
  { path: '/settings/notifications', component: () => import('../views/NotificationSettings.vue'), meta: { roles: ['admin'] } },
  { path: '/create', component: () => import('../views/UserEdit.vue'), meta: { roles: ['admin', 'operator'] } },
  { path: '/edit/:id', component: () => import('../views/UserEdit.vue'), meta: { roles: ['admin', 'operator'] } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const isUserRoute = (path) => path === '/u' || path.startsWith('/u/')
const isUserPublicRoute = (path) => path === '/u/login' || path === '/u/register'

router.beforeEach((to) => {
  const auth = useAuthStore()
  const userAuth = useUserAuthStore()

  if (auth.isAuthed && !auth.role) auth.logout()

  if (isUserRoute(to.path)) {
    if (isUserPublicRoute(to.path)) {
      if (userAuth.isAuthed) return '/u'
      return true
    }
    if (!userAuth.isAuthed) {
      return { path: '/u/login', query: { redirect: to.fullPath } }
    }
    return true
  }

  if (to.meta.public) {
    if (auth.isAuthed && to.path === '/login') return '/'
    return true
  }
  if (!auth.isAuthed) return { path: '/login', query: { redirect: to.fullPath } }
  const roles = to.meta.roles
  if (!roles) return true
  if (roles.includes(auth.role)) return true
  if (to.path !== '/') return '/'
  auth.logout()
  return { path: '/login' }
})

export default router
