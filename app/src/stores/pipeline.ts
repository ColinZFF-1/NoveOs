import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pipelineApi } from '@/api/pipeline'
import type { PipelineStatus } from '@/types'

export const usePipelineStore = defineStore('pipeline', () => {
  const status = ref<PipelineStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStatus(projectId: string) {
    loading.value = true
    error.value = null
    try {
      status.value = await pipelineApi.status(projectId)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load pipeline status'
    } finally {
      loading.value = false
    }
  }

  async function start(projectId: string, chapterRange = '1-100') {
    loading.value = true
    error.value = null
    try {
      const result = await pipelineApi.start(projectId, { chapter_range: chapterRange })
      status.value = { ...status.value!, pipeline_id: result.pipeline_id, status: 'writing', is_running: true, can_start: false }
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to start pipeline'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function pause(projectId: string) {
    loading.value = true
    try {
      await pipelineApi.pause(projectId)
      if (status.value) status.value.is_running = false
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to pause pipeline'
    } finally {
      loading.value = false
    }
  }

  async function stop(projectId: string) {
    loading.value = true
    try {
      await pipelineApi.stop(projectId)
      if (status.value) {
        status.value.is_running = false
        status.value.can_start = true
      }
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to stop pipeline'
    } finally {
      loading.value = false
    }
  }

  return {
    status,
    loading,
    error,
    fetchStatus,
    start,
    pause,
    stop,
  }
})
