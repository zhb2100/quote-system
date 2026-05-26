<script setup>
import { ref, reactive, inject, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'

const router = useRouter()
const route = useRoute()
const toast = inject('toast')
const { api } = useApi()

const editId = ref(route.query.edit || null)
const isEditing = ref(!!editId.value)

const form = reactive({
  title: '',
  supplier_id: null,
  salesperson_id: null,
  order_start: new Date().toISOString().slice(0, 10),
  order_end: '',
  project_category: [],
  remark: '',
})

const saving = ref(false)
const errors = reactive({ title: '', supplier_id: '', salesperson_id: '' })
const supplierList = ref([])
const salespersonList = ref([])
const projectOptions = ['PCBA', '固件开发', '算法开发']

async function loadOptions() {
  const [sRes, spRes] = await Promise.allSettled([
    api('/api/suppliers'),
    api('/api/salespersons'),
  ])
  if (sRes.status === 'fulfilled') {
    supplierList.value = sRes.value.suppliers || []
  }
  if (spRes.status === 'fulfilled') {
    salespersonList.value = spRes.value.salespersons || []
  }
}

async function loadQuote() {
  if (!editId.value) return
  try {
    const data = await api(`/api/quotes/${editId.value}`)
    if (data.error) { toast(data.error, 'danger'); editId.value = null; return }
    const q = data.quote
    form.title = q.title || ''
    form.supplier_id = q.supplier_id || null
    form.salesperson_id = q.salesperson_id || null
    form.order_start = q.order_start || new Date().toISOString().slice(0, 10)
    form.order_end = q.order_end || ''
    form.project_category = q.project_category ? q.project_category.split(', ').filter(Boolean) : []
    form.remark = q.remark || ''
  } catch (e) {
    toast('加载报价单失败', 'danger')
  }
}

async function saveQuote() {
  errors.title = ''; errors.supplier_id = ''; errors.salesperson_id = ''
  let hasErr = false
  if (!form.title.trim()) { errors.title = '报价单编号不能为空'; hasErr = true }
  saving.value = true
  if (hasErr) { saving.value = false; return }
  try {
    const body = {
      title: form.title.trim(),
      supplier_id: form.supplier_id || null,
      salesperson_id: form.salesperson_id || null,
      order_start: form.order_start,
      order_end: form.order_end,
      project_category: form.project_category.join(', '),
      remark: form.remark,
    }
    if (isEditing.value) {
      const r = await api(`/api/quotes/${editId.value}`, 'PUT', body)
      if (r.error) { toast(r.error, 'danger'); return }
      toast('报价单已更新')
    } else {
      const r = await api('/api/quotes', 'POST', body)
      if (r.error) { toast(r.error, 'danger'); return }
      toast('报价单创建成功')
    }
    router.push({ name: 'quotes' })
  } catch (e) {
    toast('保存失败', 'danger')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadOptions()
  loadQuote()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h5><i class="bi bi-plus-circle"></i>{{ isEditing ? '编辑报价单' : '新建报价单' }}</h5>
      <router-link :to="{name:'quotes'}" class="btn btn-outline-secondary btn-modern">
        <i class="bi bi-arrow-left"></i> 返回列表
      </router-link>
    </div>

    <div class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-file-text text-primary"></i>订单信息</div>
      <div class="row g-2">
        <div class="col-12">
          <label class="form-label-modern">报价单编号 <span class="text-danger">*</span></label>
          <input class="form-control" :class="{ 'is-invalid': errors.title }" v-model="form.title" placeholder="例如：ZH-2026-001">
          <div v-if="errors.title" class="invalid-feedback">{{ errors.title }}</div>
        </div>
        <div class="col-md-6">
          <label class="form-label-modern">供应商</label>
          <select class="form-select" :class="{ 'is-invalid': errors.supplier_id }" v-model="form.supplier_id">
            <option :value="null">请选择供应商</option>
            <option v-for="s in supplierList" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label-modern">业务员</label>
          <select class="form-select" v-model="form.salesperson_id">
            <option :value="null">请选择业务员</option>
            <option v-for="s in salespersonList" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label-modern">订单起始日期</label>
          <input class="form-control" v-model="form.order_start" type="date">
        </div>
        <div class="col-md-6">
          <label class="form-label-modern">订单完成日期</label>
          <input class="form-control" v-model="form.order_end" type="date">
        </div>
        <div class="col-12">
          <label class="form-label-modern">项目个类</label>
          <div class="d-flex gap-3 mt-1">
            <label v-for="opt in projectOptions" :key="opt" class="form-check form-check-inline">
              <input class="form-check-input" type="checkbox" :value="opt" v-model="form.project_category">
              <span class="form-check-label">{{ opt }}</span>
            </label>
          </div>
        </div>
        <div class="col-12">
          <label class="form-label-modern">备注</label>
          <textarea class="form-control" v-model="form.remark" rows="3" placeholder=""></textarea>
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-end mt-3">
      <button class="btn btn-primary btn-modern btn-lg" @click="saveQuote" :disabled="saving">
        <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-check-lg me-1"></i>保存报价单
      </button>
    </div>
  </div>
</template>
