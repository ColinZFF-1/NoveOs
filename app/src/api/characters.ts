import client, { unwrap } from './client'
import type { CharacterState, EmotionCoordinate } from '@/types'

export const charactersApi = {
  /** List all characters */
  async list(projectId: string): Promise<CharacterState[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/characters`)
    return unwrap<CharacterState[]>(res)
  },

  /** Get emotion history */
  async emotions(projectId: string): Promise<EmotionCoordinate[]> {
    const res = await client.get(`/projects/${encodeURIComponent(projectId)}/emotions`)
    const data = unwrap<{ coordinates: EmotionCoordinate[] }>(res)
    return data.coordinates
  },
}
