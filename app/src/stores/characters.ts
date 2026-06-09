import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { charactersApi } from '@/api/characters'
import type { CharacterState, EmotionCoordinate } from '@/types'

export const useCharactersStore = defineStore('characters', () => {
  const characters = ref<CharacterState[]>([])
  const emotions = ref<EmotionCoordinate[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const uniqueCharacters = computed(() => {
    const map = new Map<string, CharacterState>()
    for (const c of characters.value) {
      // Keep the latest chapter's state
      const existing = map.get(c.name)
      if (!existing || c.chapter > existing.chapter) {
        map.set(c.name, c)
      }
    }
    return Array.from(map.values())
  })

  const selectedCharacter = ref<CharacterState | null>(null)

  async function fetchCharacters(projectId: string) {
    loading.value = true
    error.value = null
    try {
      characters.value = await charactersApi.list(projectId)
      if (uniqueCharacters.value.length > 0 && !selectedCharacter.value) {
        selectedCharacter.value = uniqueCharacters.value[0]
      }
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load characters'
    } finally {
      loading.value = false
    }
  }

  async function fetchEmotions(projectId: string) {
    loading.value = true
    error.value = null
    try {
      emotions.value = await charactersApi.emotions(projectId)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load emotions'
    } finally {
      loading.value = false
    }
  }

  function selectCharacter(name: string) {
    const found = uniqueCharacters.value.find((c) => c.name === name)
    if (found) selectedCharacter.value = found
  }

  return {
    characters,
    emotions,
    uniqueCharacters,
    selectedCharacter,
    loading,
    error,
    fetchCharacters,
    fetchEmotions,
    selectCharacter,
  }
})
