<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

const navItems = [
  { path: '/dashboard', label: '总览' },
  { path: '/pipeline', label: '流水线' },
  { path: '/chapters', label: '章节' },
  { path: '/characters', label: '人物' },
  { path: '/quality', label: '质量' },
  { path: '/outline', label: '大纲' },
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<template>
  <div class="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex">
    <!-- 纤细侧边栏 -->
    <aside class="w-[64px] md:w-52 flex flex-col fixed h-full z-50" style="border-right: 1px solid var(--color-border);">
      <!-- Logo -->
      <div class="h-14 flex items-center px-4 md:px-5" style="border-bottom: 1px solid var(--color-border);">
        <div class="w-6 h-6 rounded-[4px] flex items-center justify-center" style="border: 1px solid var(--color-border-hover);">
          <span class="text-[10px] font-semibold tracking-widest" style="color: var(--color-text-secondary);">N</span>
        </div>
        <span class="hidden md:block ml-3 text-[13px] font-medium tracking-tight" style="color: var(--color-text);">Novel-OS</span>
      </div>

      <!-- Project -->
      <div class="hidden md:block px-4 py-3" style="border-bottom: 1px solid var(--color-border);">
        <select
          v-if="projectsStore.projects.length > 0"
          v-model="projectsStore.currentId"
          @change="(e) => projectsStore.selectProject((e.target as HTMLSelectElement).value)"
          class="w-full bg-transparent text-[11px] cursor-pointer focus:outline-none"
          style="color: var(--color-text-tertiary); appearance: none;"
        >
          <option v-for="p in projectsStore.projects" :key="p.project_id" :value="p.project_id" style="background: #0a0a0c;">
            {{ p.name }}
          </option>
        </select>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-2 px-2 space-y-0.5">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="router.push(item.path)"
          :class="[
            'w-full flex items-center gap-3 px-3 py-2 rounded-[var(--radius-md)] text-[12px] transition-all',
            isActive(item.path)
              ? 'fine-active text-[var(--color-accent)] font-medium'
              : 'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]',
          ]"
        >
          <span class="w-1 h-1 rounded-full flex-shrink-0"
            :class="isActive(item.path) ? 'bg-[var(--color-accent)]' : 'bg-transparent'"
          ></span>
          <span class="hidden md:block">{{ item.label }}</span>
        </button>
      </nav>

      <!-- Status -->
      <div class="px-4 py-3 flex items-center justify-center md:justify-start gap-2" style="border-top: 1px solid var(--color-border);">
        <span
          class="w-1.5 h-1.5 rounded-full flex-shrink-0"
          :class="
            projectsStore.currentStatus?.status === 'writing' ? 'bg-[var(--color-orange)]' :
            projectsStore.currentStatus?.status === 'idle' ? 'bg-[var(--color-green)]' :
            'bg-[var(--color-text-tertiary)]'
          "
        ></span>
        <span class="hidden md:block text-[10px]" style="color: var(--color-text-tertiary);">
          {{ projectsStore.currentStatus?.status === 'writing' ? '写作中' : projectsStore.currentStatus?.status === 'idle' ? '空闲' : '暂停' }}
        </span>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 ml-[64px] md:ml-52 min-h-screen p-5 md:p-8">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.page-enter-active { animation: fadeUp 0.35s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
.page-leave-active { animation: fadeUp 0.2s cubic-bezier(0.22, 1, 0.36, 1) reverse forwards; }
</style>
