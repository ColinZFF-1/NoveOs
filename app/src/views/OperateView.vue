<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useChaptersStore } from '@/stores/chapters'
import { usePipelineStore } from '@/stores/pipeline'

const projectsStore = useProjectsStore()
const chaptersStore = useChaptersStore()
const pipelineStore = usePipelineStore()

const showCreateModal = ref(false)
const newProjectName = ref('')
const newProjectGenre = ref('')
const newProjectPlatform = ref('fanqie_novel')
const newProjectChapters = ref(48)
const creating = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

const dashboardStats = computed(() => {
  const chapters = chaptersStore.chapters
  const completed = chapters.filter((c) => c.mode === 'PASS').length
  const totalWords = chapters.reduce((sum, c) => sum + (c.word_count ?? 0), 0)
  const avgWords = completed > 0 ? Math.round(totalWords / completed) : 0
  const passRate = chapters.length > 0
    ? Math.round((chapters.filter((c) => c.mode === 'PASS').length / chapters.length) * 100)
    : 0
  return { completed, totalWords, avgWords, passRate }
})

async function handleStart() {
  if (!projectsStore.currentId) return
  const total = projectsStore.currentStatus?.total_chapters ?? 100
  await pipelineStore.start(projectsStore.currentId, `1-${total}`)
  startPolling()
}

async function handlePause() {
  if (!projectsStore.currentId) return
  await pipelineStore.pause(projectsStore.currentId)
}

async function handleStop() {
  if (!projectsStore.currentId) return
  await pipelineStore.stop(projectsStore.currentId)
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!projectsStore.currentId) return
    await Promise.all([
      projectsStore.fetchStatus(projectsStore.currentId),
      chaptersStore.fetchChapters(projectsStore.currentId),
      pipelineStore.fetchStatus(projectsStore.currentId),
    ])
    if (!pipelineStore.status?.is_running && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }, 5000)
}

async function handleCreateProject() {
  if (!newProjectName.value.trim()) return
  creating.value = true
  try {
    const { projectsApi } = await import('@/api/projects')
    const projectId = newProjectName.value.trim().replace(/\s+/g, '_').toLowerCase()
    await projectsApi.create({
      project_id: projectId,
      name: newProjectName.value.trim(),
      genre: newProjectGenre.value || '都市',
      platform: newProjectPlatform.value,
      total_chapters: newProjectChapters.value,
    })
    showCreateModal.value = false
    await projectsStore.fetchProjects()
    projectsStore.selectProject(projectId)
  } catch (e: unknown) {
    console.error('Failed to create project:', e)
  } finally {
    creating.value = false
  }
}

function selectProject(p: { project_id: string }) {
  projectsStore.selectProject(p.project_id)
}

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (projectsStore.currentId) {
    await Promise.all([
      projectsStore.fetchStatus(projectsStore.currentId),
      chaptersStore.fetchChapters(projectsStore.currentId),
      pipelineStore.fetchStatus(projectsStore.currentId),
    ])
    if (pipelineStore.status?.is_running) startPolling()
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="min-h-screen pt-16">
    <!-- Hero header -->
    <div class="px-12 py-20 border-b border-gray-200">
      <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-4">Operate</div>
      <h1 class="text-5xl font-sans font-light tracking-tight text-black">运营</h1>
      <p class="mt-4 text-sm text-gray-400 font-sans max-w-md">流水线控制与项目设置</p>
    </div>

    <div class="px-12 py-12 max-w-4xl">
      <!-- Project switcher -->
      <div class="flex items-center gap-3 mb-12 flex-wrap">
        <button
          v-for="p in projectsStore.projects"
          :key="p.project_id"
          @click="selectProject(p)"
          class="px-4 py-2 text-xs border transition-all font-sans"
          :class="p.project_id === projectsStore.currentId
            ? 'border-black text-black'
            : 'border-gray-200 text-gray-400 hover:border-gray-400'"
        >
          {{ p.name }}
        </button>
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 text-xs border border-dashed border-gray-300 text-gray-400 hover:border-black hover:text-black transition-all font-sans"
        >
          + 新项目
        </button>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-4 gap-px bg-gray-200 border border-gray-200 mb-16">
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Completed</div>
          <div class="text-3xl font-sans font-light text-black">{{ dashboardStats.completed }}</div>
        </div>
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Words</div>
          <div class="text-3xl font-sans font-light text-black">{{ dashboardStats.totalWords.toLocaleString() }}</div>
        </div>
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Average</div>
          <div class="text-3xl font-sans font-light text-black">{{ dashboardStats.avgWords }}</div>
        </div>
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Pass Rate</div>
          <div class="text-3xl font-sans font-light" :class="dashboardStats.passRate >= 80 ? 'text-black' : 'text-vermilion'">
            {{ dashboardStats.passRate }}%
          </div>
        </div>
      </div>

      <!-- Pipeline -->
      <div class="border border-gray-200 p-8">
        <div class="flex items-center justify-between mb-8">
          <h3 class="text-[10px] font-mono text-gray-400 tracking-widest uppercase">Pipeline</h3>
          <div class="flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full" :class="pipelineStore.status?.is_running ? 'bg-vermilion' : 'bg-gray-200'" />
            <span class="text-[10px] font-mono text-gray-400">{{ pipelineStore.status?.is_running ? 'Running' : 'Idle' }}</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <button
            v-if="pipelineStore.status?.can_start !== false"
            @click="handleStart"
            :disabled="pipelineStore.loading"
            class="px-6 py-3 text-xs bg-black text-white hover:bg-gray-900 transition-colors disabled:opacity-40 font-sans tracking-wider uppercase"
          >
            启动
          </button>
          <button
            v-if="pipelineStore.status?.is_running"
            @click="handlePause"
            :disabled="pipelineStore.loading"
            class="px-6 py-3 text-xs border border-gray-200 text-gray-600 hover:border-black hover:text-black transition-colors disabled:opacity-40 font-sans tracking-wider uppercase"
          >
            暂停
          </button>
          <button
            v-if="pipelineStore.status?.is_running || pipelineStore.status?.status === 'paused'"
            @click="handleStop"
            :disabled="pipelineStore.loading"
            class="px-6 py-3 text-xs border border-gray-200 text-vermilion hover:border-vermilion transition-colors disabled:opacity-40 font-sans tracking-wider uppercase"
          >
            停止
          </button>
          <span v-if="pipelineStore.loading" class="text-[10px] text-gray-400 font-mono">Processing…</span>
          <span v-if="pipelineStore.error" class="text-[10px] text-vermilion font-mono">{{ pipelineStore.error }}</span>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 bg-white/80 backdrop-blur-sm z-[100] flex items-center justify-center" @click.self="showCreateModal = false">
        <div class="bg-white border border-gray-200 w-[480px] p-10">
          <h2 class="text-xl font-sans font-light text-black mb-8">新建项目</h2>
          <div class="space-y-5">
            <div>
              <label class="block text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-2">Name</label>
              <input v-model="newProjectName" class="w-full border-b border-gray-200 pb-2 text-sm text-black outline-none focus:border-black transition-colors placeholder:text-gray-300 font-sans" placeholder="项目名称" />
            </div>
            <div class="grid grid-cols-2 gap-6">
              <div>
                <label class="block text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-2">Genre</label>
                <input v-model="newProjectGenre" class="w-full border-b border-gray-200 pb-2 text-sm text-black outline-none focus:border-black transition-colors placeholder:text-gray-300 font-sans" placeholder="分类" />
              </div>
              <div>
                <label class="block text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-2">Platform</label>
                <select v-model="newProjectPlatform" class="w-full border-b border-gray-200 pb-2 text-sm text-black outline-none focus:border-black transition-colors bg-transparent font-sans">
                  <option value="fanqie_novel">番茄小说</option>
                  <option value="qimao">七猫</option>
                  <option value="other">其他</option>
                </select>
              </div>
            </div>
            <div>
              <label class="block text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-2">Chapters</label>
              <input v-model.number="newProjectChapters" type="number" min="1" max="500" class="w-full border-b border-gray-200 pb-2 text-sm text-black outline-none focus:border-black transition-colors font-sans" />
            </div>
          </div>
          <div class="flex justify-end gap-4 mt-10">
            <button @click="showCreateModal = false" class="text-xs text-gray-400 hover:text-black transition-colors font-sans tracking-wider uppercase">取消</button>
            <button @click="handleCreateProject" :disabled="creating || !newProjectName.trim()" class="text-xs bg-black text-white px-5 py-2 hover:bg-gray-900 transition-colors disabled:opacity-40 font-sans tracking-wider uppercase">
              {{ creating ? '创建中…' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
