<template>
  <div class="chart-wrapper">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  Chart,
  LineElement, PointElement, LineController,
  CategoryScale, LinearScale,
  Tooltip, Filler
} from 'chart.js'

Chart.register(LineElement, PointElement, LineController, CategoryScale, LinearScale, Tooltip, Filler)

const props = defineProps({
  labels:  { type: Array, required: true },
  datasets: { type: Array, required: true }, // [{ label, data, color }]
  height:  { type: Number, default: 200 },
})

const canvas = ref(null)
let chartInstance = null

function buildChart () {
  if (chartInstance) chartInstance.destroy()

  chartInstance = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: props.labels,
      datasets: props.datasets.map(ds => ({
        label: ds.label,
        data: ds.data,
        borderColor: ds.color,
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 6,
        pointBackgroundColor: ds.color,
        fill: true,
        backgroundColor: (ctx) => {
          const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, props.height)
          g.addColorStop(0, ds.color + '20')
          g.addColorStop(1, ds.color + '00')
          return g
        },
        tension: 0.4,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#131b2e',
          titleColor: '#9fa1a8',
          bodyColor: '#ffffff',
          padding: 10,
          cornerRadius: 8,
          titleFont: { family: 'Inter', size: 11, weight: '600' },
          bodyFont:  { family: 'Inter', size: 13, weight: '700' },
          callbacks: {
            label: ctx => ` $${ctx.parsed.y.toLocaleString()}`
          }
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: '#9fa1a8',
            font: { family: 'Inter', size: 11, weight: '600' },
          }
        },
        y: {
          grid: { color: '#f2f4f6', drawTicks: false },
          border: { display: false, dash: [4, 4] },
          ticks: {
            color: '#9fa1a8',
            font: { family: 'Inter', size: 11 },
            maxTicksLimit: 5,
            callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0)+'k' : v)
          }
        }
      }
    }
  })
}

onMounted(buildChart)
onUnmounted(() => chartInstance?.destroy())
watch(() => props.datasets, buildChart, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  position: relative;
  width: 100%;
  height: v-bind('height + "px"');
}
</style>
