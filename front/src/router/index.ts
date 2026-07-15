import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getAuthTokens } from '@/services'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/home',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: () => import('@/views/AuthCallbackView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const isLoggedIn = getAuthTokens() !== null

  if (to.name === 'home' && !isLoggedIn) {
    return { name: 'login' }
  }

  if ((to.name === 'login' || to.path === '/') && isLoggedIn) {
    return { name: 'home' }
  }

  return true
})

export default router
