<script setup>
/**
 * ModalDialog — 通用 Modal 弹窗容器
 * 消除 App.vue / ProjectDetailView / AdminView 五处相同的 Teleport+backdrop+modal 结构
 */
defineProps({
  show:  { type: Boolean, required: true },
  title: { type: String,  default: '' },
  size:  { type: String,  default: '' }, // '', 'sm', 'lg', 'xl'
})
const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="modal-backdrop show" @click="emit('close')"></div>
    <div v-if="show" class="modal d-block modern-modal" tabindex="-1" role="dialog" aria-modal="true">
      <div class="modal-dialog modal-dialog-centered" :class="size ? `modal-${size}` : ''">
        <div class="modal-content" @click.stop>
          <div class="modal-header" v-if="title || $slots.header">
            <slot name="header">
              <h5 class="modal-title fw-semibold">{{ title }}</h5>
            </slot>
            <button type="button" class="btn-close" @click="emit('close')" aria-label="关闭"></button>
          </div>
          <div class="modal-body">
            <slot></slot>
          </div>
          <div class="modal-footer" v-if="$slots.footer">
            <slot name="footer"></slot>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
