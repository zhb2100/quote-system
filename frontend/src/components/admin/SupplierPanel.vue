<script setup>
import { ref, inject, onMounted } from 'vue'
import { useApi } from '../../composables/useApi'
import ModalDialog from '../ModalDialog.vue'
import LoadingSpinner from '../LoadingSpinner.vue'
import EmptyState from '../EmptyState.vue'

const toast = inject('toast')
const { api } = useApi()

const suppliers = ref([])
const loading = ref(true)

async function fetchSuppliers() {
  loading.value = true
  try {
    const data = await api('/api/suppliers?per_page=200')
    if (!data.error) suppliers.value = data.suppliers || []
  } catch (e) {
    toast('加载供应商失败', 'danger')
  } finally {
    loading.value = false
  }
}

// Modal — 支持全部字段
const showModal = ref(false)
const editId = ref(null)
const form = ref({ name: '', contact_person: '', phone: '', email: '', address: '', notes: '' })

function openAdd() {
  editId.value = null
  form.value = { name: '', contact_person: '', phone: '', email: '', address: '', notes: '' }
  showModal.value = true
}
function openEdit(s) {
  editId.value = s.id
  form.value = {
    name: s.name || '',
    contact_person: s.contact_person || '',
    phone: s.phone || '',
    email: s.email || '',
    address: s.address || '',
    notes: s.notes || '',
  }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) { toast('请输入名称', 'warning'); return }
  const r = editId.value
    ? await api(`/api/suppliers/${editId.value}`, 'PUT', form.value)
    : await api('/api/suppliers', 'POST', form.value)
  if (r.error) { toast(r.error, 'danger'); return }
  showModal.value = false
  toast(editId.value ? '已更新' : '已添加')
  fetchSuppliers()
}

async function deleteS(s) {
  if (!confirm(`确定删除供应商「${s.name}」吗？`)) return
  const r = await api(`/api/suppliers/${s.id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast('已删除')
  fetchSuppliers()
}

onMounted(fetchSuppliers)
</script>

<template>
  <div>
    <div class="d-flex justify-content-end mb-2">
      <button class="btn btn-sm btn-primary btn-modern" @click="openAdd">
        <i class="bi bi-plus-lg"></i> 新增
      </button>
    </div>
    <LoadingSpinner v-if="loading" :center="true" />
    <div v-else class="table-responsive">
      <table class="table table-modern">
        <thead>
          <tr><th>名称</th><th>联系人</th><th>电话</th><th>创建时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-if="suppliers.length === 0">
            <td colspan="5"><EmptyState message="暂无供应商" /></td>
          </tr>
          <tr v-for="s in suppliers" :key="s.id">
            <td class="fw-medium">{{ s.name }}</td>
            <td class="text-muted small">{{ s.contact_person || '—' }}</td>
            <td class="text-muted small">{{ s.phone || '—' }}</td>
            <td class="text-muted small">{{ s.created_at || '—' }}</td>
            <td>
              <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-primary btn-sm-icon" @click="openEdit(s)" title="编辑">
                  <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger btn-sm-icon" @click="deleteS(s)" title="删除">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 完整字段 Modal -->
    <ModalDialog :show="showModal" :title="editId ? '编辑供应商' : '新增供应商'" @close="showModal = false">
      <div class="row g-2">
        <div class="col-12">
          <label class="form-label-modern">名称 <span class="text-danger">*</span></label>
          <input class="form-control" v-model="form.name" placeholder="供应商名称">
        </div>
        <div class="col-md-6">
          <label class="form-label-modern">联系人</label>
          <input class="form-control" v-model="form.contact_person" placeholder="联系人姓名">
        </div>
        <div class="col-md-6">
          <label class="form-label-modern">电话</label>
          <input class="form-control" v-model="form.phone" placeholder="联系电话">
        </div>
        <div class="col-12">
          <label class="form-label-modern">邮箱</label>
          <input class="form-control" v-model="form.email" placeholder="邮箱地址">
        </div>
        <div class="col-12">
          <label class="form-label-modern">地址</label>
          <input class="form-control" v-model="form.address" placeholder="公司地址">
        </div>
        <div class="col-12">
          <label class="form-label-modern">备注</label>
          <textarea class="form-control" v-model="form.notes" rows="2" placeholder="其他备注"></textarea>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-primary btn-modern" @click="save">保存</button>
        <button class="btn btn-secondary btn-modern" @click="showModal = false">取消</button>
      </template>
    </ModalDialog>
  </div>
</template>
