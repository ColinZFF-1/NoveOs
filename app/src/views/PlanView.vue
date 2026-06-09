<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useChaptersStore } from '@/stores/chapters'

const projectsStore = useProjectsStore()
const chaptersStore = useChaptersStore()
const activeTab = ref<'outline' | 'characters' | 'hooks'>('outline')

onMounted(async () => {
  if (!projectsStore.projects.length) await projectsStore.fetchProjects()
  if (projectsStore.currentId) await chaptersStore.fetchChapters(projectsStore.currentId)
})
</script>

<template>
  <div class="min-h-screen pt-16">
    <!-- Hero header -->
    <div class="px-12 py-20 border-b border-gray-200">
      <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-4">Plan</div>
      <h1 class="text-5xl font-sans font-light tracking-tight text-black">构思</h1>
      <p class="mt-4 text-sm text-gray-400 font-sans max-w-md">大纲、角色与伏笔的指挥中心</p>
    </div>

    <div class="px-12 py-12">
      <!-- Tabs -->
      <div class="flex items-center gap-8 border-b border-gray-200 mb-12">
        <button
          v-for="tab in (['outline', 'characters', 'hooks'] as const)"
          :key="tab"
          @click="activeTab = tab"
          class="pb-3 text-sm transition-colors relative font-sans"
          :class="activeTab === tab ? 'text-black' : 'text-gray-400 hover:text-gray-600'"
        >
          {{ tab === 'outline' ? '大纲' : tab === 'characters' ? '角色矩阵' : '伏笔追踪' }}
          <span v-if="activeTab === tab" class="absolute bottom-0 left-0 right-0 h-px bg-black" />
        </button>
      </div>

      <!-- Outline -->
      <div v-if="activeTab === 'outline'" class="max-w-2xl space-y-0">
        <div
          v-for="ch in chaptersStore.chapters"
          :key="ch.chapter_num"
          class="flex items-baseline gap-6 py-5 border-b border-gray-100 group cursor-pointer hover:bg-gray-50 transition-colors px-4 -mx-4"
        >
          <span class="font-mono text-[11px] text-gray-400 w-8">{{ String(ch.chapter_num).padStart(2, '0') }}</span>
          <div class="flex-1 min-w-0">
            <div class="text-base text-black font-sans">{{ ch.title ?? `第${ch.chapter_num}章` }}</div>
          </div>
          <span
            class="text-[10px] font-mono px-2 py-0.5"
            :class="ch.mode === 'PASS'
              ? 'text-black bg-gray-100'
              : ch.mode === 'BLOCK'
                ? 'text-vermilion bg-vermilion-soft'
                : 'text-gray-400'"
          >
            {{ ch.mode ?? '待写' }}
          </span>
        </div>
        <div v-if="chaptersStore.chapters.length === 0" class="py-20 text-gray-400 text-sm font-sans">
          暂无章节数据
        </div>
      </div>

      <!-- Characters -->
      <div v-else-if="activeTab === 'characters'" class="max-w-2xl">
        <div class="py-32 text-center">
          <div class="text-6xl text-gray-100 font-light mb-6">⊙</div>
          <p class="text-gray-400 text-sm font-sans">角色矩阵正在加载</p>
          <p class="text-[10px] text-gray-300 mt-2 font-mono">character_matrix.md</p>
        </div>
      </div>

      <!-- Hooks -->
      <div v-else class="max-w-2xl">
        <div class="py-32 text-center">
          <div class="text-6xl text-gray-100 font-light mb-6">◷</div>
          <p class="text-gray-400 text-sm font-sans">伏笔追踪板正在加载</p>
          <p class="text-[10px] text-gray-300 mt-2 font-mono">pending_hooks.md</p>
        </div>
      </div>
    </div>
  </div>
</template>
