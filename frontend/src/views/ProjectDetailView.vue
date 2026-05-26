<script setup>
import { ref, reactive, inject, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'

const router = useRouter()
const route = useRoute()
const toast = inject('toast')
const { api } = useApi()

const quote = ref(null)
const loading = ref(true)
const patching = ref(false)

const FLOW_STEPS = ['项目报价中', '项目已报价未付款', '项目生产中', '项目完结']
const STEP_COLORS = {
  '项目报价中': '#0dcaf0',
  '项目已报价未付款': '#ffc107',
  '项目生产中': '#0d6efd',
  '项目完结': '#198754',
  '项目返工': '#fd7e14',
  '项目终止': '#dc3545',
}

const canTerminate = computed(() => {
  if (!quote.value) return false
  return quote.value.status !== '项目终止'
})

const nextBtn = computed(() => {
  if (!quote.value) return ''
  if (quote.value.status === '项目完结' || quote.value.status === '项目终止') return ''
  const ns = quote.value.next_statuses || []
  const regular = ns.filter(s => s !== '项目终止')
  return regular[0] || ''
})

function stepStatus(s) {
  if (!quote.value) return 'disabled'
  if (s === quote.value.status) return 'current'
  const ns = quote.value.next_statuses || []
  if (ns.includes(s)) return 'clickable'
  return 'disabled'
}

function stepColor(s) {
  const st = stepStatus(s)
  if (st === 'current') return STEP_COLORS[s] || '#6c757d'
  if (st === 'clickable') return '#ced4da'
  return '#e9ecef'
}

function stepDotColor(s) {
  const st = stepStatus(s)
  if (st === 'current') return '#fff'
  if (st === 'clickable') return STEP_COLORS[s] || '#6c757d'
  return '#adb5bd'
}

function stepBgColor(s) {
  const st = stepStatus(s)
  if (st === 'current') return STEP_COLORS[s] || '#6c757d'
  if (st === 'clickable') return '#fff'
  return '#f8f9fa'
}

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

async function advanceStatus() {
  if (!quote.value) return
  const ns = quote.value.next_statuses || []
  const regular = ns.filter(s => s !== '项目终止')
  if (!regular.length) return
  if (!confirm(`确定将状态从「${quote.value.status}」改为「${regular[0]}」吗？`)) return
  patching.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/status`, 'PATCH', { status: regular[0] })
    if (r.error) { toast(r.error, 'danger'); return }
    await loadQuote()
    toast('状态已更新')
    fetchLogs()
  } catch (e) {
    toast('操作失败', 'danger')
  } finally {
    patching.value = false
  }
}

async function startRework() {
  if (!quote.value || !confirm('确定将项目状态改为「项目返工」吗？')) return
  patching.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/status`, 'PATCH', { status: '项目返工' })
    if (r.error) { toast(r.error, 'danger'); return }
    await loadQuote()
    toast('已改为项目返工')
    fetchLogs()
  } catch (e) {
    toast('操作失败', 'danger')
  } finally {
    patching.value = false
  }
}

async function restartProject() {
  if (!quote.value || !confirm('确定重启该项目吗？将回到「项目报价中」状态')) return
  patching.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/status`, 'PATCH', { status: '项目报价中' })
    if (r.error) { toast(r.error, 'danger'); return }
    await loadQuote()
    toast('项目已重启')
    fetchLogs()
  } catch (e) { toast('操作失败', 'danger') }
  finally { patching.value = false }
}

async function terminateProject() {
  if (!quote.value || !confirm('确定终止该项目吗？')) return
  patching.value = true
  try {
    const r = await api(`/api/quotes/${quote.value.id}/status`, 'PATCH', { status: '项目终止' })
    if (r.error) { toast(r.error, 'danger'); return }
    await loadQuote()
    toast('项目已终止')
    fetchLogs()
  } catch (e) {
    toast('操作失败', 'danger')
  } finally {
    patching.value = false
  }
}

// ─── Status Logs ───
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

// ─── Quote Events ───
const quoteEvents = ref([])
const showEventModal = ref(false)
const eventContent = ref('')
const eventDirection = ref('客户→供应商')
const loadingEvents = ref(false)

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
  const r = await api(`/api/quotes/${quote.value.id}/events`, 'POST', { content, direction: eventDirection.value })
  if (r.error) { toast(r.error, 'danger'); return }
  showEventModal.value = false
  toast('已添加')
  fetchEvents()
}

// ─── Edit Mode ───
const editing = ref(false)
const editForm = reactive({ title: '', supplier_id: null, salesperson_id: null, order_start: '', order_end: '', project_category: [], remark: '' })
const editSupplierList = ref([])
const editSpList = ref([])
const editProjectOptions = ['PCBA', '固件开发', '算法开发']

function startEdit() {
  if (!quote.value) return
  editForm.title = quote.value.title || ''
  editForm.supplier_id = quote.value.supplier_id || null
  editForm.salesperson_id = quote.value.salesperson_id || null
  editForm.order_start = quote.value.order_start || ''
  editForm.order_end = quote.value.order_end || ''
  editForm.project_category = (quote.value.project_category || '').split(', ').filter(Boolean)
  editForm.remark = quote.value.remark || ''
  editing.value = true
}

async function saveEdit() {
  const body = {
    title: editForm.title.trim(),
    supplier_id: editForm.supplier_id || null,
    salesperson_id: editForm.salesperson_id || null,
    order_start: editForm.order_start,
    order_end: editForm.order_end,
    project_category: editForm.project_category.join(', '),
    remark: editForm.remark,
  }
  const r = await api(`/api/quotes/${quote.value.id}`, 'PUT', body)
  if (r.error) { toast(r.error, 'danger'); return }
  quote.value = r.quote
  editing.value = false
  toast('已更新')
}

function cancelEdit() {
  editing.value = false
}

async function loadEditOptions() {
  const [sRes, spRes] = await Promise.allSettled([
    api('/api/suppliers'),
    api('/api/salespersons'),
  ])
  if (sRes.status === 'fulfilled') editSupplierList.value = sRes.value.suppliers || []
  if (spRes.status === 'fulfilled') editSpList.value = spRes.value.salespersons || []
}

function statusEventColor(s) {
  const map = {
    '项目报价中': '#0dcaf0',
    '项目已报价未付款': '#ffc107',
    '项目生产中': '#0d6efd',
    '项目完结': '#198754',
    '项目返工': '#fd7e14',
    '项目终止': '#dc3545',
  }
  return map[s] || '#6c757d'
}

onMounted(() => {
  loadQuote()
  fetchEvents()
  loadEditOptions()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h5><i class="bi bi-kanban"></i>项目详情</h5>
      <router-link :to="{name:'quotes'}" class="btn btn-outline-secondary btn-modern">
        <i class="bi bi-arrow-left"></i> 返回列表
      </router-link>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <template v-else-if="quote">
      <div class="card-modern mb-3">
        <div class="card-title-modern d-flex justify-content-between align-items-center">
          <span><i class="bi bi-file-text text-primary"></i>基本信息</span>
          <button v-if="!editing" class="btn btn-sm btn-outline-primary btn-modern" @click="startEdit">
            <i class="bi bi-pencil"></i> 编辑
          </button>
        </div>
        <div class="row g-2">
          <div class="col-12">
            <label class="form-label-modern">报价单编号</label>
            <input v-if="editing" class="form-control" v-model="editForm.title" placeholder="报价单编号">
            <div v-else class="fw-medium">{{ quote.title || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">供应商</label>
            <select v-if="editing" class="form-select" v-model="editForm.supplier_id">
              <option :value="null">请选择供应商</option>
              <option v-for="s in editSupplierList" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <div v-else class="fw-medium">{{ quote.supplier_name || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">业务员</label>
            <select v-if="editing" class="form-select" v-model="editForm.salesperson_id">
              <option :value="null">请选择业务员</option>
              <option v-for="sp in editSpList" :key="sp.id" :value="sp.id">{{ sp.name }}</option>
            </select>
            <div v-else class="fw-medium">{{ quote.salesperson_name || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">订单起始日期</label>
            <input v-if="editing" class="form-control" v-model="editForm.order_start" type="date">
            <div v-else class="fw-medium">{{ quote.order_start || '—' }}</div>
          </div>
          <div class="col-md-6">
            <label class="form-label-modern">订单完成日期</label>
            <input v-if="editing" class="form-control" v-model="editForm.order_end" type="date">
            <div v-else class="fw-medium">{{ quote.order_end || '—' }}</div>
          </div>
          <div class="col-12">
            <label class="form-label-modern">项目个类</label>
            <div v-if="editing" class="d-flex gap-3 mt-1">
              <label v-for="opt in editProjectOptions" :key="opt" class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" :value="opt" v-model="editForm.project_category">
                <span class="form-check-label">{{ opt }}</span>
              </label>
            </div>
            <div v-else class="fw-medium">{{ quote.project_category || '—' }}</div>
          </div>
          <div class="col-12">
            <label class="form-label-modern">备注</label>
            <textarea v-if="editing" class="form-control" v-model="editForm.remark" rows="3"></textarea>
            <div v-else class="text-muted" style="white-space:pre-wrap;font-size:.9rem">{{ quote.remark || '—' }}</div>
          </div>
        </div>
        <div v-if="editing" class="d-flex justify-content-end gap-2 mt-2">
          <button class="btn btn-primary btn-modern" @click="saveEdit">保存</button>
          <button class="btn btn-secondary btn-modern" @click="cancelEdit">取消</button>
        </div>
      </div>

      <div class="card-modern mb-3">
        <div class="card-title-modern"><i class="bi bi-flag text-primary"></i>项目状态</div>
        <div class="py-3">
          <!-- Flow steps -->
          <div class="d-flex justify-content-center align-items-center flex-wrap" style="gap:0">
            <template v-for="(s, i) in FLOW_STEPS" :key="s">
              <div class="d-flex flex-column align-items-center" style="min-width:90px">
                <div
                  class="rounded-circle d-flex align-items-center justify-content-center fw-bold"
                  :style="{
                    width:'38px', height:'38px',
                    background: stepBgColor(s),
                    border: '3px solid ' + stepColor(s),
                    color: stepDotColor(s),
                    cursor: 'default',
                    fontSize: '.75rem',
                    transition: 'all .2s',
                    animation: stepStatus(s) === 'current' ? 'stepPulse 2s ease-in-out infinite' : 'none',
                  }"
                  :title="s">
                  <template v-if="stepStatus(s) === 'current'">●</template>
                  <template v-else-if="stepStatus(s) === 'clickable'">→</template>
                  <template v-else>●</template>
                </div>
                <span class="small mt-1 text-center px-1"
                  :style="{
                    fontWeight: s === quote.status ? '700' : '400',
                    color: s === quote.status ? '#333' : '#999',
                    fontSize: '.72rem',
                    lineHeight: '1.2',
                  }">{{ s.replace('项目','').replace('已报价','已报') }}</span>
              </div>
              <div v-if="i < FLOW_STEPS.length - 1" class="text-muted" style="font-size:1.1rem;margin:0 2px">
                <template v-if="s === '项目完结' || s === '项目返工'">↔</template>
                <template v-else>→</template>
              </div>
            </template>
          </div>
          <div class="text-center mt-2">
            <template v-if="patching">
              <div class="spinner-border spinner-border-sm text-primary me-1"></div>
              <span class="small text-muted">更新中...</span>
            </template>
          </div>
          <div v-if="nextBtn" class="text-center mb-2">
            <button class="btn btn-primary btn-modern btn-lg" @click="advanceStatus" :disabled="patching">
              <span v-if="patching" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="bi bi-arrow-right me-1"></i>下一步 → {{ nextBtn }}
            </button>
          </div>
          <div v-if="quote?.status === '项目完结'" class="text-center mb-2">
            <button class="btn btn-outline-warning btn-modern btn-lg" @click="startRework" :disabled="patching">
              <i class="bi bi-arrow-counterclockwise me-1"></i>项目返工
            </button>
          </div>
        </div>
        <div class="text-center pb-3">
          <div v-if="quote.status === '项目返工'" class="d-flex align-items-center justify-content-center gap-2 py-2">
            <div style="width:18px;height:18px;border-radius:50%;background:#fd7e14"></div>
            <span class="fw-bold" style="color:#fd7e14">项目返工中</span>
          </div>
          <div v-if="quote.status === '项目终止'" class="d-flex align-items-center justify-content-center gap-2 py-2">
            <div style="width:18px;height:18px;border-radius:50%;background:#dc3545"></div>
            <span class="fw-bold" style="color:#dc3545">项目已终止</span>
          </div>
          <div v-if="quote.status === '项目终止'" class="text-center mb-2">
            <button class="btn btn-outline-success btn-modern btn-lg" @click="restartProject" :disabled="patching">
              <i class="bi bi-arrow-counterclockwise me-1"></i>重启项目
            </button>
          </div>
          <button v-if="canTerminate" class="btn btn-outline-danger btn-modern btn-lg" @click="terminateProject" :disabled="patching">
            <i class="bi bi-x-circle me-1"></i>终止项目
          </button>
        </div>
        <!-- Status Logs -->
        <div class="border-top pt-2 px-3 pb-2" style="border-color:var(--gray-200) !important">
          <div class="d-flex align-items-center gap-1" style="cursor:pointer;user-select:none"
            @click="toggleLogs">
            <i class="bi bi-clock-history text-muted small"></i>
            <span class="text-muted small">操作日志</span>
            <i class="bi ms-auto small" :class="showLogs ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
          </div>
          <div v-if="showLogs" class="mt-2" style="max-height:200px;overflow-y:auto">
            <div v-if="loadingLogs" class="text-center py-2">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </div>
            <div v-else-if="statusLogs.length === 0" class="text-muted small text-center py-2">暂无操作记录</div>
            <div v-else v-for="log in statusLogs" :key="log.id"
              class="d-flex align-items-center gap-2 py-1" style="border-bottom:1px solid var(--gray-100);font-size:.78rem">
              <span class="text-muted" style="white-space:nowrap">{{ log.created_at }}</span>
              <span class="text-muted">{{ log.from_status || '—' }} → {{ log.to_status }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quote Events -->
      <div class="card-modern mb-3">
        <div class="card-title-modern d-flex justify-content-between align-items-center">
          <span><i class="bi bi-chat-dots text-primary"></i>交流记录</span>
          <button class="btn btn-sm btn-primary btn-modern" @click="openEventModal"><i class="bi bi-plus-lg"></i> 添加</button>
        </div>
        <div v-if="loadingEvents" class="text-center py-3">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="quoteEvents.length === 0" class="text-muted text-center py-3 small">暂无交流记录</div>
        <div v-else v-for="e in quoteEvents" :key="e.id"
          class="py-2 px-2"
          :style="{ borderBottom:'1px solid var(--gray-100)', borderLeft:'4px solid ' + (statusEventColor(e.quote_status) || '#6c757d'), marginBottom:0 }">
          <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
            <span class="text-muted small">{{ e.created_at }}</span>
            <span class="text-muted small">{{ e.direction }}</span>
          </div>
          <div class="text-muted" style="font-size:.88rem;white-space:pre-wrap">{{ e.content }}</div>
        </div>
      </div>
    </template>

    <div v-else class="text-center py-5 text-muted">未找到该项目</div>
  </div>

  <!-- Event Modal -->
  <Teleport to="body">
    <div v-if="showEventModal" class="modal-backdrop show" @click="showEventModal = false"></div>
    <div v-if="showEventModal" class="modal d-block modern-modal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">添加交流记录</h5>
            <button type="button" class="btn-close" @click="showEventModal = false"></button>
          </div>
          <div class="modal-body">
            <label class="form-label-modern">方向</label>
            <select class="form-select mb-2" v-model="eventDirection">
              <option value="客户→供应商">客户 → 供应商</option>
              <option value="供应商→客户">供应商 → 客户</option>
            </select>
            <textarea class="form-control" v-model="eventContent" rows="4" placeholder="记录交流内容..."
              style="resize:vertical"></textarea>
          </div>
          <div class="modal-footer">
            <button class="btn btn-primary btn-modern" @click="saveEvent">保存</button>
            <button class="btn btn-secondary btn-modern" @click="showEventModal = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
