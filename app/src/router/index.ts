import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/dashboard',
      name: 'Dashboard',
      meta: { title: '项目总览' },
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/pipeline',
      name: 'Pipeline',
      meta: { title: '流水线控制室' },
      component: () => import('@/views/PipelineView.vue'),
    },
    {
      path: '/chapters',
      name: 'Chapters',
      meta: { title: '章节管理器' },
      component: () => import('@/views/ChaptersView.vue'),
    },
    {
      path: '/characters',
      name: 'Characters',
      meta: { title: '人物追踪器' },
      component: () => import('@/views/CharactersView.vue'),
    },
    {
      path: '/quality',
      name: 'Quality',
      meta: { title: '质量监控台' },
      component: () => import('@/views/QualityView.vue'),
    },
    {
      path: '/outline',
      name: 'Outline',
      meta: { title: '大纲编辑器' },
      component: () => import('@/views/OutlineView.vue'),
    },
    // Legacy routes (keep for compatibility)
    {
      path: '/plan',
      name: 'Plan',
      meta: { title: '规划' },
      component: () => import('@/views/PlanView.vue'),
    },
    {
      path: '/write',
      name: 'Write',
      meta: { title: '写作' },
      component: () => import('@/views/WriteView.vue'),
    },
    {
      path: '/review',
      name: 'Review',
      meta: { title: '审阅' },
      component: () => import('@/views/ReviewView.vue'),
    },
    {
      path: '/operate',
      name: 'Operate',
      meta: { title: '运营' },
      component: () => import('@/views/OperateView.vue'),
    },

  ],
})

export default router
