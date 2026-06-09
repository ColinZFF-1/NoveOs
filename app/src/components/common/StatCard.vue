<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

const props = defineProps<{
  label: string
  value: string | number
  sub?: string
  accent?: 'amber' | 'jade' | 'crimson' | 'indigo' | 'default'
}>()

const displayValue = ref('—')
const mounted = ref(false)

function animateValue(target: number) {
  const duration = 800
  const start = performance.now()
  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    displayValue.value = Math.round(target * eased).toLocaleString()
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(() => {
  mounted.value = true
  if (typeof props.value === 'number') {
    animateValue(props.value)
  } else {
    displayValue.value = String(props.value)
  }
})

watch(() => props.value, (newVal) => {
  if (typeof newVal === 'number') {
    animateValue(newVal)
  } else {
    displayValue.value = String(newVal)
  }
})

const accentClasses: Record<string, { border: string; glow: string; text: string }> = {
  amber: {
    border: 'border-amber/15 hover:border-amber/30',
    glow: 'shadow-amber/5',
    text: 'text-amber',
  },
  jade: {
    border: 'border-jade/15 hover:border-jade/30',
    glow: 'shadow-jade/5',
    text: 'text-jade',
  },
  crimson: {
    border: 'border-crimson/15 hover:border-crimson/30',
    glow: 'shadow-crimson/5',
    text: 'text-crimson',
  },
  indigo: {
    border: 'border-indigo/15 hover:border-indigo/30',
    glow: 'shadow-indigo/5',
    text: 'text-indigo',
  },
  default: {
    border: 'border-white/[0.04] hover:border-white/[0.08]',
    glow: '',
    text: 'text-primary',
  },
}

const style = accentClasses[props.accent ?? 'default']
</script>

<template>
  <div
    class="stat-card bg-surface border transition-all duration-300 px-5 py-4"
    :class="[style.border, style.glow]"
  >
    <h3 class="font-mono text-[10px] text-dim uppercase tracking-[0.15em] mb-2">{{ label }}</h3>
    <div class="font-mono text-2xl font-bold tabular-nums" :class="style.text">
      {{ mounted ? displayValue : '—' }}
    </div>
    <p v-if="sub" class="text-xs text-dim mt-1.5">{{ sub }}</p>
  </div>
</template>

<style scoped>
.stat-card {
  border-radius: 2px;
}
.stat-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
</style>
