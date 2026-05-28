<script setup>
import { ref, inject } from 'vue'
import { useApi } from '../composables/useApi'
import UserManagementPanel from '../components/admin/UserManagementPanel.vue'
import SalespersonPanel from '../components/admin/SalespersonPanel.vue'
import SupplierPanel from '../components/admin/SupplierPanel.vue'
import LoginLogPanel from '../components/admin/LoginLogPanel.vue'

const toast = inject('toast')
const { api, registrationOpen } = useApi()
const activeTab = ref('users')

async function toggleRegistration() {
  const r = await api('/api/admin/registration', 'PUT', { registration_open: registrationOpen.value })
  if (r.error) {
    toast(r.error, 'danger')
    registrationOpen.value = !registrationOpen.value
  } else {
    toast(registrationOpen.value ? '注册已开放' : '注册已关闭')
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h5><i class="bi bi-gear"></i>系统管理</h5>
    </div>

    <!-- Tab 导航：解决原来单页滚动过长、功能耦合的问题 -->
    <div class="card-modern mb-3">
      <div class="d-flex gap-2 flex-wrap">
        <button class="btn btn-sm" :class="activeTab === 'users' ? 'btn-primary' : 'btn-outline-primary'" @click="activeTab = 'users'">用户管理</button>
        <button class="btn btn-sm" :class="activeTab === 'salespersons' ? 'btn-primary' : 'btn-outline-primary'" @click="activeTab = 'salespersons'">业务员管理</button>
        <button class="btn btn-sm" :class="activeTab === 'suppliers' ? 'btn-primary' : 'btn-outline-primary'" @click="activeTab = 'suppliers'">供应商管理</button>
        <button class="btn btn-sm" :class="activeTab === 'logs' ? 'btn-primary' : 'btn-outline-primary'" @click="activeTab = 'logs'">登录日志</button>
        <button class="btn btn-sm" :class="activeTab === 'registration' ? 'btn-primary' : 'btn-outline-primary'" @click="activeTab = 'registration'">注册控制</button>
      </div>
    </div>

    <div v-if="activeTab === 'registration'" class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-people text-primary me-2"></i>注册控制</div>
      <div class="d-flex align-items-center gap-3 py-1">
        <label class="switch">
          <input type="checkbox" v-model="registrationOpen" @change="toggleRegistration">
          <span class="slider"></span>
        </label>
        <span class="fw-medium">{{ registrationOpen ? '允许新用户注册' : '已关闭注册' }}</span>
        <small class="text-muted ms-auto">{{ registrationOpen ? '任何人可注册账号' : '仅管理员可创建用户' }}</small>
      </div>
    </div>

    <div v-show="activeTab === 'users'" class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-person-lines-fill text-primary me-2"></i>用户管理</div>
      <UserManagementPanel />
    </div>

    <div v-show="activeTab === 'salespersons'" class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-person-badge text-primary me-2"></i>业务员管理</div>
      <SalespersonPanel />
    </div>

    <div v-show="activeTab === 'suppliers'" class="card-modern mb-3">
      <div class="card-title-modern"><i class="bi bi-shop text-primary me-2"></i>供应商管理</div>
      <SupplierPanel />
    </div>

    <div v-show="activeTab === 'logs'" class="card-modern">
      <div class="card-title-modern"><i class="bi bi-journal-text text-primary me-2"></i>用户登录记录</div>
      <LoginLogPanel />
    </div>
  </div>
</template>
