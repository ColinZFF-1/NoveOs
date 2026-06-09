<script setup lang="ts">
defineProps<{
  chapterNum: number
  wordCount?: number | null
  status: 'done' | 'writing' | 'pending'
}>()

function label(wordCount: number | null | undefined): string {
  if (wordCount == null || wordCount === 0) return '—'
  return `${wordCount}字`
}
</script>

<template>
  <div
    class="chapter-chip flex flex-col items-center justify-center aspect-square border transition-all duration-300 cursor-default"
    :class="{
      'bg-jade/5 border-jade/20 hover:border-jade/40': status === 'done',
      'bg-amber/5 border-amber/20 animate-amber-pulse': status === 'writing',
      'bg-surface border-white/[0.03] hover:border-white/[0.06]': status === 'pending',
    }"
  >
    <span
      class="font-mono text-sm font-semibold tabular-nums"
      :class="{
        'text-jade': status === 'done',
        'text-amber': status === 'writing',
        'text-dim': status === 'pending',
      }"
    >{{ chapterNum }}</span>
    <span class="text-[9px] text-dim/70 mt-0.5 font-mono">{{ label(wordCount) }}</span>
  </div>
</template>

<style scoped>
.chapter-chip {
  border-radius: 2px;
}
</style>
