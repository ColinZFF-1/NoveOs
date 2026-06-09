<script setup lang="ts">
defineProps<{
  text?: string
}>()
</script>

<template>
  <div class="flex items-center gap-3 text-dim">
    <span class="w-2 h-2 bg-amber rounded-full animate-amber-pulse" />
    <span class="font-mono text-xs tracking-wider">{{ text ?? '加载中' }}</span>
  </div>
</template>
