<script setup>
/**
 * UserManagementPanel — 用户管理面板
 * 从 AdminView 拆出，独立管理用户 CRUD、分页、搜索
 */
import { ref, computed, inject } from 'vue'
import { useApi } from '../../composables/useApi'
import { usePagination } from '../../composables/usePagination'
import { useDebounceSearch } from '../../composables/useDebounceSearch'
import ModalDialog from '../ModalDialog.vue'
import PaginationBar from '../PaginationBar.vue'
import LoadingSpinner from '../LoadingSpinner.vue'

const toast = inject('toast')
const { api } = useApi()

const users = ref([])
const loading = ref(true)

// 分页
const { currentPage, perPage, totalItems, totalPages, pageNumbers, goPage, setFetchFn } = usePagination({ perPageDefault: 20 })
setFetchFn(() => fetchUsers())

// 搜索
const { searchTerm, onInput, onCompositionStart, onCompositionEnd, clear: clearSearch } = useDebounceSearch(
  () => { currentPage.value = 1; fetchUsers() }
)

async function fetchUsers() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: currentPage.value, per_page: perPage.value })
    if (searchTerm.value) params.set('search', searchTerm.value)
    const data = await api(`/api/admin/users?${params}`)
    if (!data.error) {
      users.value = data.users || []
      totalItems.value = data.total || 0
    }
  } catch (e) {
    toast('加载用户失败', 'danger')
  } finally {
    loading.value = false
  }
}

// 新增用户
const showUserModal = ref(false)
const newUserForm = ref({ username: '', password: '', email: '', role: 'user' })

function openAddUser() {
  newUserForm.value = { username: '', password: '', email: '', role: 'user' }
  showUserModal.value = true
}
async function saveNewUser() {
  const f = newUserForm.value
  if (!f.username.trim()) { toast('请输入用户名', 'warning'); return }
  if (!f.password.trim() || f.password.trim().length < 8) { toast('密码至少8位', 'warning'); return }
  const r = await api('/api/admin/users', 'POST', {
    username: f.username.trim(), password: f.password.trim(),
    email: f.email.trim(), role: f.role,
  })
  if (r.error) { toast(r.error, 'danger'); return }
  showUserModal.value = false
  toast('用户已创建')
  fetchUsers()
}

// 改角色
async function toggleUserRole(user) {
  const newRole = user.role === 'admin' ? 'user' : 'admin'
  const r = await api(`/api/admin/users/${user.id}`, 'PUT', { role: newRole })
  if (r.error) { toast(r.error, 'danger'); return }
  user.role = newRole
  toast('已更新')
}

// 重置密码 Modal
const showPwModal = ref(false)
const pwTarget = ref(null)
const pwNew = ref('')
const pwConfirm = ref('')

function openResetPw(user) {
  pwTarget.value = user
  pwNew.value = ''
  pwConfirm.value = ''
  showPwModal.value = true
}
async function doResetPw() {
  if (pwNew.value.length < 8) { toast('密码至少8位', 'warning'); return }
  if (pwNew.value !== pwConfirm.value) { toast('两次密码不一致', 'warning'); return }
  const r = await api(`/api/admin/users/${pwTarget.value.id}/password`, 'PUT', { password: pwNew.value })
  if (r.error) { toast(r.error, 'danger'); return }
  showPwModal.value = false
  toast('密码已重置')
}

// 删除用户
async function deleteUser(user) {
  if (!confirm(`确定删除用户「${user.username}」吗？此操作不可撤销。`)) return
  const r = await api(`/api/admin/users/${user.id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast(r.message || '已删除')
  users.value = users.value.filter(u => u.id !== user.id)
  totalItems.value = Math.max(0, totalItems.value - 1)
}

fetchUsers()
</script>

<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-2">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <input
          :value="searchTerm"
          @input="onInput"
          @compositionstart="onCompositionStart"
          @compositionend="onCompositionEnd"
          class="form-control form-control-sm"
          placeholder="搜索用户名或邮箱..."
          style="max-width:260px"
        >
        <span class="text-muted small">共 {{ totalItems }} 个用户</span>
      </div>
      <div class="d-flex align-items-center gap-2">
        <select class="per-page-select" v-model.number="perPage" @change="currentPage = 1; fetchUsers()">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
        </select>
        <button class="btn btn-sm btn-primary btn-modern" @click="openAddUser">
          <i class="bi bi-plus-lg"></i> 新增用户
        </button>
      </div>
    </div>

    <LoadingSpinner v-if="loading" :center="true" text="加载中..." />
    <div v-else class="table-responsive">
      <table class="table table-modern">
        <thead>
          <tr>
            <th>用户名</th><th>邮箱</th><th>角色</th>
            <th>创建时间</th><th>上次登录</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="fw-medium">{{ u.username }}</td>
            <td class="text-muted small">{{ u.email || '—' }}</td>
            <td>
              <span class="badge" :class="u.role === 'admin' ? 'bg-primary' : 'bg-light text-dark'">
                {{ u.role === 'admin' ? '管理员' : '用户' }}
              </span>
            </td>
            <td class="text-muted small">{{ u.created_at || '—' }}</td>
            <td class="text-muted small">{{ u.last_login || '从未登录' }}</td>
            <td>
              <div class="d-flex gap-1">
                <button v-if="u.id !== 1" class="btn btn-sm btn-outline-warning btn-sm-icon"
                  @click="toggleUserRole(u)"
                  :title="u.role === 'admin' ? '降为普通用户' : '升为管理员'">
                  <i :class="u.role === 'admin' ? 'bi bi-arrow-down' : 'bi bi-arrow-up'"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary btn-sm-icon"
                  @click="openResetPw(u)" title="重置密码">
                  <i class="bi bi-key"></i>
                </button>
                <button v-if="u.role !== 'admin'" class="btn btn-sm btn-outline-danger btn-sm-icon"
                  @click="deleteUser(u)" title="删除用户">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :current-page="currentPage" :total-pages="totalPages" :page-numbers="pageNumbers" @go-page="goPage" />

    <!-- 新增用户 Modal -->
    <ModalDialog :show="showUserModal" title="新增用户" @close="showUserModal = false">
      <label class="form-label-modern">用户名 <span class="text-danger">*</span></label>
      <input class="form-control mb-2" v-model="newUserForm.username" placeholder="登录用户名">
      <label class="form-label-modern">密码 <span class="text-danger">*</span></label>
      <input class="form-control mb-2" type="password" v-model="newUserForm.password" placeholder="至少8位">
      <label class="form-label-modern">邮箱</label>
      <input class="form-control mb-2" v-model="newUserForm.email" placeholder="选填">
      <label class="form-label-modern">角色</label>
      <select class="form-select" v-model="newUserForm.role">
        <option value="user">普通用户</option>
        <option value="admin">管理员</option>
      </select>
      <template #footer>
        <button class="btn btn-primary btn-modern" @click="saveNewUser">创建</button>
        <button class="btn btn-secondary btn-modern" @click="showUserModal = false">取消</button>
      </template>
    </ModalDialog>

    <!-- 重置密码 Modal -->
    <ModalDialog :show="showPwModal" :title="`重置「${pwTarget?.username}」的密码`" @close="showPwModal = false">
      <label class="form-label-modern">新密码 <span class="text-danger">*</span></label>
      <input class="form-control mb-2" type="password" v-model="pwNew" placeholder="至少8位">
      <label class="form-label-modern">确认新密码 <span class="text-danger">*</span></label>
      <input class="form-control" type="password" v-model="pwConfirm" placeholder="再次输入新密码">
      <template #footer>
        <button class="btn btn-primary btn-modern" @click="doResetPw">确认重置</button>
        <button class="btn btn-secondary btn-modern" @click="showPwModal = false">取消</button>
      </template>
    </ModalDialog>
  </div>
</template>
