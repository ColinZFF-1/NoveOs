<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useChaptersStore } from '@/stores/chapters'
import { chaptersApi } from '@/api/chapters'
import type { Chapter } from '@/types'

const projectsStore = useProjectsStore()
const chaptersStore = useChaptersStore()

const selectedChapter = ref<Chapter | null>(null)
const content = ref('')
const loading = ref(false)
const aiLoading = ref(false)

const chapterList = computed(() => chaptersStore.chapters)
const currentWords = computed(() => content.value.replace(/\s/g, '').length)

async function selectChapter(ch: Chapter) {
  if (selectedChapter.value?.chapter_num === ch.chapter_num) return
  selectedChapter.value = ch
  content.value = ''
  if (!projectsStore.currentId) return
  loading.value = true
  try {
    const data = await chaptersApi.content(projectsStore.currentId, ch.chapter_num)
    content.value = data.content
  } catch {
    content.value = ''
  } finally {
    loading.value = false
  }
}

async function aiContinue() {
  if (!selectedChapter.value) return
  aiLoading.value = true
  await new Promise((r) => setTimeout(r, 1200))
  aiLoading.value = false
  content.value += '\n\n主人公深吸一口气，推开了那扇斑驳的木门。门轴发出刺耳的吱呀声，仿佛在警告他不要踏入这个被遗忘的世界。'
}

onMounted(async () => {
  if (!projectsStore.projects.length) await projectsStore.fetchProjects()
  if (projectsStore.currentId) {
    await chaptersStore.fetchChapters(projectsStore.currentId)
    if (chapterList.value.length > 0) await selectChapter(chapterList.value[0])
  }
})

watch(() => projectsStore.currentId, async (id) => {
  if (id) {
    await chaptersStore.fetchChapters(id)
    if (chapterList.value.length > 0) await selectChapter(chapterList.value[0])
  }
})
</script>

<template>
  <div class="min-h-screen pt-16 flex">
    <!-- Left: Chapter index -->
    <aside class="w-56 border-r border-gray-200 shrink-0">
      <div class="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto py-8 px-8">
        <div class="text-[10px] font-mono text-gray-400 mb-6 tracking-widest uppercase">Chapters</div>
        <div class="space-y-1">
          <button
            v-for="ch in chapterList"
            :key="ch.chapter_num"
            @click="selectChapter(ch)"
            class="w-full text-left px-3 py-2 text-[12px] transition-colors duration-200 flex items-baseline gap-3 group"
            :class="selectedChapter?.chapter_num === ch.chapter_num
              ? 'text-black bg-gray-50'
              : 'text-gray-400 hover:text-black'"
          >
            <span class="font-mono text-[10px] w-4">{{ String(ch.chapter_num).padStart(2, '0') }}</span>
            <span class="truncate">{{ ch.title ?? `第${ch.chapter_num}章` }}</span>
          </button>
        </div>
      </div>
    </aside>

    <!-- Center: Editor -->
    <section class="flex-1 min-w-0">
      <div class="max-w-3xl mx-auto px-16 py-20">
        <!-- Chapter header -->
        <header v-if="selectedChapter" class="mb-16">
          <div class="text-[10px] font-mono text-gray-400 tracking-widest uppercase mb-4">
            Chapter {{ String(selectedChapter.chapter_num).padStart(2, '0') }}
          </div>
          <h1 class="text-4xl font-sans font-light tracking-tight text-black leading-tight">
            {{ selectedChapter.title ?? `第${selectedChapter.chapter_num}章` }}
          </h1>
          <div class="mt-6 h-px bg-gray-200 w-16" />
        </header>

        <!-- Editor -->
        <div class="relative">
          <div v-if="loading" class="py-20">
            <span class="text-sm text-gray-400 font-sans">加载中…</span>
          </div>
          <textarea
            v-else
            v-model="content"
            class="w-full min-h-[60vh] resize-none outline-none text-lg leading-relaxed text-black bg-transparent placeholder:text-gray-300 font-sans"
            placeholder="开始写作"
            spellcheck="false"
          />
        </div>

        <!-- Footer -->
        <div class="mt-16 pt-8 border-t border-gray-200 flex items-center justify-between">
          <span class="text-[10px] font-mono text-gray-400">{{ currentWords.toLocaleString() }} 字</span>
          <div class="flex items-center gap-6">
            <button
              @click="aiContinue"
              :disabled="aiLoading"
              class="text-[11px] font-mono text-gray-400 hover:text-vermilion transition-colors disabled:opacity-40 tracking-wider uppercase"
            >
              {{ aiLoading ? 'Generating…' : 'AI 续写' }}
            </button>
            <button class="text-[11px] font-mono text-gray-400 hover:text-black transition-colors tracking-wider uppercase">
              保存
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Right: Minimal panel -->
    <aside class="w-48 border-l border-gray-200 shrink-0">
      <div class="sticky top-16 h-[calc(100vh-4rem)] py-8 px-6">
        <div class="text-[10px] font-mono text-gray-400 mb-6 tracking-widest uppercase">Status</div>
        <div class="space-y-4">
          <div>
            <div class="text-[10px] font-mono text-gray-400">Mode</div>
            <div class="text-[12px] text-black mt-1">{{ selectedChapter?.mode ?? '—' }}</div>
          </div>
          <div>
            <div class="text-[10px] font-mono text-gray-400">Words</div>
            <div class="text-[12px] text-black mt-1">{{ currentWords.toLocaleString() }}</div>
          </div>
          <div v-if="projectsStore.currentStatus?.reader_pull_score !== null">
            <div class="text-[10px] font-mono text-gray-400">Score</div>
            <div class="text-[12px] text-black mt-1">{{ projectsStore.currentStatus?.reader_pull_score?.toFixed(1) ?? '—' }}</div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>
