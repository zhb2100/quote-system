<script setup>
import { ref, inject, onMounted } from 'vue'
import { useApi } from '../../composables/useApi'
import ModalDialog from '../ModalDialog.vue'
import LoadingSpinner from '../LoadingSpinner.vue'
import EmptyState from '../EmptyState.vue'

const toast = inject('toast')
const { api } = useApi()

const salespersons = ref([])
const loading = ref(true)
const userAccounts = ref([])

async function fetchSalespersons() {
  loading.value = true
  try {
    const data = await api('/api/salespersons')
    if (!data.error) salespersons.value = data.salespersons || []
  } catch (e) {
    toast('加载业务员失败', 'danger')
  } finally {
    loading.value = false
  }
}

async function fetchUserAccounts() {
  try {
    // per_page=200 确保加载足够多的用户
    const data = await api('/api/admin/users?per_page=200')
    userAccounts.value = data.users || []
  } catch (e) { /* ignore */ }
}

function getUserName(userId) {
  if (!userId) return '—'
  const found = userAccounts.value.find(u => u.id === userId)
  return found ? found.username : '—'
}

// Modal
const showModal = ref(false)
const editId = ref(null)
const spName = ref('')
const spUserId = ref(null)

function openAdd() { editId.value = null; spName.value = ''; spUserId.value = null; showModal.value = true }
function openEdit(sp) { editId.value = sp.id; spName.value = sp.name; spUserId.value = sp.user_id; showModal.value = true }

async function save() {
  const name = spName.value.trim()
  if (!name) { toast('请输入姓名', 'warning'); return }
  const r = editId.value
    ? await api(`/api/salespersons/${editId.value}`, 'PUT', { name, user_id: spUserId.value })
    : await api('/api/salespersons', 'POST', { name, user_id: spUserId.value })
  if (r.error) { toast(r.error, 'danger'); return }
  showModal.value = false
  toast(editId.value ? '已更新' : '已添加')
  fetchSalespersons()
}

async function deleteSp(sp) {
  if (!confirm(`确定删除业务员「${sp.name}」吗？`)) return
  const r = await api(`/api/salespersons/${sp.id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast('已删除')
  fetchSalespersons()
}

onMounted(() => { fetchSalespersons(); fetchUserAccounts() })
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
        <thead><tr><th>姓名</th><th>关联账号</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-if="salespersons.length === 0">
            <td colspan="4"><EmptyState message="暂无业务员" /></td>
          </tr>
          <tr v-for="sp in salespersons" :key="sp.id">
            <td class="fw-medium">{{ sp.name }}</td>
            <td class="text-muted small">{{ getUserName(sp.user_id) }}</td>
            <td class="text-muted small">{{ sp.created_at || '—' }}</td>
            <td>
              <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-primary btn-sm-icon" @click="openEdit(sp)" title="编辑">
                  <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger btn-sm-icon" @click="deleteSp(sp)" title="删除">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ModalDialog :show="showModal" :title="editId ? '编辑业务员' : '新增业务员'" @close="showModal = false" size="sm">
      <label class="form-label-modern">姓名 <span class="text-danger">*</span></label>
      <input class="form-control mb-2" v-model="spName" placeholder="业务员姓名" @keyup.enter="save">
      <label class="form-label-modern">关联账号</label>
      <select class="form-select" v-model="spUserId">
        <option :value="null">不关联</option>
        <option v-for="u in userAccounts" :key="u.id" :value="u.id">{{ u.username }}</option>
      </select>
      <template #footer>
        <button class="btn btn-primary btn-modern" @click="save">保存</button>
        <button class="btn btn-secondary btn-modern" @click="showModal = false">取消</button>
      </template>
    </ModalDialog>
  </div>
</template>
