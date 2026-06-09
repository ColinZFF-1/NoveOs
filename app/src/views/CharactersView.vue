<script setup lang="ts">
import { computed, watch } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useCharactersStore } from '@/stores/characters'

const projectsStore = useProjectsStore()
const charactersStore = useCharactersStore()

const selected = computed(() => charactersStore.selectedCharacter)
const timeline = computed(() => {
  if (!selected.value) return []
  return charactersStore.characters.filter(c => c.name === selected.value!.name).sort((a,b) => a.chapter - b.chapter)
})

watch(() => projectsStore.currentId, (id) => {
  if (id) { charactersStore.fetchCharacters(id); charactersStore.fetchEmotions(id) }
}, { immediate: true })
</script>

<template>
  <div class="max-w-[900px]">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <!-- 列表 -->
      <div class="lg:col-span-1 s1">
        <div class="fine">
          <button
            v-for="c in charactersStore.uniqueCharacters"
            :key="c.name"
            @click="charactersStore.selectCharacter(c.name)"
            class="w-full text-left row"
            :class="selected?.name === c.name ? 'fine-active' : ''"
          >
            <div>
              <div style="font-size: 13px;">{{ c.name }}</div>
              <div style="font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px;">{{ c.emotional_state || '—' }}</div>
            </div>
          </button>
          <div v-if="charactersStore.uniqueCharacters.length === 0" class="py-8 text-center" style="font-size: 12px; color: var(--color-text-tertiary);">
            {{ charactersStore.loading ? '加载中…' : '暂无人物' }}
          </div>
        </div>
      </div>

      <!-- 详情 -->
      <div class="lg:col-span-3 space-y-4 s2">
        <div v-if="selected" class="fine p-5">
          <div class="flex items-center justify-between mb-5">
            <span style="font-size: 20px; font-weight: 300; letter-spacing: -0.02em;">{{ selected.name }}</span>
            <span class="caption">第 {{ selected.chapter }} 章</span>
          </div>
          <div class="grid grid-cols-2 gap-x-6 gap-y-4" style="font-size: 12px;">
            <div><span style="color: var(--color-text-tertiary);">位置</span><div class="mt-1">{{ selected.location || '—' }}</div></div>
            <div><span style="color: var(--color-text-tertiary);">情绪</span><div class="mt-1">{{ selected.emotional_state || '—' }}</div></div>
            <div><span style="color: var(--color-text-tertiary);">已知秘密</span><div class="mt-1">{{ selected.known_secrets || '—' }}</div></div>
            <div><span style="color: var(--color-text-tertiary);">对话指纹</span><div class="mt-1">{{ selected.dialog_fingerprint || '—' }}</div></div>
          </div>
        </div>

        <div v-if="timeline.length > 1" class="fine p-5">
          <div class="caption mb-4">时间线</div>
          <div class="relative pl-3">
            <div class="absolute left-[5px] top-1 bottom-1 w-[1px]" style="background: var(--color-border);"></div>
            <div class="space-y-4">
              <div v-for="t in timeline" :key="t.chapter" class="flex items-start gap-3">
                <div class="w-2.5 h-2.5 rounded-full flex-shrink-0 z-10 mt-0.5" style="background: var(--color-bg); border: 1px solid var(--color-border-hover);"></div>
                <div>
                  <div style="font-size: 12px;">第 {{ t.chapter }} 章</div>
                  <div style="font-size: 11px; color: var(--color-text-tertiary);">{{ t.location || '—' }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="fine p-5">
          <div class="caption mb-4">情感坐标</div>
          <div v-if="charactersStore.emotions.length > 0" class="flex flex-wrap gap-2">
            <div v-for="e in charactersStore.emotions" :key="e.chapter" class="px-3 py-2 rounded-[var(--radius-sm)]" style="border: 1px solid var(--color-border);">
              <div style="font-size: 10px; color: var(--color-text-tertiary);">第{{ e.chapter }}章</div>
              <div style="font-size: 11px; font-weight: 500; margin-top: 1px;" :class="e.mode==='PASS'?'text-[var(--color-green)]':e.mode==='WARN'?'text-[var(--color-orange)]':'text-[var(--color-red)]'">{{ e.mode }}</div>
            </div>
          </div>
          <div v-else class="py-4 text-center" style="font-size: 12px; color: var(--color-text-tertiary);">{{ charactersStore.loading ? '加载中…' : '暂无数据' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
