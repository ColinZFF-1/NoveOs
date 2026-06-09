<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { usePipelineStore } from '@/stores/pipeline'

const projectsStore = useProjectsStore()
const pipelineStore = usePipelineStore()

const chapterRange = ref('44-48')
const isStarting = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const steps = [
  { key: 'director', label: '导演' },
  { key: 'beat', label: '节拍' },
  { key: 'writer', label: '写手' },
  { key: 'hook', label: '钩子' },
  { key: 'polish', label: '润色' },
  { key: 'auditor', label: '审计' },
]

const activeStep = computed(() => {
  const idx = pipelineStore.status?.current_step_index ?? 0
  return Math.min(idx, steps.length - 1)
})

const isRunning = computed(() => pipelineStore.status?.is_running ?? false)
const canStart = computed(() => pipelineStore.status?.can_start ?? true)

async function handleStart() {
  if (!projectsStore.currentId) return
  isStarting.value = true
  try {
    await pipelineStore.start(projectsStore.currentId, chapterRange.value)
    startPolling()
  } finally {
    isStarting.value = false
  }
}

async function handlePause() {
  if (!projectsStore.currentId) return
  await pipelineStore.pause(projectsStore.currentId)
}

async function handleStop() {
  if (!projectsStore.currentId) return
  await pipelineStore.stop(projectsStore.currentId)
  stopPolling()
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (projectsStore.currentId) pipelineStore.fetchStatus(projectsStore.currentId)
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => {
  if (projectsStore.currentId) {
    pipelineStore.fetchStatus(projectsStore.currentId)
    if (isRunning.value) startPolling()
  }
})

onUnmounted(() => stopPolling())
</script>

<template>
  <div class="max-w-[900px]">
    <!-- 状态 -->
    <section class="mb-10 s1">
      <div class="flex items-baseline gap-3 mb-1">
        <span
          class="w-1.5 h-1.5 rounded-full"
          :class="isRunning ? 'bg-[var(--color-orange)]' : canStart ? 'bg-[var(--color-green)]' : 'bg-[var(--color-text-tertiary)]'"
        ></span>
        <span style="font-size: 13px; color: var(--color-text-secondary);">
          {{ isRunning ? '写作中' : canStart ? '就绪' : '已暂停' }}
        </span>
      </div>
      <div class="display" style="font-size: 36px;">
        第 {{ projectsStore.currentStatus?.current_chapter ?? '—' }} 章
      </div>
    </section>

    <!-- 控制 -->
    <section class="flex items-center gap-2 mb-12 s2">
      <input
        v-if="canStart && !isRunning"
        v-model="chapterRange"
        type="text"
        placeholder="章节范围"
        class="btn"
        style="width: 90px; text-align: center;"
      />
      <button v-if="canStart && !isRunning" @click="handleStart" :disabled="isStarting" class="btn btn-accent">
        {{ isStarting ? '…' : '启动' }}
      </button>
      <button v-if="isRunning" @click="handlePause" class="btn">暂停</button>
      <button v-if="isRunning" @click="handleStop" class="btn" style="color: var(--color-red); border-color: rgba(242,139,130,0.2);">停止</button>
      <button v-if="!canStart && !isRunning" @click="handleStart" class="btn btn-accent">继续</button>
    </section>

    <!-- 流程 -->
    <section class="mb-12 s3">
      <div class="caption mb-4">Agent 流程</div>
      <div class="flex items-center gap-1">
        <div
          v-for="(step, i) in steps"
          :key="step.key"
          class="flex-1 text-center"
        >
          <div
            class="py-3 rounded-[var(--radius-md)] text-[11px] transition-all"
            :class="
              i < activeStep
                ? 'fine-active text-[var(--color-green)]'
                : i === activeStep && isRunning
                ? 'fine-active text-[var(--color-orange)]'
                : i === activeStep
                ? 'fine text-[var(--color-orange)]'
                : 'fine text-[var(--color-text-tertiary)]'
            "
          >
            {{ step.label }}
          </div>
          <div v-if="i < steps.length - 1" class="hidden md:block absolute h-[1px]" style="background: var(--color-border); top: 50%; right: -4px; width: 8px;"></div>
        </div>
      </div>
    </section>

    <!-- 门禁 -->
    <section v-if="pipelineStore.status?.audit" class="grid grid-cols-2 gap-3 s4">
      <div class="fine p-5">
        <div class="caption mb-3">质量门禁</div>
        <div class="flex justify-between text-[13px] mb-2">
          <span style="color: var(--color-text-secondary);">字数</span>
          <span :style="pipelineStore.status.audit.quality_passed ? 'color: var(--color-green);' : 'color: var(--color-red);'">{{ pipelineStore.status.audit.quality_passed ? '通过' : '未通过' }}</span>
        </div>
        <div class="flex justify-between text-[13px]">
          <span style="color: var(--color-text-secondary);">敏感词</span>
          <span :style="pipelineStore.status.audit.sensitive_passed ? 'color: var(--color-green);' : 'color: var(--color-red);'">{{ pipelineStore.status.audit.sensitive_passed ? '通过' : '未通过' }}</span>
        </div>
      </div>
    </section>

    <div v-if="pipelineStore.error" class="mt-4 p-4 rounded-[var(--radius-md)] text-[12px]" style="border: 1px solid rgba(242,139,130,0.15); color: var(--color-red); background: rgba(242,139,130,0.04);">
      {{ pipelineStore.error }}
    </div>
  </div>
</template>
