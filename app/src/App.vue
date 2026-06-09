<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
import { onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'

const projectsStore = useProjectsStore()

onMounted(() => {
  projectsStore.fetchProjects()
})
</script>

<template>
  <AppLayout />
</template>
