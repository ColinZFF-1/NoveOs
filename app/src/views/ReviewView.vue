<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useChaptersStore } from '@/stores/chapters'

const projectsStore = useProjectsStore()
const chaptersStore = useChaptersStore()

const qualityDimensions = [
  { name: '画面感', score: 7.8 },
  { name: '节奏', score: 6.5 },
  { name: '人设一致', score: 8.2 },
  { name: '对话自然', score: 7.0 },
  { name: '悬念', score: 6.8 },
  { name: '情感张力', score: 7.5 },
  { name: '去 AI 味', score: 5.5 },
  { name: '标点节奏', score: 7.2 },
]

const avgScore = computed(() => {
  const sum = qualityDimensions.reduce((acc, d) => acc + d.score, 0)
  return (sum / qualityDimensions.length).toFixed(1)
})

onMounted(async () => {
  if (!projectsStore.projects.length) await projectsStore.fetchProjects()
  if (projectsStore.currentId) await chaptersStore.fetchChapters(projectsStore.currentId)
})
</script>

<template>
  <div class="min-h-screen pt-16">
    <!-- Hero header -->
    <div class="px-12 py-20 border-b border-gray-200">
      <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-4">Review</div>
      <h1 class="text-5xl font-sans font-light tracking-tight text-black">审阅</h1>
      <p class="mt-4 text-sm text-gray-400 font-sans max-w-md">质量雷达与 AI 痕迹检测</p>
    </div>

    <div class="px-12 py-12">
      <!-- Score cards -->
      <div class="grid grid-cols-4 gap-px bg-gray-200 border border-gray-200 mb-16">
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Score</div>
          <div class="text-4xl font-sans font-light text-black">{{ avgScore }}</div>
        </div>
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">AI-Free</div>
          <div class="text-4xl font-sans font-light" :class="Number(avgScore) >= 7 ? 'text-black' : 'text-vermilion'">
            {{ qualityDimensions.find(d => d.name === '去 AI 味')?.score ?? '-' }}
          </div>
        </div>
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Done</div>
          <div class="text-4xl font-sans font-light text-black">
            {{ chaptersStore.chapters.filter(c => c.mode === 'PASS').length }}
          </div>
        </div>
        <div class="bg-white p-8">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-3">Words</div>
          <div class="text-4xl font-sans font-light text-black">
            {{ chaptersStore.chapters.reduce((s, c) => s + (c.word_count ?? 0), 0).toLocaleString() }}
          </div>
        </div>
      </div>

      <!-- Dimension bars -->
      <div class="max-w-2xl mb-16">
        <h3 class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-8">Dimensions</h3>
        <div class="space-y-5">
          <div v-for="d in qualityDimensions" :key="d.name" class="flex items-center gap-6">
            <span class="w-20 text-xs text-gray-600 text-right font-sans">{{ d.name }}</span>
            <div class="flex-1 h-px bg-gray-200 relative">
              <div
                class="absolute top-0 left-0 h-full bg-black transition-all duration-1000"
                :style="{ width: `${(d.score / 10) * 100}%` }"
              />
            </div>
            <span class="w-8 text-xs font-mono text-gray-400">{{ d.score }}</span>
          </div>
        </div>
      </div>

      <!-- Chapter list -->
      <div class="max-w-2xl">
        <h3 class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-8">Chapters</h3>
        <div class="border-t border-gray-200">
          <div
            v-for="ch in chaptersStore.chapters"
            :key="ch.chapter_num"
            class="flex items-baseline gap-6 py-4 border-b border-gray-100"
          >
            <span class="font-mono text-[11px] text-gray-400 w-8">{{ String(ch.chapter_num).padStart(2, '0') }}</span>
            <span class="flex-1 text-sm text-black font-sans">{{ ch.title ?? '—' }}</span>
            <span class="text-xs font-mono text-gray-400 w-16 text-right">{{ ch.word_count?.toLocaleString() ?? '—' }}</span>
            <span
              class="text-[10px] font-mono w-12 text-right"
              :class="ch.mode === 'PASS' ? 'text-black' : ch.mode === 'BLOCK' ? 'text-vermilion' : 'text-gray-400'"
            >
              {{ ch.mode ?? '—' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
