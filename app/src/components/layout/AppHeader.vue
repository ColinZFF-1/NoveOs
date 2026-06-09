<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { usePipelineStore } from '@/stores/pipeline'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const pipelineStore = usePipelineStore()

const modes = [
  { key: 'plan', label: '构思', path: '/plan' },
  { key: 'write', label: '执笔', path: '/write' },
  { key: 'review', label: '审阅', path: '/review' },
  { key: 'operate', label: '运营', path: '/operate' },
] as const

const currentMode = computed(() =>
  modes.find((m) => route.path.startsWith(m.path))?.key ?? 'write'
)

function switchMode(path: string) {
  router.push(path)
}
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white">
    <div class="flex items-center justify-between px-12 h-16">
      <!-- Left: Logo -->
      <div class="w-40">
        <span class="text-[11px] font-mono tracking-widest text-gray-400 uppercase">Novel-OS</span>
      </div>

      <!-- Center: Nav -->
      <nav class="flex items-center gap-0">
        <button
          v-for="mode in modes"
          :key="mode.key"
          @click="switchMode(mode.path)"
          class="px-6 py-2 text-[13px] tracking-wide transition-colors duration-300 font-sans"
          :class="currentMode === mode.key
            ? 'text-black'
            : 'text-gray-400 hover:text-black'"
        >
          {{ mode.label }}
        </button>
      </nav>

      <!-- Right: Status dot -->
      <div class="w-40 flex justify-end">
        <div class="flex items-center gap-2">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="pipelineStore.status?.is_running ? 'bg-vermilion' : 'bg-gray-200'"
          />
          <span class="text-[10px] font-mono text-gray-400 tracking-wider">
            {{ projectsStore.currentProject?.name?.slice(0, 8) ?? '墨斋' }}
          </span>
        </div>
      </div>
    </div>
    <!-- Hairline border -->
    <div class="h-px bg-gray-200" />
  </header>
</template>
