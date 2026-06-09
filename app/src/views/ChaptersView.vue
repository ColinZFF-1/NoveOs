<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useChaptersStore } from '@/stores/chapters'
import client, { unwrap } from '@/api/client'
import type { Chapter } from '@/types'

const projectsStore = useProjectsStore()
const chaptersStore = useChaptersStore()

const selectedChapter = ref<Chapter | null>(null)
const chapterContent = ref('')
const loadingContent = ref(false)
const searchQuery = ref('')

const filteredChapters = computed(() => {
  let list = chaptersStore.chapters
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((c) => (c.title?.toLowerCase().includes(q) ?? false) || String(c.chapter_num).includes(q))
  }
  return list
})

async function loadContent(ch: Chapter) {
  if (!projectsStore.currentId) return
  selectedChapter.value = ch
  loadingContent.value = true
  chapterContent.value = ''
  try {
    const res = await client.get(`/projects/${encodeURIComponent(projectsStore.currentId)}/chapters/${ch.chapter_num}/content`)
    chapterContent.value = unwrap<{ content: string }>(res).content
  } catch {
    chapterContent.value = '无法加载'
  } finally {
    loadingContent.value = false
  }
}

function closeContent() {
  selectedChapter.value = null
  chapterContent.value = ''
}

function statusColor(mode: string | null) {
  switch (mode) {
    case 'PASS': return 'color: var(--color-green);'
    case 'WARN': return 'color: var(--color-orange);'
    case 'BLOCK': return 'color: var(--color-red);'
    default: return 'color: var(--color-text-tertiary);'
  }
}

watch(() => projectsStore.currentId, (id) => { if (id) chaptersStore.fetchChapters(id) }, { immediate: true })
</script>

<template>
  <div class="max-w-[900px]">
    <!-- 搜索 -->
    <section class="mb-8 s1">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索章节..."
        class="w-full bg-transparent text-[14px] focus:outline-none"
        style="color: var(--color-text); border-bottom: 1px solid var(--color-border); padding: 8px 0;"
      />
    </section>

    <!-- 列表 -->
    <section class="fine s2">
      <div
        v-for="ch in filteredChapters"
        :key="ch.chapter_num"
        class="row"
        @click="loadContent(ch)"
      >
        <div class="flex items-center gap-4">
          <span style="font-size: 12px; color: var(--color-text-tertiary); font-family: var(--font-display); min-width: 24px;">{{ String(ch.chapter_num).padStart(2, '0') }}</span>
          <span style="font-size: 13px;">{{ ch.title ?? '未命名' }}</span>
        </div>
        <div class="flex items-center gap-5">
          <span style="font-size: 12px; color: var(--color-text-tertiary);">{{ ch.word_count?.toLocaleString() ?? '—' }} 字</span>
          <span style="font-size: 12px; font-weight: 500;" :style="statusColor(ch.mode)">{{ ch.mode ?? '草稿' }}</span>
        </div>
      </div>

      <div v-if="filteredChapters.length === 0" class="py-10 text-center" style="font-size: 13px; color: var(--color-text-tertiary);">
        {{ chaptersStore.loading ? '加载中…' : '暂无章节' }}
      </div>
    </section>

    <!-- 阅读弹窗 -->
    <Transition name="sheet">
      <div v-if="selectedChapter" class="fixed inset-0 z-50 flex items-end md:items-center justify-center">
        <div class="absolute inset-0" style="background: rgba(0,0,0,0.6); backdrop-filter: blur(8px);" @click="closeContent"></div>
        <div class="relative w-full md:w-[640px] max-h-[80vh] flex flex-col" style="background: var(--color-bg-raised); border-top: 1px solid var(--color-border); border-radius: var(--radius-xl) var(--radius-xl) 0 0;">
          <div class="flex items-center justify-between px-6 py-4" style="border-bottom: 1px solid var(--color-border);">
            <div>
              <div style="font-size: 15px; font-weight: 500;">第 {{ selectedChapter.chapter_num }} 章</div>
              <div style="font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px;">{{ selectedChapter.word_count?.toLocaleString() ?? '—' }} 字</div>
            </div>
            <button @click="closeContent" style="font-size: 18px; color: var(--color-text-tertiary); padding: 4px;">×</button>
          </div>
          <div class="flex-1 overflow-y-auto p-6">
            <div v-if="loadingContent" style="text-align: center; color: var(--color-text-tertiary); font-size: 13px; padding: 40px 0;">加载中…</div>
            <div v-else style="font-size: 15px; line-height: 1.8; white-space: pre-wrap; color: var(--color-text);">{{ chapterContent }}</div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.sheet-enter-active, .sheet-leave-active { transition: opacity 0.25s ease; }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
</style>
