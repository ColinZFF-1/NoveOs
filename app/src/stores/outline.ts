import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { outlineApi } from '@/api/outline'
import type { ChapterOutline, Debt, Foreshadowing, Skill, Rule } from '@/types'

export const useOutlineStore = defineStore('outline', () => {
  const outlines = ref<ChapterOutline[]>([])
  const debts = ref<Debt[]>([])
  const foreshadowing = ref<Foreshadowing[]>([])
  const skills = ref<Skill[]>([])
  const rules = ref<Rule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeTab = ref<'outline' | 'debts' | 'skills' | 'rules'>('outline')

  const debtStats = computed(() => {
    const active = debts.value.filter((d) => d.status === 'active').length
    const collected = debts.value.filter((d) => d.status === 'collected').length
    const abandoned = debts.value.filter((d) => d.status === 'abandoned').length
    return { active, collected, abandoned, total: debts.value.length }
  })

  const fsStats = computed(() => {
    const active = foreshadowing.value.filter((f) => f.status === 'active').length
    const collected = foreshadowing.value.filter((f) => f.status === 'collected').length
    return { active, collected, total: foreshadowing.value.length }
  })

  async function fetchAll(projectId: string) {
    loading.value = true
    error.value = null
    try {
      const [o, d, f, s, r] = await Promise.all([
        outlineApi.list(projectId),
        outlineApi.debts(projectId),
        outlineApi.foreshadowing(projectId),
        outlineApi.skills(projectId),
        outlineApi.rules(projectId),
      ])
      outlines.value = o
      debts.value = d
      foreshadowing.value = f
      skills.value = s
      rules.value = r
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load outline data'
    } finally {
      loading.value = false
    }
  }

  return {
    outlines,
    debts,
    foreshadowing,
    skills,
    rules,
    loading,
    error,
    activeTab,
    debtStats,
    fsStats,
    fetchAll,
  }
})
