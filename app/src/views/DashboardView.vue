<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useChaptersStore } from '@/stores/chapters'

const projectsStore = useProjectsStore()
const chaptersStore = useChaptersStore()

const stats = computed(() => {
  const p = projectsStore.currentStatus
  if (!p) return null
  const progress = p.total_chapters > 0 ? Math.round((p.completed_chapters / p.total_chapters) * 100) : 0
  return {
    progress,
    words: p.total_words?.toLocaleString() ?? '0',
    completed: p.completed_chapters ?? 0,
    total: p.total_chapters ?? 0,
    score: p.reader_pull_score?.toFixed(1) ?? '—',
  }
})

const recentChapters = computed(() => chaptersStore.chapters.slice().reverse().slice(0, 5))

function statusColor(mode: string | null) {
  switch (mode) {
    case 'PASS': return 'color: var(--color-green);'
    case 'WARN': return 'color: var(--color-orange);'
    case 'BLOCK': return 'color: var(--color-red);'
    default: return 'color: var(--color-text-tertiary);'
  }
}

onMounted(() => {
  if (projectsStore.currentId) chaptersStore.fetchChapters(projectsStore.currentId)
})
</script>

<template>
  <div class="max-w-[900px]">
    <!-- 头部 -->
    <header class="mb-10 s1">
      <h1 class="display">{{ stats?.progress ?? 0 }}<span style="font-size: 20px; color: var(--color-text-tertiary); margin-left: 4px;">%</span></h1>
      <p class="mt-2" style="font-size: 14px; color: var(--color-text-secondary);">
        {{ projectsStore.currentProject?.name }} · {{ stats?.completed }}/{{ stats?.total }} 章
      </p>
    </header>

    <!-- 数字行 -->
    <section v-if="stats" class="flex gap-8 mb-12 s2">
      <div>
        <div class="caption mb-1">总字数</div>
        <div style="font-size: 28px; font-weight: 300; letter-spacing: -0.02em; color: var(--color-text);">{{ stats.words }}</div>
      </div>
      <div>
        <div class="caption mb-1">读者拉力</div>
        <div style="font-size: 28px; font-weight: 300; letter-spacing: -0.02em;" :style="Number(stats.score) >= 7 ? 'color: var(--color-green);' : 'color: var(--color-orange);'">{{ stats.score }}</div>
      </div>
    </section>

    <!-- 进度条 -->
    <section v-if="stats" class="mb-12 s3">
      <div class="h-[1px] w-full" style="background: var(--color-border);">
        <div class="h-full transition-all duration-1000" style="background: var(--color-accent); width: var(--w);" :style="{ '--w': stats.progress + '%' }"></div>
      </div>
    </section>

    <!-- 最近章节 -->
    <section class="s4">
      <div class="flex items-center justify-between mb-4">
        <span class="caption">最近章节</span>
        <router-link to="/chapters" style="font-size: 11px; color: var(--color-text-tertiary);" class="hover:text-[var(--color-accent)] transition-colors">全部</router-link>
      </div>

      <div class="fine">
        <div
          v-for="ch in recentChapters"
          :key="ch.chapter_num"
          class="row"
          @click="$router.push('/chapters')"
        >
          <div class="flex items-center gap-4">
            <span style="font-size: 12px; color: var(--color-text-tertiary); font-family: var(--font-display); min-width: 24px;">{{ String(ch.chapter_num).padStart(2, '0') }}</span>
            <span style="font-size: 13px; font-weight: 400;">{{ ch.title ?? '未命名' }}</span>
          </div>
          <div class="flex items-center gap-4">
            <span style="font-size: 12px; color: var(--color-text-tertiary);">{{ ch.word_count?.toLocaleString() ?? '—' }} 字</span>
            <span style="font-size: 12px; font-weight: 500;" :style="statusColor(ch.mode)">{{ ch.mode ?? '草稿' }}</span>
          </div>
        </div>

        <div v-if="recentChapters.length === 0" class="py-8 text-center" style="font-size: 13px; color: var(--color-text-tertiary);">
          暂无章节
        </div>
      </div>
    </section>
  </div>
</template>
