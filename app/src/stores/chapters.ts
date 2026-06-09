import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chaptersApi } from '@/api/chapters'
import type { Chapter } from '@/types'

export const useChaptersStore = defineStore('chapters', () => {
  const chapters = ref<Chapter[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchChapters(projectId: string) {
    loading.value = true
    error.value = null
    try {
      chapters.value = await chaptersApi.list(projectId)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load chapters'
    } finally {
      loading.value = false
    }
  }

  function chapterStatus(chapterNum: number): 'done' | 'writing' | 'pending' {
    const ch = chapters.value.find((c) => c.chapter_num === chapterNum)
    if (!ch || !ch.mode) return 'pending'
    if (ch.mode === 'WARN' || ch.mode === 'BLOCK') return 'writing'
    return 'done'
  }

  return {
    chapters,
    loading,
    error,
    fetchChapters,
    chapterStatus,
  }
})
