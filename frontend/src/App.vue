<script setup>
import { ref, computed, onMounted, watch, onUnmounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from './composables/useApi'
import ToastMessage from './components/ToastMessage.vue'
import ModalDialog from './components/ModalDialog.vue'

const { api, authToken, currentUser, registrationOpen, setToken, isLoggedIn, isAdmin } = useApi()
const router = useRouter()
const route = useRoute()

// ─── Toast ───────────────────────────────────────────────────
const toastRef = ref(null)
function toast(msg, type = 'success') { toastRef.value?.toast(msg, type) }
provide('toast', toast)

// ─── Sidebar ─────────────────────────────────────────────────
const showSidebar = computed(() => isLoggedIn() && route.name !== 'login')
const sidebarOpen = ref(false)
const sidebarCollapsed = ref(false)

function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value }
function closeSidebar() { sidebarOpen.value = false }
function toggleCollapse() { sidebarCollapsed.value = !sidebarCollapsed.value }

watch(() => route.name, () => { closeSidebar() })

// ─── Responsive: 移动端默认折叠（具名函数，便于 removeEventListener）──
function _onResize() {
  if (window.innerWidth < 768) sidebarCollapsed.value = true
}
onMounted(() => {
  if (window.innerWidth < 768) sidebarCollapsed.value = true
  window.addEventListener('resize', _onResize)
})
onUnmounted(() => window.removeEventListener('resize', _onResize))

// ─── Force re-render on same-route click ─────────────────────
const refreshKey = ref(0)
function navOrRefresh(tab) {
  if (route.name === tab.id) {
    refreshKey.value++
  } else {
    router.push({ name: tab.id })
  }
}

// ─── Tabs ─────────────────────────────────────────────────────
const allTabs = [
  { id: 'dashboard', label: '首页', icon: 'bi bi-speedometer2' },
  { id: 'quotes', label: '报价管理', icon: 'bi bi-file-earmark-text', badge: '+' },
  { id: 'admin', label: '管理', icon: 'bi bi-gear', adminOnly: true },
]
const tabs = computed(() => allTabs.filter(t => !t.adminOnly || isAdmin()))

// ─── Version ─────────────────────────────────────────────────
const version = ref('')

// ─── Profile Modal ────────────────────────────────────────────
const showProfile = ref(false)
const profileEmail = ref('')
const profileCurPw = ref('')
const profileNewPw = ref('')

function openProfile() {
  if (!currentUser.value) return
  profileEmail.value = currentUser.value.email || ''
  profileCurPw.value = ''
  profileNewPw.value = ''
  showProfile.value = true
}

async function saveProfile() {
  const newpw = profileNewPw.value.trim()
  // 客户端校验：修改密码时必须提供当前密码
  if (newpw) {
    if (!profileCurPw.value.trim()) { toast('请输入当前密码', 'warning'); return }
    if (newpw.length < 8) { toast('新密码至少8位', 'warning'); return }
  }
  const body = { email: profileEmail.value.trim() }
  if (newpw) {
    body.current_password = profileCurPw.value.trim()
    body.new_password = newpw
  }
  const r = await api('/api/auth/profile', 'PUT', body)
  if (r.user) {
    currentUser.value = r.user
    showProfile.value = false
    toast(r.message || '已更新')
  } else {
    toast(r.error || '修改失败', 'warning')
  }
}

// ─── Logout ───────────────────────────────────────────────────
function logout() {
  setToken('')
  currentUser.value = null
  router.push({ name: 'login' })
}

// ─── Watch token — 401 后重定向登录 ──────────────────────────
watch(authToken, (val) => {
  if (!val && route.name !== 'login') router.push({ name: 'login' })
})

// ─── Check session on mount ───────────────────────────────────
onMounted(async () => {
  if (!authToken.value) return
  try {
    const d = await api('/api/session')
    if (d.user) {
      currentUser.value = d.user
      registrationOpen.value = d.registration_open !== false
    }
  } catch (e) { /* offline — stay on current page */ }
  try {
    const v = await api('/api/version')
    version.value = v.version || ''
  } catch (e) { /* ignore */ }
})
</script>

<template>
  <div class="d-flex">
    <!-- Sidebar Overlay (mobile) -->
    <div v-if="showSidebar" class="sidebar-overlay" :class="{ show: sidebarOpen }" @click="closeSidebar"></div>

    <!-- Sidebar -->
    <div v-if="showSidebar" class="sidebar" :class="{ open: sidebarOpen, collapsed: sidebarCollapsed }">
      <div class="sidebar-logo" style="position:relative">
        <h5><i class="bi bi-file-text me-2"></i>报价系统</h5>
        <small>嵌入式开发报价管理平台</small>
        <button class="sidebar-collapse-btn" @click="toggleCollapse"
          :title="sidebarCollapsed ? '展开菜单' : '收起菜单'">
          <i :class="sidebarCollapsed ? 'bi bi-chevron-right' : 'bi bi-chevron-left'"></i>
        </button>
      </div>
      <div class="sidebar-nav">
        <template v-for="tab in tabs" :key="tab.id">
          <a class="nav-link" :class="{ active: route.name === tab.id }"
            href="#" @click.prevent="navOrRefresh(tab)">
            <i :class="tab.icon"></i> {{ tab.label }}
            <span v-if="tab.badge" class="badge"
              @click.stop="router.push({ name: 'newquote' })">{{ tab.badge }}</span>
          </a>
        </template>
        <hr style="border-color: rgba(255,255,255,.08); margin: .5rem 0;">
        <a class="nav-link" style="opacity:.6; font-size:.8rem; cursor:default">
          <i class="bi bi-info-circle"></i> <span>{{ version || 'v—' }}</span>
        </a>
      </div>
      <div v-if="currentUser" class="sidebar-user dropdown"
        style="border-top:1px solid rgba(255,255,255,.08);padding:.5rem">
        <button class="btn btn-sm btn-outline-light dropdown-toggle w-100" type="button"
          data-bs-toggle="dropdown" style="font-size:.75rem;text-align:left">
          <i class="bi bi-person-circle me-1"></i>
          <span class="sidebar-user-name">{{ currentUser.username }}</span>
        </button>
        <ul class="dropdown-menu" style="font-size:.82rem;min-width:140px">
          <li>
            <a class="dropdown-item" href="#" @click.prevent="openProfile">
              <i class="bi bi-person-gear me-2"></i>个人信息
            </a>
          </li>
          <li><hr class="dropdown-divider" style="margin:.25rem 0"></li>
          <li>
            <a class="dropdown-item text-danger" href="#" @click.prevent="logout">
              <i class="bi bi-box-arrow-right me-2"></i>退出
            </a>
          </li>
        </ul>
      </div>
    </div>

    <!-- Main Wrapper -->
    <div class="main-wrapper" :class="{ expanded: sidebarCollapsed }"
      :style="!showSidebar ? { marginLeft: '0' } : {}">
      <button v-if="showSidebar && !sidebarOpen"
        class="btn btn-link sidebar-toggle text-dark position-fixed p-0"
        @click="toggleSidebar"
        style="top:.8rem;left:.8rem;font-size:1.2rem;text-decoration:none;z-index:1040"
        aria-label="打开菜单">
        <i class="bi bi-list"></i>
      </button>
      <div class="main-content" :style="showSidebar && !sidebarOpen ? { paddingTop: '2.8rem' } : {}">
        <router-view v-slot="{ Component }" :key="refreshKey">
          <template v-if="Component">
            <component :is="Component" />
          </template>
        </router-view>
      </div>
    </div>

    <!-- Profile Modal -->
    <ModalDialog :show="showProfile" title="个人信息" @close="showProfile = false">
      <div class="mb-3">
        <label class="form-label small" for="profile-username">用户名</label>
        <input id="profile-username" class="form-control" :value="currentUser?.username || ''" disabled>
      </div>
      <div class="mb-3">
        <label class="form-label small" for="profile-role">角色</label>
        <input id="profile-role" class="form-control" :value="isAdmin() ? '管理员' : '普通用户'" disabled>
      </div>
      <div class="mb-3">
        <label class="form-label small" for="profile-email">邮箱</label>
        <input id="profile-email" class="form-control" v-model="profileEmail" placeholder="选填">
      </div>
      <hr>
      <div class="mb-2">
        <label class="form-label small" for="profile-curpw">
          当前密码 <span class="text-muted">（修改邮箱或密码时需验证）</span>
        </label>
        <input id="profile-curpw" class="form-control" type="password" v-model="profileCurPw">
      </div>
      <div class="mb-2">
        <label class="form-label small" for="profile-newpw">
          新密码 <span class="text-muted">（留空不修改，至少8位）</span>
        </label>
        <input id="profile-newpw" class="form-control" type="password" v-model="profileNewPw">
      </div>
      <template #footer>
        <button class="btn btn-primary btn-modern" @click="saveProfile">保存</button>
        <button class="btn btn-secondary btn-modern" @click="showProfile = false">取消</button>
      </template>
    </ModalDialog>

    <ToastMessage ref="toastRef" />
  </div>
</template>
