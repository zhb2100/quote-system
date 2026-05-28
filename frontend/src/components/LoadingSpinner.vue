<script setup>
defineProps({
  size: { type: String, default: '' },        // '' | 'sm'
  text: { type: String, default: '加载中...' },
  center: { type: Boolean, default: false },
})
</script>

<template>
  <div :class="center ? 'text-center py-5' : 'd-inline-flex align-items-center gap-2'">
    <div
      class="spinner-border text-primary"
      :class="size === 'sm' ? 'spinner-border-sm' : ''"
      role="status"
    >
      <span class="visually-hidden">{{ text }}</span>
    </div>
    <span v-if="center && text" class="text-muted small">{{ text }}</span>
  </div>
</template>
