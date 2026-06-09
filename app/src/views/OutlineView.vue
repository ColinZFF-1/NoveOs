<script setup lang="ts">
import { computed, watch } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useOutlineStore } from '@/stores/outline'

const projectsStore = useProjectsStore()
const outlineStore = useOutlineStore()

const tabs = computed(() => [
  { key: 'outline' as const, label: '大纲' },
  { key: 'debts' as const, label: `债务 ${outlineStore.debtStats.total}` },
  { key: 'skills' as const, label: `技能 ${outlineStore.skills.length}` },
  { key: 'rules' as const, label: `规则 ${outlineStore.rules.length}` },
])

const debtColor = (s: string) => s === 'active' ? 'color: var(--color-orange);' : s === 'collected' ? 'color: var(--color-green);' : 'color: var(--color-text-tertiary);'
const ruleColor = (l: string) => l === 'strict' ? 'color: var(--color-red);' : l === 'medium' ? 'color: var(--color-orange);' : 'color: var(--color-green);'

watch(() => projectsStore.currentId, (id) => { if (id) outlineStore.fetchAll(id) }, { immediate: true })
</script>

<template>
  <div class="max-w-[900px]">
    <!-- Tabs -->
    <section class="flex gap-1 mb-6 s1">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="outlineStore.activeTab = tab.key"
        style="font-size: 12px; padding: 6px 14px; border-radius: var(--radius-md); transition: all 0.2s;"
        :style="outlineStore.activeTab === tab.key
          ? 'background: var(--color-accent-dim); color: var(--color-accent); border: 1px solid rgba(138,180,248,0.2);'
          : 'color: var(--color-text-tertiary); border: 1px solid transparent;'"
      >
        {{ tab.label }}
      </button>
    </section>

    <!-- 大纲 -->
    <section v-if="outlineStore.activeTab === 'outline'" class="s2">
      <div class="fine">
        <div v-for="o in outlineStore.outlines" :key="o.chapter" class="row">
          <div class="flex items-center gap-4">
            <span style="font-size: 11px; color: var(--color-text-tertiary); font-family: var(--font-display); min-width: 20px;">{{ String(o.chapter).padStart(2,'0') }}</span>
            <span style="font-size: 12px; color: var(--color-text-secondary);">{{ o.arc || '—' }}</span>
          </div>
          <span style="font-size: 12px; color: var(--color-text-tertiary); max-width: 50%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ o.core_event || '—' }}</span>
        </div>
        <div v-if="outlineStore.outlines.length === 0" class="py-8 text-center" style="font-size: 12px; color: var(--color-text-tertiary);">暂无大纲</div>
      </div>
    </section>

    <!-- 债务 -->
    <section v-if="outlineStore.activeTab === 'debts'" class="s2">
      <div class="flex gap-6 mb-6">
        <div><div style="font-size: 24px; font-weight: 300;">{{ outlineStore.debtStats.active }}</div><div class="caption mt-1">活跃</div></div>
        <div><div style="font-size: 24px; font-weight: 300; color: var(--color-green);">{{ outlineStore.debtStats.collected }}</div><div class="caption mt-1">已回收</div></div>
        <div><div style="font-size: 24px; font-weight: 300; color: var(--color-text-tertiary);">{{ outlineStore.debtStats.abandoned }}</div><div class="caption mt-1">已废弃</div></div>
      </div>
      <div class="fine">
        <div v-for="d in outlineStore.debts" :key="d.debt_id" class="row">
          <div style="font-size: 12px; max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ d.content }}</div>
          <div class="flex items-center gap-4">
            <span style="font-size: 11px; color: var(--color-text-tertiary);">{{ d.bury_chapter }} → {{ d.collect_chapter ?? '?' }}</span>
            <span style="font-size: 11px; font-weight: 500;" :style="debtColor(d.status)">{{ d.status }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 技能 -->
    <section v-if="outlineStore.activeTab === 'skills'" class="s2">
      <div class="fine">
        <div v-for="s in outlineStore.skills" :key="s.skill_name" class="row">
          <div class="flex items-center gap-4">
            <span style="font-size: 12px; font-weight: 500;">{{ s.skill_name }}</span>
            <span style="font-size: 11px; color: var(--color-text-tertiary);">{{ s.description || '—' }}</span>
          </div>
          <span style="font-size: 11px; color: var(--color-text-tertiary); font-family: var(--font-display);">{{ s.unlock_chapter }}</span>
        </div>
      </div>
    </section>

    <!-- 规则 -->
    <section v-if="outlineStore.activeTab === 'rules'" class="s2">
      <div class="fine">
        <div v-for="r in outlineStore.rules" :key="r.rule_type + r.rule_content" class="row">
          <div style="font-size: 12px;">{{ r.rule_type }}</div>
          <div class="flex items-center gap-4">
            <span style="font-size: 11px; color: var(--color-text-tertiary); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ r.rule_content }}</span>
            <span style="font-size: 11px; font-weight: 500;" :style="ruleColor(r.enforcement_level)">{{ r.enforcement_level }}</span>
          </div>
        </div>
      </div>
    </section>

    <div v-if="outlineStore.error" class="mt-4 p-4 rounded-[var(--radius-md)] text-[12px]" style="border: 1px solid rgba(242,139,130,0.12); color: var(--color-red); background: rgba(242,139,130,0.03);">
      {{ outlineStore.error }}
    </div>
  </div>
</template>
