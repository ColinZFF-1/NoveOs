<script setup lang="ts">
import { computed } from 'vue'
import type { BrandGeoProfile } from '@/types/geo'

const props = defineProps<{
  brand: BrandGeoProfile
}>()

const dims = [
  { key: 'schema', label: 'Schema结构化' },
  { key: 'engineAdapt', label: '双引擎适配' },
  { key: 'automation', label: '自动化能力' },
  { key: 'entityTrust', label: '实体一致性' },
  { key: 'eeat', label: 'E-E-A-T权威' },
  { key: 'freshness', label: '内容新鲜度' },
  { key: 'compliance', label: '合规安全' },
  { key: 'promptCov', label: 'Prompt覆盖' },
]

const rows = computed(() =>
  dims.map((d) => ({
    ...d,
    kim: props.brand.dimensions[d.key]?.kim ?? 0,
    ds: props.brand.dimensions[d.key]?.deepSeek ?? 0,
    diff: (props.brand.dimensions[d.key]?.kim ?? 0) - (props.brand.dimensions[d.key]?.deepSeek ?? 0),
  }))
)

const kimAvg = computed(() => Math.round(rows.value.reduce((s, r) => s + r.kim, 0) / rows.value.length))
const dsAvg = computed(() => Math.round(rows.value.reduce((s, r) => s + r.ds, 0) / rows.value.length))
</script>

<template>
  <div class="bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] rounded-lg overflow-hidden">
    <div class="px-4 py-3 border-b border-[var(--color-border-subtle)] flex items-center justify-between">
      <h3 class="text-sm font-medium text-[var(--color-text-primary)]">引擎差异分析</h3>
      <div class="flex items-center gap-3 text-[10px] font-mono">
        <span class="text-amber-400">Kimi 均值 {{ kimAvg }}</span>
        <span class="text-slate-600">vs</span>
        <span class="text-blue-400">DeepSeek 均值 {{ dsAvg }}</span>
      </div>
    </div>

    <div class="divide-y divide-[var(--color-border-subtle)]">
      <div
        v-for="r in rows"
        :key="r.key"
        class="px-4 py-2.5 flex items-center gap-4 hover:bg-[var(--color-slate-800)]/50 transition-colors"
      >
        <span class="w-24 text-xs text-[var(--color-text-secondary)] shrink-0">{{ r.label }}</span>

        <div class="flex-1 flex items-center gap-3">
          <!-- Kimi bar -->
          <div class="flex-1 flex items-center gap-2 justify-end">
            <div class="w-24 h-2 bg-[var(--color-slate-800)] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-amber-500"
                :style="{ width: r.kim + '%' }"
              />
            </div>
            <span class="text-[10px] font-mono w-6 text-right text-amber-400">{{ r.kim }}</span>
          </div>

          <!-- Diff indicator -->
          <div class="w-10 flex justify-center">
            <span
              class="text-[10px] font-mono"
              :class="r.diff > 0 ? 'text-amber-400' : r.diff < 0 ? 'text-blue-400' : 'text-slate-500'"
            >
              {{ r.diff > 0 ? '+' : '' }}{{ r.diff }}
            </span>
          </div>

          <!-- DeepSeek bar -->
          <div class="flex-1 flex items-center gap-2">
            <span class="text-[10px] font-mono w-6 text-left text-blue-400">{{ r.ds }}</span>
            <div class="w-24 h-2 bg-[var(--color-slate-800)] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-blue-500"
                :style="{ width: r.ds + '%' }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
