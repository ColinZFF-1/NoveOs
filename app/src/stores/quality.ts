import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { metricsApi } from '@/api/metrics'
import { guardsApi } from '@/api/guards'
import type { ChapterMetric, GuardResult } from '@/types'

export const useQualityStore = defineStore('quality', () => {
  const metrics = ref<ChapterMetric[]>([])
  const guards = ref<GuardResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const avgWordCount = computed(() => {
    if (metrics.value.length === 0) return 0
    const sum = metrics.value.reduce((a, b) => a + (b.word_count || 0), 0)
    return Math.round(sum / metrics.value.length)
  })

  const avgTaDensity = computed(() => {
    if (metrics.value.length === 0) return 0
    const sum = metrics.value.reduce((a, b) => a + (b.ta_density || 0), 0)
    return (sum / metrics.value.length).toFixed(1)
  })

  const avgIwrScore = computed(() => {
    if (metrics.value.length === 0) return 0
    const sum = metrics.value.reduce((a, b) => a + (b.iwr_score || 0), 0)
    return (sum / metrics.value.length).toFixed(2)
  })

  const guardSummary = computed(() => {
    const pass = guards.value.filter((g) => g.level === 'PASS').length
    const warn = guards.value.filter((g) => g.level === 'WARN').length
    const block = guards.value.filter((g) => g.level === 'BLOCKING').length
    const info = guards.value.filter((g) => g.level === 'INFO').length
    return { pass, warn, block, info, total: guards.value.length }
  })

  async function fetchMetrics(projectId: string) {
    loading.value = true
    error.value = null
    try {
      metrics.value = await metricsApi.list(projectId)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load metrics'
    } finally {
      loading.value = false
    }
  }

  async function fetchGuards(projectId: string) {
    loading.value = true
    error.value = null
    try {
      guards.value = await guardsApi.list(projectId)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load guards'
    } finally {
      loading.value = false
    }
  }

  async function runGuards(projectId: string, content: string) {
    loading.value = true
    error.value = null
    try {
      guards.value = await guardsApi.run(projectId, content)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to run guards'
    } finally {
      loading.value = false
    }
  }

  return {
    metrics,
    guards,
    loading,
    error,
    avgWordCount,
    avgTaDensity,
    avgIwrScore,
    guardSummary,
    fetchMetrics,
    fetchGuards,
    runGuards,
  }
})
