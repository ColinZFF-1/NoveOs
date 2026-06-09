<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  description: string
  kim: number
  deepSeek: number
  weight: number
}>()

const avg = computed(() => Math.round((props.kim + props.deepSeek) / 2))
const diff = computed(() => props.kim - props.deepSeek)
const better = computed(() => (diff.value > 3 ? 'kim' : diff.value < -3 ? 'ds' : 'eq'))
</script>

<template>
  <div
    class="group relative bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] rounded-lg p-4 hover:border-[var(--color-geo-copper)] transition-colors duration-300"
  >
    <!-- Scanline effect on hover -->
    <div
      class="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none overflow-hidden"
    >
      <div
        class="absolute inset-x-0 h-px bg-[var(--color-geo-copper)] opacity-20 animate-scanline"
      />
    </div>

    <div class="flex items-start justify-between mb-3">
      <div>
        <h4 class="text-sm font-medium text-[var(--color-text-primary)]">{{ label }}</h4>
        <p class="text-[10px] text-[var(--color-text-muted)] mt-0.5">{{ description }}</p>
      </div>
      <div class="flex items-center gap-1.5">
        <span
          class="text-[10px] px-1.5 py-0.5 rounded font-mono"
          :class="
            better === 'kim'
              ? 'bg-amber-500/10 text-amber-400'
              : better === 'ds'
                ? 'bg-blue-500/10 text-blue-400'
                : 'bg-slate-700 text-slate-400'
          "
        >
          {{ better === 'kim' ? 'Kimi ↑' : better === 'ds' ? 'DeepSeek ↑' : '均衡' }}
        </span>
      </div>
    </div>

    <!-- Score bars -->
    <div class="space-y-2.5">
      <div class="flex items-center gap-2">
        <span class="text-[10px] w-16 text-right text-[var(--color-text-muted)] font-mono"
          >Kimi</span
        >
        <div class="flex-1 h-1.5 bg-[var(--color-slate-800)] rounded-full overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-700"
            :style="{ width: kim + '%' }"
          />
        </div>
        <span class="text-xs w-8 text-right font-mono text-amber-400">{{ kim }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[10px] w-16 text-right text-[var(--color-text-muted)] font-mono"
          >DeepSeek</span
        >
        <div class="flex-1 h-1.5 bg-[var(--color-slate-800)] rounded-full overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-blue-700 to-blue-400 transition-all duration-700"
            :style="{ width: deepSeek + '%' }"
          />
        </div>
        <span class="text-xs w-8 text-right font-mono text-blue-400">{{ deepSeek }}</span>
      </div>
    </div>

    <!-- Bottom meta -->
    <div class="mt-3 pt-2 border-t border-[var(--color-border-subtle)] flex items-center justify-between">
      <span class="text-[10px] text-[var(--color-text-muted)]">权重 {{ (weight * 100).toFixed(0) }}%</span>
      <span class="text-sm font-semibold font-mono" :class="avg >= 70 ? 'text-emerald-400' : avg >= 50 ? 'text-amber-400' : 'text-rose-400'">
        {{ avg }}
      </span>
    </div>
  </div>
</template>
