<script setup>
import { ref, computed, watch, inject, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'
import QuoteFormFields from '../components/quote/QuoteFormFields.vue'

const router = useRouter()
const route = useRoute()
const toast = inject('toast')
const { api } = useApi()

const editId = computed(() => route.query.edit || null)
const isEditing = computed(() => !!editId.value)

const form = ref({
  title: '', supplier_id: null, salesperson_id: null,
  order_start: new Date().toISOString().slice(0, 10),
  order_end: '', project_category: [], remark: '',
})
const saving = ref(false)
const errors = ref({ title: '' })
const supplierList = ref([])
const salespersonList = ref([])

async function loadOptions() {
  const [sRes, spRes] = await Promise.allSettled([api('/api/suppliers'), api('/api/salespersons')])
  if (sRes.status === 'fulfilled') supplierList.value = sRes.value.suppliers || []
  if (spRes.status === 'fulfilled') salespersonList.value = spRes.value.salespersons || []
}

async function loadQuote() {
  if (!editId.value) return
  try {
    const data = await api(`/api/quotes/${editId.value}`)
    if (data.error) { toast(data.error, 'danger'); return }
    const q = data.quote
    form.value = {
      title: q.title || '', supplier_id: q.supplier_id || null,
      salesperson_id: q.salesperson_id || null,
      order_start: q.order_start || new Date().toISOString().slice(0, 10),
      order_end: q.order_end || '',
      project_category: q.project_category ? q.project_category.split(', ').filter(Boolean) : [],
      remark: q.remark || '',
    }
  } catch (e) { toast('加载报价单失败', 'danger') }
}

async function saveQuote() {
  errors.value = { title: '' }
  if (!form.value.title.trim()) { errors.value.title = '报价单编号不能为空'; return }
  saving.value = true
  try {
    const body = {
      title: form.value.title.trim(),
      supplier_id: form.value.supplier_id || null,
      salesperson_id: form.value.salesperson_id || null,
      order_start: form.value.order_start,
      order_end: form.value.order_end,
      project_category: form.value.project_category.join(', '),
      remark: form.value.remark,
    }
    const r = isEditing.value
      ? await api(`/api/quotes/${editId.value}`, 'PUT', body)
      : await api('/api/quotes', 'POST', body)
    if (r.error) { toast(r.error, 'danger'); return }
    toast(isEditing.value ? '报价单已更新' : '报价单创建成功')
    router.push({ name: 'quotes' })
  } catch (e) {
    toast('保存失败', 'danger')
  } finally {
    saving.value = false
  }
}

watch(editId, loadQuote, { immediate: true })
onMounted(loadOptions)
</script>

<template>
  <div>
    <div class="page-header">
      <h5><i class="bi bi-plus-circle"></i>{{ isEditing ? '编辑报价单' : '新建报价单' }}</h5>
      <router-link :to="{ name: 'quotes' }" class="btn btn-outline-secondary btn-modern">
        <i class="bi bi-arrow-left"></i> 返回列表
      </router-link>
    </div>

    <div class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-file-text text-primary me-2"></i>订单信息</div>
      <QuoteFormFields v-model="form" :supplier-list="supplierList" :salesperson-list="salespersonList" :errors="errors" />
    </div>

    <div class="d-flex justify-content-end mt-3">
      <button class="btn btn-primary btn-modern btn-lg" @click="saveQuote" :disabled="saving">
        <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-check-lg me-1"></i>保存报价单
      </button>
    </div>
  </div>
</template>
