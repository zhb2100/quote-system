<script setup>
defineProps({
  icon:    { type: String, default: 'bi-inbox' },
  message: { type: String, default: '暂无数据' },
})
</script>

<template>
  <div class="empty-state">
    <i :class="`bi ${icon}`"></i>
    <p>{{ message }}</p>
    <slot></slot>
  </div>
</template>
