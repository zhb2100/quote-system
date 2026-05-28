<script setup>
defineProps({
  icon:      { type: String, required: true },
  bgColor:   { type: String, required: true },
  iconColor: { type: String, required: true },
  label:     { type: String, required: true },
  value:     { type: [Number, String], required: true },
})
</script>

<template>
  <div class="stat-card anim-in">
    <div class="d-flex align-items-center gap-3">
      <div class="stat-icon" :style="{ background: bgColor, color: iconColor }">
        <i :class="icon"></i>
      </div>
      <div>
        <div class="text-muted small">{{ label }}</div>
        <div class="fw-bold" style="font-size:1.6rem">{{ value }}</div>
      </div>
    </div>
  </div>
</template>
