import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/write' },
    {
      path: '/plan',
      name: 'Plan',
      component: () => import('@/views/PlanView.vue'),
    },
    {
      path: '/write',
      name: 'Write',
      component: () => import('@/views/WriteView.vue'),
    },
    {
      path: '/review',
      name: 'Review',
      component: () => import('@/views/ReviewView.vue'),
    },
    {
      path: '/operate',
      name: 'Operate',
      component: () => import('@/views/OperateView.vue'),
    },
  ],
})

export default router
