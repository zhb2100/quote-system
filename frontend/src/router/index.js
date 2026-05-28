import { createRouter, createWebHistory } from 'vue-router'
import { useApi } from '../composables/useApi'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { guest: true } },
  { path: '/', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { auth: true } },
  // :id? 参数已移除，QuotesView 仅作列表页，详情通过 project-detail 路由查看
  { path: '/quotes', name: 'quotes', component: () => import('../views/QuotesView.vue'), meta: { auth: true } },
  { path: '/new-quote', name: 'newquote', component: () => import('../views/NewQuoteView.vue'), meta: { auth: true, admin: true } },
  { path: '/project/:id', name: 'project-detail', component: () => import('../views/ProjectDetailView.vue'), meta: { auth: true } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { auth: true, admin: true } },
  // 404 catch-all
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to, from, next) => {
  const { isLoggedIn, isAdmin } = useApi()
  if (to.meta.auth && !isLoggedIn()) return next({ name: 'login' })
  if (to.meta.admin && !isAdmin()) return next({ name: 'dashboard' })
  if (to.meta.guest && isLoggedIn()) return next({ name: 'dashboard' })
  next()
})

export default router
