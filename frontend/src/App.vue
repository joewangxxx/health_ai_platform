<template>
  <router-view />
  <ToastProvider />
</template>

<script setup>
// Light mode only - no theme switching logic needed
import ToastProvider from './components/ui/ToastProvider.vue'

</script>

<style>
/* Global Resets */
html,
body,
#app {
  min-height: 100%;
  margin: 0;
  padding: 0;
}

body {
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
</style>
