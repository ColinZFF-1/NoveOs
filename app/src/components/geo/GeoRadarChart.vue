<script setup lang="ts">
import { computed } from 'vue'
import { GEO_DIMENSIONS } from '@/types/geo'

const props = defineProps<{
  data: Record<string, { kim: number; deepSeek: number }>
  size?: number
}>()

const size = props.size ?? 280
const center = size / 2
const radius = size / 2 - 32
const levels = 5

const dims = GEO_DIMENSIONS.map((d, i) => {
  const angle = (Math.PI * 2 * i) / GEO_DIMENSIONS.length - Math.PI / 2
  return {
    ...d,
    angle,
    x: center + Math.cos(angle) * radius,
    y: center + Math.sin(angle) * radius,
    labelX: center + Math.cos(angle) * (radius + 22),
    labelY: center + Math.sin(angle) * (radius + 22),
  }
})

function polyPoints(scores: number[]) {
  return scores
    .map((s, i) => {
      const a = dims[i].angle
      const r = (s / 100) * radius
      return `${center + Math.cos(a) * r},${center + Math.sin(a) * r}`
    })
    .join(' ')
}

const kimScores = computed(() => dims.map((d) => props.data[d.key]?.kim ?? 0))
const dsScores = computed(() => dims.map((d) => props.data[d.key]?.deepSeek ?? 0))

const gridLines = Array.from({ length: levels }, (_, i) => {
  const r = ((i + 1) / levels) * radius
  return dims.map((d) => `${center + Math.cos(d.angle) * r},${center + Math.sin(d.angle) * r}`).join(' ')
})
</script>

<template>
  <svg :width="size" :height="size" class="overflow-visible">
    <!-- Grid polygons -->
    <polygon
      v-for="(points, i) in gridLines"
      :key="i"
      :points="points"
      fill="none"
      stroke="rgba(184,115,51,0.12)"
      stroke-width="1"
    />
    <!-- Axis lines -->
    <line
      v-for="d in dims"
      :key="d.key"
      :x1="center"
      :y1="center"
      :x2="d.x"
      :y2="d.y"
      stroke="rgba(184,115,51,0.15)"
      stroke-width="1"
    />
    <!-- DeepSeek area -->
    <polygon
      :points="polyPoints(dsScores)"
      fill="rgba(59,130,246,0.15)"
      stroke="#3b82f6"
      stroke-width="2"
      stroke-linejoin="round"
      class="animate-dash-draw"
      style="stroke-dasharray: 800; stroke-dashoffset: 800;"
    />
    <!-- Kimi area -->
    <polygon
      :points="polyPoints(kimScores)"
      fill="rgba(217,119,6,0.15)"
      stroke="#d97706"
      stroke-width="2"
      stroke-linejoin="round"
      class="animate-dash-draw"
      style="stroke-dasharray: 800; stroke-dashoffset: 800; animation-delay: 0.3s;"
    />
    <!-- Labels -->
    <text
      v-for="d in dims"
      :key="d.key + '-label'"
      :x="d.labelX"
      :y="d.labelY"
      text-anchor="middle"
      dominant-baseline="middle"
      class="text-[9px] fill-[var(--color-text-muted)]"
      style="font-family: var(--font-mono);"
    >
      {{ d.label }}
    </text>
    <!-- Center dot -->
    <circle :cx="center" :cy="center" r="2" fill="var(--color-geo-copper)" />
  </svg>
</template>
