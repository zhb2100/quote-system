<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useApi } from '../composables/useApi'

const toast = inject('toast')
const { api } = useApi()

// ─── Registration toggle ───
const registrationOpen = ref(true)

async function toggleRegistration() {
  const r = await api('/api/admin/registration', 'PUT', {
    registration_open: registrationOpen.value
  })
  if (r.error) {
    toast(r.error, 'danger')
    registrationOpen.value = !registrationOpen.value
  } else {
    toast(registrationOpen.value ? '注册已开放' : '注册已关闭')
  }
}

// ─── Users ───
const users = ref([])
const userSearch = ref('')
const userCurrentPage = ref(1)
const userPerPage = ref(20)
const userTotal = ref(0)
const userTotalPages = computed(() => Math.max(1, Math.ceil(userTotal.value / userPerPage.value)))
const loadingUsers = ref(true)

// ─── User pagination pages ───
const userPageNumbers = computed(() => {
  const total = userTotalPages.value
  if (total <= 1) return []
  const half = 3
  let start = Math.max(1, userCurrentPage.value - half)
  let end = Math.min(total, userCurrentPage.value + half)
  if (start === 1) end = Math.min(total, start + 6)
  else if (end === total) start = Math.max(1, end - 6)
  const pages = []
  for (let p = start; p <= end; p++) pages.push(p)
  return pages
})

function userGoPage(p) {
  if (p < 1 || p > userTotalPages.value) return
  userCurrentPage.value = p
  fetchUsers()
}

// Debounced user search
let userSearchTimer = null
function onUserSearch(val) {
  clearTimeout(userSearchTimer)
  userSearchTimer = setTimeout(() => {
    userSearch.value = val
    userCurrentPage.value = 1
    fetchUsers()
  }, 400)
}

async function fetchUsers() {
  try {
    const params = new URLSearchParams({
      page: userCurrentPage.value,
      per_page: userPerPage.value,
    })
    if (userSearch.value) params.set('search', userSearch.value)
    const data = await api(`/api/admin/users?${params}`)
    if (!data.error) {
      users.value = data.users || []
      userTotal.value = data.total || 0
    }
  } catch (e) {
    toast('加载用户失败', 'danger')
  } finally {
    loadingUsers.value = false
  }
}

async function toggleUserRole(user) {
  const newRole = user.role === 'admin' ? 'user' : 'admin'
  const r = await api(`/api/admin/users/${user.id}`, 'PUT', { role: newRole })
  if (r.error) { toast(r.error, 'danger'); return }
  user.role = newRole
  toast('已更新')
}

async function resetPassword(user) {
  const pw = prompt(`为 ${user.username} 设置新密码（至少3位）：`)
  if (!pw) return
  const r = await api(`/api/admin/users/${user.id}/password`, 'PUT', { password: pw })
  if (r.error) { toast(r.error, 'danger'); return }
  toast('密码已重置')
}

async function deleteUser(user) {
  if (!confirm(`确定删除用户「${user.username}」吗？此操作不可撤销。`)) return
  const r = await api(`/api/admin/users/${user.id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast(r.message || '已删除')
  users.value = users.value.filter(u => u.id !== user.id)
}

// ─── Settings ───
const settings = ref({})
async function fetchSettings() {
  try {
    const data = await api('/api/admin/settings')
    if (!data.error) {
      settings.value = data.settings || {}
      registrationOpen.value = data.settings?.registration_open === 'true'
    }
  } catch (e) { /* ignore */ }
}

// ─── Login Logs ───
const loginLogs = ref([])
const loginLogCurrentPage = ref(1)
const loginLogPerPage = ref(20)
const loginLogTotal = ref(0)
const loginLogTotalPages = computed(() => Math.max(1, Math.ceil(loginLogTotal.value / loginLogPerPage.value)))
const loadingLoginLogs = ref(true)

const loginLogPageNumbers = computed(() => {
  const total = loginLogTotalPages.value
  if (total <= 1) return []
  const half = 3
  let start = Math.max(1, loginLogCurrentPage.value - half)
  let end = Math.min(total, loginLogCurrentPage.value + half)
  if (start === 1) end = Math.min(total, start + 6)
  else if (end === total) start = Math.max(1, end - 6)
  const pages = []
  for (let p = start; p <= end; p++) pages.push(p)
  return pages
})

function loginLogGoPage(p) {
  if (p < 1 || p > loginLogTotalPages.value) return
  loginLogCurrentPage.value = p
  fetchLoginLogs()
}

async function fetchLoginLogs() {
  loadingLoginLogs.value = true
  try {
    const params = new URLSearchParams({
      page: loginLogCurrentPage.value,
      per_page: loginLogPerPage.value,
    })
    const data = await api(`/api/admin/login-logs?${params}`)
    if (!data.error) {
      loginLogs.value = data.logs || []
      loginLogTotal.value = data.total || 0
    }
  } catch (e) {
    toast('加载登录记录失败', 'danger')
  } finally {
    loadingLoginLogs.value = false
  }
}

// ─── Salespersons ───
const salespersons = ref([])
const showSpModal = ref(false)
const spEditId = ref(null)
const spName = ref('')
const spUserId = ref(null)
const userAccounts = ref([])
const loadingSp = ref(true)

async function fetchSalespersons() {
  loadingSp.value = true
  try {
    const data = await api('/api/salespersons')
    if (!data.error) salespersons.value = data.salespersons || []
  } catch (e) { toast('加载业务员失败', 'danger') }
  finally { loadingSp.value = false }
}

async function fetchUserAccounts() {
  try {
    const data = await api('/api/admin/users')
    userAccounts.value = data.users || []
  } catch (e) { /* ignore */ }
}

function openAddSp() {
  spEditId.value = null
  spName.value = ''
  spUserId.value = null
  showSpModal.value = true
}

function openEditSp(sp) {
  spEditId.value = sp.id
  spName.value = sp.name
  spUserId.value = sp.user_id
  showSpModal.value = true
}

async function saveSp() {
  const name = spName.value.trim()
  if (!name) { toast('请输入姓名', 'warning'); return }
  const body = { name, user_id: spUserId.value }
  let r
  if (spEditId.value) {
    r = await api(`/api/salespersons/${spEditId.value}`, 'PUT', body)
  } else {
    r = await api('/api/salespersons', 'POST', body)
  }
  if (r.error) { toast(r.error, 'danger'); return }
  showSpModal.value = false
  toast(spEditId.value ? '已更新' : '已添加')
  fetchSalespersons()
}

async function deleteSp(sp) {
  if (!confirm(`确定删除业务员「${sp.name}」吗？`)) return
  const r = await api(`/api/salespersons/${sp.id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast('已删除')
  fetchSalespersons()
}

function getUserName(userId) {
  if (!userId) return '—'
  const found = userAccounts.value.find(u => u.id === userId)
  return found ? found.username : '—'
}

// ─── Suppliers ───
const supplierList = ref([])
const showSModal = ref(false)
const sEditId = ref(null)
const sName = ref('')
const loadingS = ref(true)

async function fetchSuppliers() {
  loadingS.value = true
  try {
    const data = await api('/api/suppliers')
    if (!data.error) supplierList.value = data.suppliers || []
  } catch (e) { toast('加载供应商失败', 'danger') }
  finally { loadingS.value = false }
}

function openAddS() {
  sEditId.value = null; sName.value = ''; showSModal.value = true
}

function openEditS(s) {
  sEditId.value = s.id; sName.value = s.name; showSModal.value = true
}

async function saveS() {
  const name = sName.value.trim()
  if (!name) { toast('请输入名称', 'warning'); return }
  const body = { name }
  let r
  if (sEditId.value) {
    r = await api(`/api/suppliers/${sEditId.value}`, 'PUT', body)
  } else {
    r = await api('/api/suppliers', 'POST', body)
  }
  if (r.error) { toast(r.error, 'danger'); return }
  showSModal.value = false
  toast(sEditId.value ? '已更新' : '已添加')
  fetchSuppliers()
}

async function deleteS(s) {
  if (!confirm(`确定删除供应商「${s.name}」吗？`)) return
  const r = await api(`/api/suppliers/${s.id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast('已删除')
  fetchSuppliers()
}

onMounted(() => {
  fetchUsers()
  fetchSettings()
  fetchLoginLogs()
  fetchSalespersons()
  fetchUserAccounts()
  fetchSuppliers()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h5><i class="bi bi-gear"></i>系统管理</h5>
    </div>

    <!-- Registration -->
    <div class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-people text-primary"></i>注册控制</div>
      <div class="d-flex align-items-center gap-3 py-1">
        <label class="switch">
          <input type="checkbox" v-model="registrationOpen" @change="toggleRegistration">
          <span class="slider"></span>
        </label>
        <span class="fw-medium">{{ registrationOpen ? '允许新用户注册' : '已关闭注册' }}</span>
        <small class="text-muted ms-auto">{{ registrationOpen ? '任何人可注册账号' : '仅管理员可创建用户' }}</small>
      </div>
    </div>

    <!-- Users -->
    <div class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-person-lines-fill text-primary"></i>用户管理</div>
      <div v-if="loadingUsers" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <div v-else class="table-responsive">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="d-flex align-items-center gap-2">
            <input :value="userSearch" @input="onUserSearch($event.target.value)" class="form-control form-control-sm" placeholder="搜索用户名或邮箱..." style="max-width:260px">
            <span v-if="!loadingUsers" class="text-muted flex-shrink-0" style="font-size:.82rem;white-space:nowrap">共 {{ userTotal }} 个用户</span>
          </div>
          <select class="per-page-select" v-model.number="userPerPage" @change="userCurrentPage = 1; fetchUsers()">
            <option :value="10">10条/页</option>
            <option :value="20">20条/页</option>
            <option :value="50">50条/页</option>
            <option :value="100">100条/页</option>
          </select>
        </div>
        <table class="table table-modern">
          <thead>
            <tr>
              <th>用户名</th>
              <th>邮箱</th>
              <th>角色</th>
              <th>创建时间</th>
              <th>上次登录</th>
              <th>操作</th>
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
                  <button v-if="u.id !== 1" class="btn btn-sm btn-outline-warning btn-sm-icon" @click="toggleUserRole(u)"
                    :title="u.role === 'admin' ? '降为普通用户' : '升为管理员'">
                    <i :class="u.role === 'admin' ? 'bi bi-arrow-down' : 'bi bi-arrow-up'"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-secondary btn-sm-icon" @click="resetPassword(u)" title="重置密码">
                    <i class="bi bi-key"></i>
                  </button>
                  <button v-if="u.role !== 'admin'" class="btn btn-sm btn-outline-danger btn-sm-icon" @click="deleteUser(u)" title="删除用户">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <!-- User pagination -->
        <nav v-if="userTotalPages > 1" class="mt-3">
          <ul class="pagination pagination-modern justify-content-center mb-0">
            <li class="page-item" :class="{ disabled: userCurrentPage <= 1 }">
              <a class="page-link" @click="userGoPage(1)" title="首页"><i class="bi bi-chevron-double-left"></i></a>
            </li>
            <li class="page-item" :class="{ disabled: userCurrentPage <= 1 }">
              <a class="page-link" @click="userGoPage(userCurrentPage - 1)">上一页</a>
            </li>
            <li v-for="p in userPageNumbers" :key="p" class="page-item" :class="{ active: p === userCurrentPage }">
              <a class="page-link" @click="userGoPage(p)">{{ p }}</a>
            </li>
            <li class="page-item" :class="{ disabled: userCurrentPage >= userTotalPages }">
              <a class="page-link" @click="userGoPage(userCurrentPage + 1)">下一页</a>
            </li>
            <li class="page-item" :class="{ disabled: userCurrentPage >= userTotalPages }">
              <a class="page-link" @click="userGoPage(userTotalPages)" title="末页"><i class="bi bi-chevron-double-right"></i></a>
            </li>
          </ul>
        </nav>
      </div>
    </div>

    <!-- Salespersons -->
    <div class="card-modern mb-3">
      <div class="card-title-modern d-flex justify-content-between align-items-center">
        <span><i class="bi bi-person-badge text-primary"></i>业务员管理</span>
        <button class="btn btn-sm btn-primary btn-modern" @click="openAddSp"><i class="bi bi-plus-lg"></i> 新增</button>
      </div>
      <div v-if="loadingSp" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <div v-else class="table-responsive">
        <table class="table table-modern">
          <thead>
            <tr><th>姓名</th><th>关联账号</th><th>创建时间</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-if="salespersons.length === 0">
              <td colspan="4"><div class="empty-state"><i class="bi bi-inbox"></i><p>暂无业务员</p></div></td>
            </tr>
            <tr v-for="sp in salespersons" :key="sp.id">
              <td class="fw-medium">{{ sp.name }}</td>
              <td class="text-muted small">{{ getUserName(sp.user_id) }}</td>
              <td class="text-muted small">{{ sp.created_at || '—' }}</td>
              <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-sm btn-outline-primary btn-sm-icon" @click="openEditSp(sp)" title="编辑">
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
    </div>

    <!-- Modal -->
    <Teleport to="body">
      <div v-if="showSpModal" class="modal-backdrop show" @click="showSpModal = false"></div>
      <div v-if="showSpModal" class="modal d-block modern-modal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered" style="max-width:360px">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">{{ spEditId ? '编辑业务员' : '新增业务员' }}</h5>
              <button type="button" class="btn-close" @click="showSpModal = false"></button>
            </div>
            <div class="modal-body">
              <label class="form-label-modern">姓名 <span class="text-danger">*</span></label>
              <input class="form-control" v-model="spName" placeholder="业务员姓名" @keyup.enter="saveSp">
              <label class="form-label-modern mt-2">关联账号</label>
              <select class="form-select" v-model="spUserId">
                <option :value="null">不关联</option>
                <option v-for="u in userAccounts" :key="u.id" :value="u.id">{{ u.username }}</option>
              </select>
            </div>
            <div class="modal-footer">
              <button class="btn btn-primary btn-modern" @click="saveSp">保存</button>
              <button class="btn btn-secondary btn-modern" @click="showSpModal = false">取消</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Suppliers -->
    <div class="card-modern mb-3">
      <div class="card-title-modern d-flex justify-content-between align-items-center">
        <span><i class="bi bi-shop text-primary"></i>供应商管理</span>
        <button class="btn btn-sm btn-primary btn-modern" @click="openAddS"><i class="bi bi-plus-lg"></i> 新增</button>
      </div>
      <div v-if="loadingS" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <div v-else class="table-responsive">
        <table class="table table-modern">
          <thead>
            <tr><th>名称</th><th>创建时间</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-if="supplierList.length === 0">
              <td colspan="3"><div class="empty-state"><i class="bi bi-inbox"></i><p>暂无供应商</p></div></td>
            </tr>
            <tr v-for="s in supplierList" :key="s.id">
              <td class="fw-medium">{{ s.name }}</td>
              <td class="text-muted small">{{ s.created_at || '—' }}</td>
              <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-sm btn-outline-primary btn-sm-icon" @click="openEditS(s)" title="编辑"><i class="bi bi-pencil"></i></button>
                  <button class="btn btn-sm btn-outline-danger btn-sm-icon" @click="deleteS(s)" title="删除"><i class="bi bi-trash"></i></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Supplier Modal -->
    <Teleport to="body">
      <div v-if="showSModal" class="modal-backdrop show" @click="showSModal = false"></div>
      <div v-if="showSModal" class="modal d-block modern-modal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered" style="max-width:360px">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">{{ sEditId ? '编辑供应商' : '新增供应商' }}</h5>
              <button type="button" class="btn-close" @click="showSModal = false"></button>
            </div>
            <div class="modal-body">
              <label class="form-label-modern">名称 <span class="text-danger">*</span></label>
              <input class="form-control" v-model="sName" placeholder="供应商名称" @keyup.enter="saveS">
            </div>
            <div class="modal-footer">
              <button class="btn btn-primary btn-modern" @click="saveS">保存</button>
              <button class="btn btn-secondary btn-modern" @click="showSModal = false">取消</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Login Logs -->
    <div class="card-modern">
      <div class="card-title-modern"><i class="bi bi-journal-text text-primary"></i>用户登录记录</div>
      <div v-if="loadingLoginLogs" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <div v-else class="table-responsive">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span v-if="!loadingLoginLogs" class="text-muted" style="font-size:.82rem">共 {{ loginLogTotal }} 条记录</span>
          <select class="per-page-select" v-model.number="loginLogPerPage" @change="loginLogCurrentPage = 1; fetchLoginLogs()">
            <option :value="10">10条/页</option>
            <option :value="20">20条/页</option>
            <option :value="50">50条/页</option>
          </select>
        </div>
        <table class="table table-modern">
          <thead>
            <tr>
              <th>用户名</th>
              <th>IP 地址</th>
              <th>区域</th>
              <th>User-Agent</th>
              <th>登录时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loginLogs.length === 0">
              <td colspan="5"><div class="empty-state"><i class="bi bi-inbox"></i><p>暂无登录记录</p></div></td>
            </tr>
            <tr v-for="log in loginLogs" :key="log.id">
              <td class="fw-medium">{{ log.username }}</td>
              <td class="text-muted small">{{ log.ip_address || '—' }}</td>
              <td>{{ log.region || '—' }}</td>
              <td class="td-name" style="max-width:200px;font-size:.75rem" :title="log.user_agent">{{ log.user_agent || '—' }}</td>
              <td class="text-muted small">{{ log.created_at }}</td>
            </tr>
          </tbody>
        </table>
        <nav v-if="loginLogTotalPages > 1" class="mt-3">
          <ul class="pagination pagination-modern justify-content-center mb-0">
            <li class="page-item" :class="{ disabled: loginLogCurrentPage <= 1 }">
              <a class="page-link" @click="loginLogGoPage(1)" title="首页"><i class="bi bi-chevron-double-left"></i></a>
            </li>
            <li class="page-item" :class="{ disabled: loginLogCurrentPage <= 1 }">
              <a class="page-link" @click="loginLogGoPage(loginLogCurrentPage - 1)">上一页</a>
            </li>
            <li v-for="p in loginLogPageNumbers" :key="p" class="page-item" :class="{ active: p === loginLogCurrentPage }">
              <a class="page-link" @click="loginLogGoPage(p)">{{ p }}</a>
            </li>
            <li class="page-item" :class="{ disabled: loginLogCurrentPage >= loginLogTotalPages }">
              <a class="page-link" @click="loginLogGoPage(loginLogCurrentPage + 1)">下一页</a>
            </li>
            <li class="page-item" :class="{ disabled: loginLogCurrentPage >= loginLogTotalPages }">
              <a class="page-link" @click="loginLogGoPage(loginLogTotalPages)" title="末页"><i class="bi bi-chevron-double-right"></i></a>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  </div>
</template>
