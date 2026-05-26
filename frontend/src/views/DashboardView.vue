<script setup>
import { ref, computed, onMounted, inject, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const router = useRouter()
const toast = inject('toast')
const { api } = useApi()

const loading = ref(true)
const totalCount = ref(0)
const inProgressCount = ref(0)
const monthCount = ref(0)
const terminatedCount = ref(0)
const statusCounts = ref({})
const recentQuotes = ref([])
const trendData = ref([])

const STATUS_COLORS = {
  '项目报价中': '#0dcaf0',
  '项目已报价未付款': '#ffc107',
  '项目生产中': '#0d6efd',
  '项目完结': '#198754',
  '项目返工': '#fd7e14',
  '项目终止': '#dc3545',
}

const trendCanvas = ref(null)
const pieCanvas = ref(null)
let trendChart = null
let pieChart = null

async function fetchDashboard() {
  loading.value = true
  try {
    const now = new Date()
    const monthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const [r1, r2, r3, r4] = await Promise.all([
      api('/api/quotes/stats'),
      api(`/api/quotes/stats?month=${monthStr}`),
      api('/api/quotes?per_page=5'),
      api('/api/quotes/trends?months=6'),
    ])
    totalCount.value = r1.total || 0
    statusCounts.value = r1.status_counts || {}
    monthCount.value = r2.total || 0
    terminatedCount.value = r1.status_counts?.['项目终止'] || 0
    recentQuotes.value = (r3.quotes || []).slice(0, 5)
    trendData.value = r4.trends || []
    inProgressCount.value = Object.entries(statusCounts.value)
      .filter(([s]) => s !== '项目完结' && s !== '项目终止')
      .reduce((sum, [, c]) => sum + c, 0)
    await nextTick()
    renderCharts()
  } catch (e) {
    toast('加载概览失败', 'danger')
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  if (trendChart) trendChart.destroy()
  if (pieChart) pieChart.destroy()
  if (trendCanvas.value && trendData.value.length) {
    trendChart = new Chart(trendCanvas.value, {
      type: 'line',
      data: {
        labels: trendData.value.map(t => t.month),
        datasets: [{
          label: '新建',
          data: trendData.value.map(t => t.created),
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79,70,229,.1)',
          fill: true,
          tension: .3,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
        },
      },
    })
  }
  if (pieCanvas.value) {
    const labels = Object.keys(statusCounts.value)
    const data = Object.values(statusCounts.value)
    if (labels.length) {
      pieChart = new Chart(pieCanvas.value, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: labels.map(l => STATUS_COLORS[l] || '#6c757d'),
          }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'right', labels: { font: { size: 11 } } },
          },
        },
      })
    }
  }
}

const sortedStatuses = computed(() => {
  const order = ['项目报价中', '项目已报价未付款', '项目生产中', '项目完结', '项目返工', '项目终止']
  return order.filter(s => statusCounts.value[s])
})

onMounted(fetchDashboard)
</script>

<template>
  <div v-if="loading" class="text-center py-5">
    <div class="spinner-border text-primary mb-2" role="status"></div>
    <p class="text-muted small">加载概览...</p>
  </div>

  <template v-else>
    <div class="page-header">
      <h5><i class="bi bi-house-door"></i>首页</h5>
    </div>

    <!-- Stat Cards -->
    <div class="row g-3 mb-3">
      <div class="col-md-3">
        <div class="stat-card anim-in">
          <div class="d-flex align-items-center gap-3">
            <div class="stat-icon" style="background:#e0e7ff;color:#4f46e5">
              <i class="bi bi-file-earmark-text"></i>
            </div>
            <div>
              <div class="text-muted small">总报价单</div>
              <div class="fw-bold" style="font-size:1.6rem">{{ totalCount }}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="stat-card anim-in">
          <div class="d-flex align-items-center gap-3">
            <div class="stat-icon" style="background:#dbeafe;color:#2563eb">
              <i class="bi bi-arrow-repeat"></i>
            </div>
            <div>
              <div class="text-muted small">进行中</div>
              <div class="fw-bold" style="font-size:1.6rem">{{ inProgressCount }}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="stat-card anim-in">
          <div class="d-flex align-items-center gap-3">
            <div class="stat-icon" style="background:#dcfce7;color:#16a34a">
              <i class="bi bi-calendar-plus"></i>
            </div>
            <div>
              <div class="text-muted small">本月新增</div>
              <div class="fw-bold" style="font-size:1.6rem">{{ monthCount }}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="stat-card anim-in">
          <div class="d-flex align-items-center gap-3">
            <div class="stat-icon" style="background:#fef2f2;color:#dc2626">
              <i class="bi bi-x-circle"></i>
            </div>
            <div>
              <div class="text-muted small">项目终止</div>
              <div class="fw-bold" style="font-size:1.6rem">{{ terminatedCount }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Trend Chart + Pie Chart -->
    <div class="row g-3 mb-3">
      <div class="col-md-7">
        <div class="card-modern anim-in" style="animation-delay:.05s">
          <div class="card-title-modern"><span><i class="bi bi-graph-up text-primary me-2"></i>月度趋势</span></div>
          <canvas ref="trendCanvas" style="max-height:220px"></canvas>
        </div>
      </div>
      <div class="col-md-5">
        <div class="card-modern anim-in" style="animation-delay:.05s">
          <div class="card-title-modern"><span><i class="bi bi-pie-chart text-primary me-2"></i>状态占比</span></div>
          <canvas ref="pieCanvas" style="max-height:220px"></canvas>
        </div>
      </div>
    </div>

    <!-- Status Distribution -->
    <div class="card-modern anim-in" style="animation-delay:.05s">
      <div class="card-title-modern"><span><i class="bi bi-bar-chart text-primary me-2"></i>状态分布</span></div>
      <div v-if="sortedStatuses.length" class="d-flex flex-column gap-2">
        <div v-for="s in sortedStatuses" :key="s" class="d-flex align-items-center gap-2">
          <span class="text-muted small" style="width:130px;flex-shrink:0">{{ s }}</span>
          <div class="flex-grow-1" style="height:22px;background:var(--gray-100);border-radius:6px;overflow:hidden">
            <div
              :style="{
                width: (statusCounts[s] / (totalCount || 1) * 100) + '%',
                height: '100%',
                background: STATUS_COLORS[s] || '#0dcaf0',
                borderRadius: '6px',
                transition: 'width .4s ease',
                minWidth: statusCounts[s] > 0 ? '20px' : '0',
              }"
            ></div>
          </div>
          <span class="fw-medium small" style="width:36px;text-align:right">{{ statusCounts[s] }}</span>
        </div>
      </div>
      <div v-else class="text-muted text-center py-2 small">暂无数据</div>
    </div>

    <!-- Recent Quotes -->
    <div class="card-modern anim-in" style="animation-delay:.1s">
      <div class="card-title-modern d-flex justify-content-between align-items-center">
        <span><i class="bi bi-clock-history text-primary me-2"></i>最近更新</span>
        <router-link :to="{name:'quotes'}" class="btn btn-sm btn-outline-primary btn-modern">
          查看全部 <i class="bi bi-arrow-right ms-1"></i>
        </router-link>
      </div>
      <template v-if="recentQuotes.length">
        <div v-for="qq in recentQuotes" :key="qq.id"
          class="d-grid align-items-center py-2 px-2 rounded"
          style="grid-template-columns:24px 160px 120px 120px auto;gap:10px;cursor:pointer;border-bottom:1px solid var(--gray-100)"
          @click="router.push({name:'project-detail',params:{id:qq.id}})">
          <i class="bi bi-file-earmark text-muted" style="text-align:center"></i>
          <div class="fw-medium text-truncate" style="font-size:.9rem;text-align:left">{{ qq.title || '未命名' }}</div>
          <div class="text-muted small text-truncate" style="text-align:left">{{ qq.supplier_name || qq.client || '--' }}</div>
          <div class="text-muted small text-truncate" style="text-align:left">
            <i class="bi bi-person me-1"></i>{{ qq.salesperson_name || qq.contact || '--' }}
          </div>
          <span class="badge" :class="{
            'bg-info': qq.status === '项目报价中',
            'bg-warning text-dark': qq.status === '项目已报价未付款',
            'bg-primary': qq.status === '项目生产中',
            'bg-success': qq.status === '项目完结',
            'bg-warning': qq.status === '项目返工',
            'bg-danger': qq.status === '项目终止',
          }" style="font-size:.7rem">{{ qq.status }}</span>
        </div>
      </template>
      <div v-else class="text-muted text-center py-3 small">暂无报价单</div>
    </div>
  </template>
</template>
