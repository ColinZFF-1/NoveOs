<script setup lang="ts">
import { computed, watch } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useQualityStore } from '@/stores/quality'

const projectsStore = useProjectsStore()
const qualityStore = useQualityStore()

const maxWordCount = computed(() => qualityStore.metrics.length ? Math.max(...qualityStore.metrics.map(m => m.word_count || 0)) : 1)
const maxTaDensity = computed(() => qualityStore.metrics.length ? Math.max(...qualityStore.metrics.map(m => m.ta_density || 0), 10) : 1)

function guardBorder(level: string) {
  switch (level) {
    case 'PASS': return 'border-color: rgba(129,201,149,0.2); background: rgba(129,201,149,0.04);'
    case 'WARN': return 'border-color: rgba(249,171,0,0.2); background: rgba(249,171,0,0.04);'
    case 'BLOCKING': return 'border-color: rgba(242,139,130,0.2); background: rgba(242,139,130,0.04);'
    default: return ''
  }
}

function guardColor(level: string) {
  switch (level) {
    case 'PASS': return 'color: var(--color-green);'
    case 'WARN': return 'color: var(--color-orange);'
    case 'BLOCKING': return 'color: var(--color-red);'
    default: return 'color: var(--color-text-tertiary);'
  }
}

watch(() => projectsStore.currentId, (id) => {
  if (id) { qualityStore.fetchMetrics(id); qualityStore.fetchGuards(id) }
}, { immediate: true })
</script>

<template>
  <div class="max-w-[900px]">
    <!-- 指标 -->
    <section v-if="qualityStore.metrics.length > 0" class="flex gap-10 mb-12 s1">
      <div>
        <div class="caption mb-1">平均字数</div>
        <div style="font-size: 28px; font-weight: 300; letter-spacing: -0.02em;">{{ qualityStore.avgWordCount }}</div>
      </div>
      <div>
        <div class="caption mb-1">他字密度</div>
        <div style="font-size: 28px; font-weight: 300; letter-spacing: -0.02em;" :style="Number(qualityStore.avgTaDensity) > 5 ? 'color: var(--color-red);' : 'color: var(--color-green);'">{{ qualityStore.avgTaDensity }}%</div>
      </div>
      <div>
        <div class="caption mb-1">IWR</div>
        <div style="font-size: 28px; font-weight: 300; letter-spacing: -0.02em; color: var(--color-accent);">{{ qualityStore.avgIwrScore }}</div>
      </div>
      <div>
        <div class="caption mb-1">平台适配</div>
        <div style="font-size: 28px; font-weight: 300; letter-spacing: -0.02em;">{{ qualityStore.metrics[qualityStore.metrics.length-1]?.platform_grade ?? '—' }}</div>
      </div>
    </section>

    <!-- 图表 -->
    <section v-if="qualityStore.metrics.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-10 s2">
      <div class="fine p-5">
        <div class="caption mb-5">字数趋势</div>
        <div class="flex items-end gap-[2px] h-28">
          <div v-for="m in qualityStore.metrics" :key="m.chapter" class="flex-1 flex flex-col items-center gap-1 group">
            <div class="w-full rounded-t-[2px] transition-all relative" style="background: var(--color-accent-dim); min-height: 2px;" :style="{ height: ((m.word_count||0)/maxWordCount*100)+'%' }">
              <div class="absolute -top-5 left-1/2 -translate-x-1/2 text-[9px] opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap" style="color: var(--color-text-tertiary);">{{ m.word_count }}</div>
            </div>
            <span style="font-size: 8px; color: var(--color-text-tertiary);">{{ m.chapter }}</span>
          </div>
        </div>
      </div>
      <div class="fine p-5">
        <div class="caption mb-5">他字密度</div>
        <div class="flex items-end gap-[2px] h-28">
          <div v-for="m in qualityStore.metrics" :key="m.chapter" class="flex-1 flex flex-col items-center gap-1 group">
            <div class="w-full rounded-t-[2px] transition-all relative" :class="(m.ta_density||0)>5?'bg-[var(--color-red-dim)]':'bg-[var(--color-green-dim)]'" style="min-height: 2px;" :style="{ height: Math.max(((m.ta_density||0)/maxTaDensity*100),2)+'%' }">
              <div class="absolute -top-5 left-1/2 -translate-x-1/2 text-[9px] opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap" style="color: var(--color-text-tertiary);">{{ (m.ta_density||0).toFixed(1) }}%</div>
            </div>
            <span style="font-size: 8px; color: var(--color-text-tertiary);">{{ m.chapter }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 指标列表 -->
    <section v-if="qualityStore.metrics.length > 0" class="mb-10 s3">
      <div class="caption mb-3">章节指标</div>
      <div class="fine">
        <div
          v-for="m in qualityStore.metrics"
          :key="m.chapter"
          class="row"
        >
          <div class="flex items-center gap-6">
            <span style="font-size: 12px; color: var(--color-text-tertiary); font-family: var(--font-display); min-width: 24px;">{{ String(m.chapter).padStart(2,'0') }}</span>
            <span style="font-size: 12px; color: var(--color-text-secondary);">{{ m.word_count }} 字</span>
            <span style="font-size: 12px; color: var(--color-text-tertiary);">句长 {{ m.sentence_length?.toFixed(1) ?? '—' }}</span>
          </div>
          <div class="flex items-center gap-5">
            <span style="font-size: 12px;" :class="(m.ta_density||0)>5?'text-[var(--color-red)]':'text-[var(--color-green)]'">{{ m.ta_density?.toFixed(1) ?? '—' }}%</span>
            <span style="font-size: 12px; color: var(--color-text-tertiary);">{{ m.platform_grade ?? '—' }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Guards -->
    <section v-if="qualityStore.guards.length > 0" class="s4">
      <div class="caption mb-3">质量门禁</div>
      <div class="space-y-2">
        <div
          v-for="g in qualityStore.guards"
          :key="g.guard_id"
          class="fine p-4 text-[12px]"
          :style="guardBorder(g.level)"
        >
          <div class="flex items-center justify-between mb-1">
            <span style="font-weight: 500;">{{ g.guard_id }}</span>
            <span style="font-size: 10px; font-weight: 500;" :style="guardColor(g.level)">{{ g.level }}</span>
          </div>
          <p style="color: var(--color-text-secondary);">{{ g.message }}</p>
        </div>
      </div>
    </section>

    <div v-if="qualityStore.error" class="mt-4 p-4 rounded-[var(--radius-md)] text-[12px]" style="border: 1px solid rgba(242,139,130,0.12); color: var(--color-red); background: rgba(242,139,130,0.03);">
      {{ qualityStore.error }}
    </div>
  </div>
</template>
