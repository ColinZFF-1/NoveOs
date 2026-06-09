<script setup lang="ts">
defineProps<{
  mode: 'PASS' | 'WARN' | 'BLOCK' | null | undefined
}>()

function label(mode: string | null | undefined): string {
  switch (mode) {
    case 'PASS': return 'PASS'
    case 'WARN': return 'WARN'
    case 'BLOCK': return 'BLOCK'
    default: return '—'
  }
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider"
    :class="{
      'bg-jade/10 text-jade border border-jade/20': mode === 'PASS',
      'bg-amber/10 text-amber border border-amber/20': mode === 'WARN',
      'bg-crimson/10 text-crimson border border-crimson/20 animate-amber-pulse': mode === 'BLOCK',
      'bg-surface text-dim border border-white/[0.04]': !mode,
    }"
  >
    <span
      v-if="mode === 'PASS' || mode === 'WARN' || mode === 'BLOCK'"
      class="w-1.5 h-1.5 rounded-full"
      :class="{
        'bg-jade': mode === 'PASS',
        'bg-amber': mode === 'WARN',
        'bg-crimson': mode === 'BLOCK',
      }"
    />
    {{ label(mode) }}
  </span>
</template>
