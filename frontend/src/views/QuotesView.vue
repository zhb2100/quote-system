<script setup>
import { ref, onMounted, inject, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useApi, BASE_URL } from '../composables/useApi'
import { usePagination } from '../composables/usePagination'
import { useShortcuts } from '../composables/useShortcuts'
import MonthPicker from '../components/MonthPicker.vue'

const router = useRouter()
const toast = inject('toast')
const { api, isAdmin } = useApi()

const quotes = ref([])
const statusFilter = ref('')
const loading = ref(true)
const salespersonList = ref([])
const salespersonFilter = ref(null)
const supplierList = ref([])
const supplierFilter = ref(null)
const monthFilter = ref(null)
const eventDirectionFilter = ref('')
const sortField = ref('id')
const sortOrder = ref('desc')

function toggleSort(field) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'desc'
  }
  resetPage()
}

// ─── Search & Pagination ───
const searchTerm = ref('')
const { currentPage, perPage, totalItems, totalPages, pageNumbers, goPage, resetPage, setFetchFn } = usePagination({
  perPageDefault: 20,
})
setFetchFn(() => fetchQuotes())

const searchInput = ref(null)
useShortcuts({
  newItem: () => { if (isAdmin()) router.push({name:'newquote'}) },
  focusSearch: () => searchInput.value?.focus(),
})

// ─── IME composition ───
const isComposing = ref(false)
function onCompositionStart() { isComposing.value = true }
function onCompositionEnd(e) {
  isComposing.value = false
  debouncedSearch(e.target.value)
}

// ─── Debounced search ───
let searchTimer = null
function debouncedSearch(val) {
  if (isComposing.value) return
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    searchTerm.value = val
    resetPage()
  }, 500)
}
function clearSearch() {
  searchTerm.value = ''
  resetPage()
}

async function fetchQuotes() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: currentPage.value,
      per_page: perPage.value,
    })
    if (statusFilter.value) params.set('status', statusFilter.value)
    if (searchTerm.value) params.set('search', searchTerm.value)
    if (salespersonFilter.value !== null) params.set('salesperson_id', salespersonFilter.value)
    if (supplierFilter.value !== null) params.set('supplier_id', supplierFilter.value)
    if (monthFilter.value) params.set('month', monthFilter.value)
    if (eventDirectionFilter.value) params.set('event_direction', eventDirectionFilter.value)
    params.set('sort_by', sortField.value)
    params.set('sort_order', sortOrder.value)

    const data = await api(`/api/quotes?${params}`)
    if (!data.error) {
      quotes.value = data.quotes || []
      totalItems.value = data.total || 0
      await nextTick()
    }
  } catch (e) {
    toast('加载报价单失败', 'danger')
  } finally {
    loading.value = false
  }
}

// ─── Edit quote ───
function editQuote(id) {
  router.push({ name: 'newquote', query: { edit: id } })
}

// ─── Batch Delete ───
const selectedIds = ref(new Set())
const selectAll = ref(false)

function toggleSelectAll() {
  if (selectAll.value) {
    selectedIds.value = new Set(quotes.value.map(q => q.id))
  } else {
    selectedIds.value = new Set()
  }
}

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
  selectAll.value = s.size === quotes.value.length && quotes.value.length > 0
}

async function batchDelete() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  if (!confirm(`确定删除选中的 ${ids.length} 条报价单吗？`)) return

  const r = await api('/api/quotes/batch', 'DELETE', { ids })
  if (r.error) { toast(r.error, 'danger'); return }

  const msg = `已删除 ${r.deleted} 条`
  if (r.forbidden?.length) toast(`${msg}，${r.forbidden.length} 条无权限`, 'warning')
  else toast(msg, 'success')

  selectedIds.value = new Set()
  selectAll.value = false
  fetchQuotes()
}

async function deleteQuote(id) {
  if (!confirm('确定删除该报价单吗？')) return
  const r = await api(`/api/quotes/${id}`, 'DELETE')
  if (r.error) { toast(r.error, 'danger'); return }
  toast('已删除')
  selectedIds.value.delete(id)
  fetchQuotes()
}

function statusBadge(s) {
  return s || '—'
}

function statusClass(s) {
  const map = {
    '项目报价中': 'bg-info',
    '项目已报价未付款': 'bg-warning text-dark',
    '项目生产中': 'bg-primary',
    '项目完结': 'bg-success',
    '项目返工': 'bg-warning',
    '项目终止': 'bg-danger',
  }
  return map[s] || 'bg-info'
}

async function loadFilterOptions() {
  const [spRes, sRes] = await Promise.allSettled([
    api('/api/salespersons'),
    api('/api/suppliers'),
  ])
  if (spRes.status === 'fulfilled') {
    salespersonList.value = spRes.value.salespersons || []
  }
  if (sRes.status === 'fulfilled') {
    supplierList.value = sRes.value.suppliers || []
  }
}

onMounted(() => {
  loadFilterOptions()
  setTimeout(() => fetchQuotes(), 0)
})
</script>

<template>
  <div>
    <div class="page-header justify-content-between">
      <h5><i class="bi bi-file-text"></i>报价管理</h5>
      <button class="btn btn-primary btn-modern" @click="router.push({name:'newquote'})">
        <i class="bi bi-plus-lg"></i> 新建报价单
      </button>
    </div>

    <div class="card-modern">
      <div class="d-flex align-items-center gap-2 flex-wrap mb-3">
        <div class="input-group input-group-sm" style="width:200px">
          <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
          <input type="text" class="form-control border-start-0" placeholder="搜索订单号... (/)"
            ref="searchInput"
            :value="searchTerm"
            @input="debouncedSearch($event.target.value)"
            @compositionstart="onCompositionStart"
            @compositionend="onCompositionEnd">
          <button v-if="searchTerm" class="btn btn-outline-secondary" type="button" @click="clearSearch">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
        <select class="form-select form-select-sm d-inline-block w-auto" v-model="statusFilter" @change="resetPage()">
          <option value="">全部状态</option>
          <option value="项目报价中">项目报价中</option>
          <option value="项目已报价未付款">项目已报价未付款</option>
          <option value="项目生产中">项目生产中</option>
          <option value="项目完结">项目完结</option>
          <option value="项目返工">项目返工</option>
          <option value="项目终止">项目终止</option>
        </select>
        <MonthPicker v-model="monthFilter" />
        <select class="form-select form-select-sm d-inline-block w-auto" v-model="salespersonFilter" @change="resetPage()" style="min-width:100px">
          <option :value="null">全部业务员</option>
          <option v-for="s in salespersonList" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <select class="form-select form-select-sm d-inline-block w-auto" v-model="supplierFilter" @change="resetPage()" style="min-width:100px">
          <option :value="null">全部供应商</option>
          <option v-for="s in supplierList" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <select class="form-select form-select-sm d-inline-block w-auto" v-model="eventDirectionFilter" @change="resetPage()" style="min-width:130px">
          <option value="">全部接收方</option>
          <option value="客户→供应商">客户→供应商</option>
          <option value="供应商→客户">供应商→客户</option>
        </select>
      </div>

      <!-- Batch action bar -->
      <div v-if="selectedIds.size > 0" class="d-flex align-items-center gap-2 p-2 rounded mb-3" style="position:sticky;top:0;z-index:10;background:var(--primary);color:#fff">
        <i class="bi bi-check2-square me-1"></i>
        <span class="small fw-medium">已选 {{ selectedIds.size }} 条报价单</span>
        <button class="btn btn-sm btn-light btn-modern ms-2" @click="batchDelete">
          <i class="bi bi-trash"></i> 批量删除
        </button>
        <button class="btn btn-sm btn-outline-light btn-modern" @click="selectedIds = new Set(); selectAll = false">
          取消选择
        </button>
      </div>

      <div v-if="loading" class="text-center py-5">
        <div class="spinner-border text-primary" role="status"></div>
      </div>

      <div v-else class="table-responsive">
        <table class="table table-modern">
          <thead>
            <tr>
              <th style="width:36px">
                <input type="checkbox" class="form-check-input" v-model="selectAll" @change="toggleSelectAll">
              </th>
              <th style="cursor:pointer" @click="toggleSort('title')">
                编号 <i :class="sortField==='title' ? (sortOrder==='asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill') : 'bi-caret-down'"></i>
              </th>
              <th>供应商</th>
              <th>业务员</th>
              <th>状态</th>
              <th class="d-none d-md-table-cell" style="cursor:pointer" @click="toggleSort('order_start')">
                起始 <i :class="sortField==='order_start' ? (sortOrder==='asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill') : 'bi-caret-down'"></i>
              </th>
              <th class="d-none d-md-table-cell">完成</th>
              <th class="d-none d-lg-table-cell">项目个类</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="quotes.length === 0">
              <td colspan="9"><div class="empty-state"><i class="bi bi-inbox"></i><p>暂无报价单</p></div></td>
            </tr>
            <tr v-for="q in quotes" :key="q.id">
              <td>
                <input type="checkbox" class="form-check-input" :checked="selectedIds.has(q.id)" @change="toggleSelect(q.id)">
              </td>
              <td>
                <span class="fw-medium" style="cursor:pointer;color:var(--primary)" @click="router.push({name:'quotes',params:{id:q.id}})">{{ q.title || '未命名' }}</span>
              </td>
              <td>{{ q.supplier_name || '—' }}</td>
              <td>{{ q.salesperson_name || '—' }}</td>
              <td>
                <span class="badge" :class="statusClass(q.status)" style="font-size:.75rem;padding:.2rem .5rem">{{ statusBadge(q.status) }}</span>
              </td>
              <td class="d-none d-md-table-cell">{{ q.order_start || '—' }}</td>
              <td class="d-none d-md-table-cell">{{ q.order_end || '—' }}</td>
              <td class="d-none d-lg-table-cell">{{ q.project_category || '—' }}</td>
              <td>
                <div class="d-flex flex-wrap gap-1">
                  <button class="btn btn-sm btn-outline-info btn-sm-icon" @click="router.push({name:'project-detail',params:{id:q.id}})" title="详情">
                    <i class="bi bi-kanban"></i>
                  </button>

                  <button class="btn btn-sm btn-outline-danger btn-sm-icon" @click="deleteQuote(q.id)" title="删除">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <nav v-if="totalPages > 1" class="mt-3">
        <ul class="pagination pagination-modern justify-content-center mb-0">
          <li class="page-item" :class="{ disabled: currentPage <= 1 }">
            <a class="page-link" @click="goPage(1)" title="首页"><i class="bi bi-chevron-double-left"></i></a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage <= 1 }">
            <a class="page-link" @click="goPage(currentPage - 1)">上一页</a>
          </li>
          <li v-for="p in pageNumbers" :key="p" class="page-item" :class="{ active: p === currentPage }">
            <a class="page-link" @click="goPage(p)">{{ p }}</a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage >= totalPages }">
            <a class="page-link" @click="goPage(currentPage + 1)">下一页</a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage >= totalPages }">
            <a class="page-link" @click="goPage(totalPages)" title="末页"><i class="bi bi-chevron-double-right"></i></a>
          </li>
        </ul>
      </nav>
    </div>
  </div>
</template>
