<script setup>
/**
 * QuoteFormFields — 报价单通用表单字段
 * 供 NewQuoteView 和 ProjectDetailView 的内联编辑共用，消除重复
 */
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  supplierList:    { type: Array, default: () => [] },
  salespersonList: { type: Array, default: () => [] },
  errors:          { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

const PROJECT_OPTIONS = ['PCBA', '固件开发', '算法开发']

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

function toggleCategory(opt) {
  const cur = props.modelValue.project_category || []
  const next = cur.includes(opt) ? cur.filter(c => c !== opt) : [...cur, opt]
  update('project_category', next)
}
</script>

<template>
  <div class="row g-2">
    <div class="col-12">
      <label class="form-label-modern" for="qf-title">
        报价单编号 <span class="text-danger">*</span>
      </label>
      <input
        id="qf-title"
        class="form-control"
        :class="{ 'is-invalid': errors.title }"
        :value="modelValue.title"
        @input="update('title', $event.target.value)"
        placeholder="例如：ZH-2026-001"
      >
      <div v-if="errors.title" class="invalid-feedback">{{ errors.title }}</div>
    </div>

    <div class="col-md-6">
      <label class="form-label-modern" for="qf-supplier">供应商</label>
      <select id="qf-supplier" class="form-select"
        :value="modelValue.supplier_id"
        @change="update('supplier_id', $event.target.value ? Number($event.target.value) : null)">
        <option :value="null">请选择供应商</option>
        <option v-for="s in supplierList" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <div class="col-md-6">
      <label class="form-label-modern" for="qf-sp">业务员</label>
      <select id="qf-sp" class="form-select"
        :value="modelValue.salesperson_id"
        @change="update('salesperson_id', $event.target.value ? Number($event.target.value) : null)">
        <option :value="null">请选择业务员</option>
        <option v-for="s in salespersonList" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <div class="col-md-6">
      <label class="form-label-modern" for="qf-start">订单起始日期</label>
      <input id="qf-start" class="form-control" type="date"
        :value="modelValue.order_start"
        @input="update('order_start', $event.target.value)">
    </div>

    <div class="col-md-6">
      <label class="form-label-modern" for="qf-end">订单完成日期</label>
      <input id="qf-end" class="form-control" type="date"
        :value="modelValue.order_end"
        @input="update('order_end', $event.target.value)">
    </div>

    <div class="col-12">
      <label class="form-label-modern">项目类别</label>
      <div class="d-flex gap-3 mt-1 flex-wrap">
        <label v-for="opt in PROJECT_OPTIONS" :key="opt" class="form-check form-check-inline">
          <input class="form-check-input" type="checkbox"
            :checked="(modelValue.project_category || []).includes(opt)"
            @change="toggleCategory(opt)">
          <span class="form-check-label">{{ opt }}</span>
        </label>
      </div>
    </div>

    <div class="col-12">
      <label class="form-label-modern" for="qf-remark">备注</label>
      <textarea id="qf-remark" class="form-control" rows="3"
        :value="modelValue.remark"
        @input="update('remark', $event.target.value)"></textarea>
    </div>
  </div>
</template>
