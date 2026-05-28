<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'
import { useQuoteStatus } from '../composables/useQuoteStatus'
import StatCard from '../components/dashboard/StatCard.vue'
import TrendChart from '../components/dashboard/TrendChart.vue'

const router = useRouter()
const toast = inject('toast')
const { api } = useApi()
const { statusClass, STATUS_HEX } = useQuoteStatus()

const loading = ref(true)
const totalCount = ref(0)
const inProgressCount = ref(0)
const monthCount = ref(0)
const terminatedCount = ref(0)
const statusCounts = ref({})
const recentQuotes = ref([])
const trendData = ref([])

const STAT_CARDS = computed(() => [
  { icon: 'bi bi-file-earmark-text', bgColor: '#e0e7ff', iconColor: '#4f46e5', label: '总报价单', value: totalCount.value },
  { icon: 'bi bi-arrow-repeat',      bgColor: '#dbeafe', iconColor: '#2563eb', label: '进行中',  value: inProgressCount.value },
  { icon: 'bi bi-calendar-plus',     bgColor: '#dcfce7', iconColor: '#16a34a', label: '本月新增', value: monthCount.value },
  { icon: 'bi bi-x-circle',          bgColor: '#fef2f2', iconColor: '#dc2626', label: '项目终止', value: terminatedCount.value },
])

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
  } catch (e) {
    toast('加载概览失败', 'danger')
  } finally {
    loading.value = false
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
    <div class="spinner-border text-primary mb-2" role="status">
      <span class="visually-hidden">加载中...</span>
    </div>
    <p class="text-muted small">加载概览...</p>
  </div>

  <template v-else>
    <div class="page-header">
      <h5><i class="bi bi-house-door"></i>首页</h5>
    </div>

    <!-- 统计卡片（StatCard 组件，消除 4 处重复） -->
    <div class="row g-3 mb-3">
      <div v-for="card in STAT_CARDS" :key="card.label" class="col-md-3 col-6">
        <StatCard v-bind="card" />
      </div>
    </div>

    <!-- 月度趋势图 -->
    <div class="card-modern mb-3 anim-in" style="animation-delay:.05s">
      <div class="card-title-modern">
        <span><i class="bi bi-graph-up text-primary me-2"></i>月度趋势</span>
      </div>
      <TrendChart :trend-data="trendData" />
    </div>

    <!-- 状态分布 -->
    <div class="card-modern mb-3 anim-in" style="animation-delay:.05s">
      <div class="card-title-modern">
        <span><i class="bi bi-bar-chart text-primary me-2"></i>状态分布</span>
      </div>
      <div v-if="sortedStatuses.length" class="d-flex flex-column gap-2">
        <div v-for="s in sortedStatuses" :key="s" class="d-flex align-items-center gap-2">
          <span class="text-muted small" style="width:130px;flex-shrink:0">{{ s }}</span>
          <div class="flex-grow-1" style="height:22px;background:var(--gray-100);border-radius:6px;overflow:hidden">
            <div :style="{
              width: (statusCounts[s] / (totalCount || 1) * 100) + '%',
              height: '100%',
              background: STATUS_HEX[s] || '#0dcaf0',
              borderRadius: '6px',
              transition: 'width .4s ease',
              minWidth: statusCounts[s] > 0 ? '20px' : '0',
            }"></div>
          </div>
          <span class="fw-medium small" style="width:36px;text-align:right">{{ statusCounts[s] }}</span>
        </div>
      </div>
      <div v-else class="text-muted text-center py-2 small">暂无数据</div>
    </div>

    <!-- 最近更新 -->
    <div class="card-modern anim-in" style="animation-delay:.1s">
      <div class="card-title-modern d-flex justify-content-between align-items-center">
        <span><i class="bi bi-clock-history text-primary me-2"></i>最近更新</span>
        <router-link :to="{ name: 'quotes' }" class="btn btn-sm btn-outline-primary btn-modern">
          查看全部 <i class="bi bi-arrow-right ms-1"></i>
        </router-link>
      </div>
      <template v-if="recentQuotes.length">
        <div v-for="qq in recentQuotes" :key="qq.id"
          class="py-2 px-2 rounded recent-quote-row"
          style="cursor:pointer;border-bottom:1px solid var(--gray-100)"
          @click="router.push({ name: 'project-detail', params: { id: qq.id } })">
          <i class="bi bi-file-earmark text-muted"></i>
          <div class="fw-medium text-truncate" style="font-size:.9rem;min-width:0">
            {{ qq.title || '未命名' }}
          </div>
          <div class="text-muted small text-truncate d-none d-sm-block" style="min-width:0">
            {{ qq.supplier_name || '—' }}
          </div>
          <div class="text-muted small text-truncate d-none d-md-block" style="min-width:0">
            <i class="bi bi-person me-1"></i>{{ qq.salesperson_name || '—' }}
          </div>
          <span class="badge" :class="statusClass(qq.status)" style="font-size:.7rem">
            {{ qq.status }}
          </span>
        </div>
      </template>
      <div v-else class="text-muted text-center py-3 small">暂无报价单</div>
    </div>
  </template>
</template>
