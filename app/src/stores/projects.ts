import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi } from '@/api/projects'
import type { Project, ProjectStatus } from '@/types'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const currentId = ref<string | null>(null)
  const currentStatus = ref<ProjectStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const currentProject = computed(() =>
    projects.value.find((p) => p.project_id === currentId.value) ?? null,
  )

  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      projects.value = await projectsApi.list()
      // Auto-select first project if none selected
      if (!currentId.value && projects.value.length > 0) {
        currentId.value = projects.value[0].project_id
      }
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load projects'
    } finally {
      loading.value = false
    }
  }

  async function fetchStatus(projectId?: string) {
    const id = projectId ?? currentId.value
    if (!id) return
    loading.value = true
    error.value = null
    try {
      currentStatus.value = await projectsApi.get(id)
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load project status'
    } finally {
      loading.value = false
    }
  }

  function selectProject(id: string) {
    currentId.value = id
    currentStatus.value = null
    fetchStatus(id)
  }

  async function refresh() {
    await Promise.all([fetchProjects(), currentId.value ? fetchStatus(currentId.value) : Promise.resolve()])
  }

  return {
    projects,
    currentId,
    currentStatus,
    currentProject,
    loading,
    error,
    fetchProjects,
    fetchStatus,
    selectProject,
    refresh,
  }
})
