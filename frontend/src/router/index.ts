import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../layouts/AppShell.vue'
import { useAppStore } from '../stores/app'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
    { path: '/:pathMatch(.*)*', component: AppShell }
  ]
})

export default router

router.beforeEach(async (to) => {
  const app = useAppStore()

  if (app.token && !app.currentUser) {
    const sessionValid = await app.restoreSession()
    if (!sessionValid) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  if (to.meta.public) {
    return app.token ? { path: '/dashboard' } : true
  }
  if (!app.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})
