<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  trendData: { type: Array, default: () => [] },
})

const canvas = ref(null)
let chart = null

function renderChart() {
  if (chart) { chart.destroy(); chart = null }
  if (!canvas.value || !props.trendData.length) return
  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: props.trendData.map(t => t.month),
      datasets: [{
        label: '新建',
        data: props.trendData.map(t => t.created),
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79,70,229,.1)',
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  })
}

onMounted(renderChart)
watch(() => props.trendData, renderChart, { deep: true })
onUnmounted(() => { chart?.destroy() })
</script>

<template>
  <div style="height:220px;position:relative">
    <canvas ref="canvas"></canvas>
  </div>
</template>
