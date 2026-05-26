<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({ modelValue: { type: String, default: null } })
const emit = defineEmits(['update:modelValue'])

const show = ref(false)
const viewYear = ref(new Date().getFullYear())
const picker = ref(null)

const selectedText = computed(() => {
  if (!props.modelValue) return '全部月份'
  const dash = props.modelValue.indexOf('-')
  if (dash > 0) {
    const y = props.modelValue.slice(0, dash)
    const m = parseInt(props.modelValue.slice(dash + 1))
    return `${y}年${m}月`
  }
  return `${props.modelValue}年`
})

const months = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月']

function selectMonth(m) {
  emit('update:modelValue', `${viewYear.value}-${String(m).padStart(2, '0')}`)
  show.value = false
}
function selectYear() {
  emit('update:modelValue', String(viewYear.value))
  show.value = false
}
function clearFilter() {
  emit('update:modelValue', null)
  show.value = false
}
function prevYear() { viewYear.value-- }
function nextYear() { viewYear.value++ }

function onClickOutside(e) {
  if (picker.value && !picker.value.contains(e.target)) show.value = false
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<template>
  <div ref="picker" style="position:relative">
    <button class="btn btn-outline-secondary btn-sm" style="min-width:135px" @click="show = !show">
      <i class="bi bi-calendar3 me-1"></i>{{ selectedText }}
    </button>
    <div v-if="show" class="card shadow-sm" style="position:absolute;top:100%;left:0;z-index:1050;width:290px;margin-top:4px;padding:14px;border:1px solid #dee2e6" @click.stop>
      <div class="d-flex justify-content-between align-items-center mb-2">
        <button class="btn btn-sm btn-link p-0 text-decoration-none" @click="prevYear">&laquo;</button>
        <strong>{{ viewYear }}年</strong>
        <button class="btn btn-sm btn-link p-0 text-decoration-none" @click="nextYear">&raquo;</button>
      </div>
      <div class="row g-1">
        <div v-for="(m, i) in months" :key="i" class="col-3">
          <button class="btn btn-sm w-100 py-1" style="font-size:.82rem"
            :class="modelValue === `${viewYear}-${String(i+1).padStart(2,'0')}` ? 'btn-primary' : 'btn-outline-secondary'"
            @click="selectMonth(i+1)">{{ m }}</button>
        </div>
      </div>
      <div class="d-flex gap-2 mt-2 pt-2" style="border-top:1px solid #eee">
        <button class="btn btn-sm btn-outline-primary flex-grow-1" @click="selectYear">全年</button>
        <button class="btn btn-sm btn-outline-secondary flex-grow-1" @click="clearFilter">取消</button>
      </div>
    </div>
  </div>
</template>
