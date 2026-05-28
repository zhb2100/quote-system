<script setup>
import { ref, inject } from 'vue'
import { useApi } from '../../composables/useApi'
import { usePagination } from '../../composables/usePagination'
import PaginationBar from '../PaginationBar.vue'
import LoadingSpinner from '../LoadingSpinner.vue'

const toast = inject('toast')
const { api } = useApi()

const loginLogs = ref([])
const loading = ref(true)

const { currentPage, perPage, totalItems, totalPages, pageNumbers, goPage, setFetchFn } = usePagination({ perPageDefault: 20 })
setFetchFn(() => fetchLogs())

async function fetchLogs() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: currentPage.value, per_page: perPage.value })
    const data = await api(`/api/admin/login-logs?${params}`)
    if (!data.error) {
      loginLogs.value = data.logs || []
      totalItems.value = data.total || 0
    }
  } catch (e) {
    toast('加载登录记录失败', 'danger')
  } finally {
    loading.value = false
  }
}

fetchLogs()
</script>

<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-2">
      <span class="text-muted small">共 {{ totalItems }} 条记录</span>
      <select class="per-page-select" v-model.number="perPage" @change="currentPage = 1; fetchLogs()">
        <option :value="10">10条/页</option>
        <option :value="20">20条/页</option>
        <option :value="50">50条/页</option>
      </select>
    </div>
    <LoadingSpinner v-if="loading" :center="true" />
    <div v-else class="table-responsive">
      <table class="table table-modern">
        <thead>
          <tr><th>用户名</th><th>IP 地址</th><th>区域</th><th>User-Agent</th><th>登录时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="loginLogs.length === 0">
            <td colspan="5" class="text-center text-muted py-3">暂无登录记录</td>
          </tr>
          <tr v-for="log in loginLogs" :key="log.id">
            <td class="fw-medium">{{ log.username }}</td>
            <td class="text-muted small">{{ log.ip_address || '—' }}</td>
            <td>{{ log.region || '—' }}</td>
            <td class="text-muted" style="max-width:200px;font-size:.75rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="log.user_agent">
              {{ log.user_agent || '—' }}
            </td>
            <td class="text-muted small">{{ log.created_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :current-page="currentPage" :total-pages="totalPages" :page-numbers="pageNumbers" @go-page="goPage" />
  </div>
</template>
