<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <div class="min-h-screen bg-white text-black">
    <AppHeader />
    <main>
      <router-view v-slot="{ Component, route }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style>
.page-enter-active {
  animation: reveal 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.page-leave-active {
  animation: reveal 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards;
}
</style>
