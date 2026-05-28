<script setup>
import { ref, reactive, computed, watch, inject, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'
import { useQuoteStatus } from '../composables/useQuoteStatus'
import QuoteFormFields from '../components/quote/QuoteFormFields.vue'
import ModalDialog from '../components/ModalDialog.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const router = useRouter()
const route = useRoute()
const toast = inject('toast')
const { api, isAdmin } = useApi()
const { statusColor } = useQuoteStatus()

const quote = ref(null)
const loading = ref(true)
const patching = ref(false)

// 主线流程步骤（不含返工/终止，它们是旁支状态）
const FLOW_STEPS = ['项目报价中', '项目已报价未付款', '项目生产中', '项目完结']

const canTerminate = computed(() => quote.value && quote.value.status !== '项目终止')

const nextBtn = computed(() => {
  if (!quote.value) return ''
  if (quote.value.status === '项目完结' || quote.value.status === '项目终止') return ''
  const ns = (quote.value.next_statuses || []).filter(s => s !== '项目终止')
  return ns[0] || ''
})

// ─── 步骤节点样式计算（合并为一次遍历，避免重复调用）──────────
const stepStyles = computed(() => {
  if (!quote.value) return {}
  return Object.fromEntries(FLOW_STEPS.map(s => {
    const isCurrent = s === quote.value.status
    const isNext = (quote.value.next_statuses || []).includes(s)
    const color = statusColor(s)
    return [s, {
      border:     `3px solid ${isCurrent ? color : isNext ? '#ced4da' : '#e9ecef'}`,
      background: isCurrent ? color : isNext ? '#fff' : '#f8f9fa',
      color:      isCurrent ? '#fff' : isNext ? color : '#adb5bd',
      animation:  isCurrent ? 'stepPulse 2s ease-in-out infinite' : 'none',
    }]
  }))
})

function stepLabelStyle(s) {
  if (!quote.value) return {}
  return {
    fontWeight: s === quote.value.status ? '700' : '400',
    color: s === quote.value.status ? '#333' : '#999',
    fontSize: '.72rem',
  }
}

// ─── 加载报价单 ───────────────────────────────────────────────
async function loadQuote() {
  loading.value = true
  try {
    const data = await api(`/api/quotes/${route.params.id}`)
    if (data.error) { toast(data.error, 'danger'); return }
    quote.value = data.quote
  } catch (e) {
    toast('加载失败', 'danger')
  } finally {
    loading.value = false
  }
}

// ─── 状态变更 ─────────────────────────────────────────────────
async function _patchStatus(newStatus, confirmMsg) {
  if (!confirm(confirmMsg)) return
  patching.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/status`, 'PATCH', { status: newStatus })
    if (r.error) { toast(r.error, 'danger'); return }
    await loadQuote()
    fetchLogs()
    toast('状态已更新')
  } catch (e) {
    toast('操作失败', 'danger')
  } finally {
    patching.value = false
  }
}
const advanceStatus = () =>
  nextBtn.value && _patchStatus(nextBtn.value, `确定将状态从「${quote.value.status}」改为「${nextBtn.value}」吗？`)
const startRework = () =>
  _patchStatus('项目返工', '确定将项目状态改为「项目返工」吗？')
const restartProject = () =>
  _patchStatus('项目报价中', '确定重启该项目吗？将回到「项目报价中」状态')
const terminateProject = () =>
  _patchStatus('项目终止', '确定终止该项目吗？')

// ─── 状态日志 ─────────────────────────────────────────────────
const showLogs = ref(false)
const statusLogs = ref([])
const loadingLogs = ref(false)

async function fetchLogs() {
  if (!quote.value) return
  loadingLogs.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/logs`)
    statusLogs.value = r.logs || []
  } catch (e) { /* ignore */ }
  finally { loadingLogs.value = false }
}

function toggleLogs() {
  showLogs.value = !showLogs.value
  if (showLogs.value && !statusLogs.value.length) fetchLogs()
}

// ─── 交流记录 ─────────────────────────────────────────────────
const quoteEvents = ref([])
const loadingEvents = ref(true)   // 初始为 true，避免空状态闪烁
const showEventModal = ref(false)
const eventContent = ref('')
const eventDirection = ref('客户→供应商')
const savingEvent = ref(false)

async function fetchEvents() {
  if (!quote.value) return
  loadingEvents.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/events`)
    quoteEvents.value = r.events || []
  } catch (e) { /* ignore */ }
  finally { loadingEvents.value = false }
}

function openEventModal() {
  eventContent.value = ''
  eventDirection.value = '客户→供应商'
  showEventModal.value = true
}

async function saveEvent() {
  const content = eventContent.value.trim()
  if (!content) { toast('请输入内容', 'warning'); return }
  savingEvent.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/events`, 'POST',
      { content, direction: eventDirection.value })
    if (r.error) { toast(r.error, 'danger'); return }
    showEventModal.value = false
    toast('已添加')
    await fetchEvents()
  } catch (e) {
    toast('保存失败', 'danger')
  } finally {
    savingEvent.value = false }
}

// ─── 内联编辑 ─────────────────────────────────────────────────
const editing = ref(false)
const editForm = ref({ title: '', supplier_id: null, salesperson_id: null, order_start: '', order_end: '', project_category: [], remark: '' })
const editSupplierList = ref([])
const editSpList = ref([])

const editErrors = ref({})

function startEdit() {
  if (!quote.value) return
  editErrors.value = {}
  editForm.value = {
    title: quote.value.title || '',
    supplier_id: quote.value.supplier_id || null,
    salesperson_id: quote.value.salesperson_id || null,
    order_start: quote.value.order_start || '',
    order_end: quote.value.order_end || '',
    project_category: (quote.value.project_category || '').split(', ').filter(Boolean),
    remark: quote.value.remark || '',
  }
  editing.value = true
}

async function saveEdit() {
  if (!editForm.value.title.trim()) { editErrors.value.title = '报价单编号不能为空'; return }
  editErrors.value = {}
  const body = {
    title: editForm.value.title.trim(),
    supplier_id: editForm.value.supplier_id || null,
    salesperson_id: editForm.value.salesperson_id || null,
    order_start: editForm.value.order_start,
    order_end: editForm.value.order_end,
    project_category: editForm.value.project_category.join(', '),
    remark: editForm.value.remark,
  }
  const r = await api(`/api/quotes/${quote.value.id}`, 'PUT', body)
  if (r.error) { toast(r.error, 'danger'); return }
  quote.value = r.quote
  editing.value = false
  toast('已更新')
}

async function loadEditOptions() {
  const [sRes, spRes] = await Promise.allSettled([api('/api/suppliers'), api('/api/salespersons')])
  if (sRes.status === 'fulfilled') editSupplierList.value = sRes.value.suppliers || []
  if (spRes.status === 'fulfilled') editSpList.value = spRes.value.salespersons || []
}

// ─── 重置页面状态（路由 id 变化或首次挂载时调用）────────────────
async function initPage() {
  quote.value = null
  quoteEvents.value = []
  statusLogs.value = []
  showLogs.value = false
  loading.value = true
  loadingEvents.value = true
  await loadQuote()
  await fetchEvents()
}

// ─── 挂载：首次进入 ──────────────────────────────────────────
onMounted(async () => {
  await initPage()
  loadEditOptions()
})

// ─── 监听路由 id 变化：同组件实例复用时重新加载 ─────────────────
// 场景：从 /project/1 跳转到 /project/2，Vue Router 复用组件实例
// 不加 watch 的话 onMounted 不会重跑，导致旧数据残留
watch(
  () => route.params.id,
  async (newId, oldId) => {
    if (!newId || newId === oldId) return
    await initPage()
  }
)
</script>

<template>
  <div>
    <div class="page-header">
      <h5><i class="bi bi-kanban"></i>项目详情</h5>
      <router-link :to="{ name: 'quotes' }" class="btn btn-outline-secondary btn-modern">
        <i class="bi bi-arrow-left"></i> 返回列表
      </router-link>
    </div>

    <LoadingSpinner v-if="loading" :center="true" text="加载中..." />

    <template v-else-if="quote">
      <!-- 基本信息 -->
      <div class="card-modern mb-3">
        <div class="card-title-modern d-flex justify-content-between align-items-center">
          <span><i class="bi bi-file-text text-primary me-2"></i>基本信息</span>
          <button v-if="!editing && isAdmin()" class="btn btn-sm btn-outline-primary btn-modern" @click="startEdit">
            <i class="bi bi-pencil"></i> 编辑
          </button>
        </div>
        <div v-if="editing">
          <QuoteFormFields v-model="editForm" :supplier-list="editSupplierList" :salesperson-list="editSpList" :errors="editErrors" />
          <div class="d-flex justify-content-end gap-2 mt-2">
            <button class="btn btn-primary btn-modern" @click="saveEdit">保存</button>
            <button class="btn btn-secondary btn-modern" @click="editing = false">取消</button>
          </div>
        </div>
        <div v-else class="row g-2">
          <div class="col-12">
            <label class="form-label-modern">报价单编号</label>
            <div class="fw-medium">{{ quote.title || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">供应商</label>
            <div class="fw-medium">{{ quote.supplier_name || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">业务员</label>
            <div class="fw-medium">{{ quote.salesperson_name || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">订单起始日期</label>
            <div class="fw-medium">{{ quote.order_start || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">订单完成日期</label>
            <div class="fw-medium">{{ quote.order_end || '—' }}</div>
          </div>
          <div class="col-12">
            <label class="form-label-modern">项目类别</label>
            <div class="fw-medium">{{ quote.project_category || '—' }}</div>
          </div>
          <div class="col-12">
            <label class="form-label-modern">备注</label>
            <div class="text-muted" style="white-space:pre-wrap;font-size:.9rem">{{ quote.remark || '—' }}</div>
          </div>
        </div>
      </div>

      <!-- 项目状态 -->
      <div class="card-modern mb-3">
        <div class="card-title-modern"><i class="bi bi-flag text-primary"></i>项目状态</div>
        <div class="py-3">
          <!-- 流程步骤 -->
          <div class="d-flex justify-content-center align-items-center flex-wrap" style="gap:0">
            <template v-for="(s, i) in FLOW_STEPS" :key="s">
              <div class="d-flex flex-column align-items-center" style="min-width:90px">
                <div class="rounded-circle d-flex align-items-center justify-content-center fw-bold"
                  :style="{ ...stepStyles[s], width:'38px', height:'38px', cursor:'default', fontSize:'.75rem', transition:'all .2s' }"
                  :title="s">
                  ●
                </div>
                <span class="small mt-1 text-center px-1" :style="stepLabelStyle(s)">
                  {{ s.replace('项目', '').replace('已报价', '已报') }}
                </span>
              </div>
              <div v-if="i < FLOW_STEPS.length - 1" class="text-muted" style="font-size:1.1rem;margin:0 2px">→</div>
            </template>
          </div>

          <!-- 特殊状态展示 -->
          <div v-if="quote.status === '项目返工'" class="d-flex align-items-center justify-content-center gap-2 py-2 mt-2">
            <div style="width:18px;height:18px;border-radius:50%;background:#fd7e14"></div>
            <span class="fw-bold" style="color:#fd7e14">项目返工中</span>
          </div>
          <div v-if="quote.status === '项目终止'" class="d-flex align-items-center justify-content-center gap-2 py-2 mt-2">
            <div style="width:18px;height:18px;border-radius:50%;background:#dc3545"></div>
            <span class="fw-bold" style="color:#dc3545">项目已终止</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="text-center pb-3 d-flex flex-wrap justify-content-center gap-2">
          <button v-if="nextBtn" class="btn btn-primary btn-modern btn-lg"
            @click="advanceStatus" :disabled="patching">
            <span v-if="patching" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-arrow-right me-1"></i>下一步 → {{ nextBtn }}
          </button>
          <button v-if="quote.status === '项目完结'" class="btn btn-outline-warning btn-modern btn-lg"
            @click="startRework" :disabled="patching">
            <i class="bi bi-arrow-counterclockwise me-1"></i>项目返工
          </button>
          <button v-if="quote.status === '项目终止'" class="btn btn-outline-success btn-modern btn-lg"
            @click="restartProject" :disabled="patching">
            <i class="bi bi-arrow-counterclockwise me-1"></i>重启项目
          </button>
          <button v-if="canTerminate" class="btn btn-outline-danger btn-modern btn-lg"
            @click="terminateProject" :disabled="patching">
            <i class="bi bi-x-circle me-1"></i>终止项目
          </button>
        </div>

        <!-- 操作日志（折叠） -->
        <div class="border-top pt-2 px-3 pb-2" style="border-color:var(--gray-200) !important">
          <div class="d-flex align-items-center gap-1" style="cursor:pointer;user-select:none" @click="toggleLogs">
            <i class="bi bi-clock-history text-muted small"></i>
            <span class="text-muted small">操作日志</span>
            <i class="bi ms-auto small" :class="showLogs ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
          </div>
          <div v-if="showLogs" class="mt-2" style="max-height:200px;overflow-y:auto">
            <LoadingSpinner v-if="loadingLogs" size="sm" />
            <div v-else-if="statusLogs.length === 0" class="text-muted small text-center py-2">暂无操作记录</div>
            <div v-else v-for="log in statusLogs" :key="log.id"
              class="d-flex align-items-center gap-2 py-1" style="border-bottom:1px solid var(--gray-100);font-size:.78rem">
              <span class="text-muted" style="white-space:nowrap">{{ log.created_at }}</span>
              <span class="text-muted">{{ log.operator_name || '—' }}</span>
              <span class="text-muted">{{ log.from_status || '—' }} → {{ log.to_status }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 交流记录 -->
      <div class="card-modern mb-3">
        <div class="card-title-modern d-flex justify-content-between align-items-center">
          <span><i class="bi bi-chat-dots text-primary me-2"></i>交流记录</span>
          <button class="btn btn-sm btn-primary btn-modern" @click="openEventModal">
            <i class="bi bi-plus-lg"></i> 添加
          </button>
        </div>
        <LoadingSpinner v-if="loadingEvents" size="sm" />
        <div v-else-if="quoteEvents.length === 0" class="text-muted text-center py-3 small">暂无交流记录</div>
        <div v-else v-for="e in quoteEvents" :key="e.id"
          class="py-2 px-2"
          :style="{ borderBottom:'1px solid var(--gray-100)', borderLeft:'4px solid ' + (statusColor(e.quote_status) || '#6c757d') }">
          <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
            <span class="text-muted small">{{ e.created_at }}</span>
            <span class="text-muted small">{{ e.direction }}</span>
            <span v-if="e.creator_name" class="text-muted small">— {{ e.creator_name }}</span>
          </div>
          <div class="text-muted" style="font-size:.88rem;white-space:pre-wrap">{{ e.content }}</div>
        </div>
      </div>
    </template>

    <div v-else class="text-center py-5 text-muted">未找到该项目</div>
  </div>

  <!-- 添加交流记录 Modal -->
  <ModalDialog :show="showEventModal" title="添加交流记录" @close="showEventModal = false">
    <label class="form-label-modern">方向</label>
    <select class="form-select mb-2" v-model="eventDirection">
      <option value="客户→供应商">客户 → 供应商</option>
      <option value="供应商→客户">供应商 → 客户</option>
    </select>
    <textarea class="form-control" v-model="eventContent" rows="4" placeholder="记录交流内容..." style="resize:vertical"></textarea>
    <template #footer>
      <button class="btn btn-primary btn-modern" @click="saveEvent" :disabled="savingEvent">
        <span v-if="savingEvent" class="spinner-border spinner-border-sm me-1"></span>
        保存
      </button>
      <button class="btn btn-secondary btn-modern" @click="showEventModal = false">取消</button>
    </template>
  </ModalDialog>
</template>
