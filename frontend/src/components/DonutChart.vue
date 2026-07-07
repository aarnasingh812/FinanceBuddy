<template>
  <div class="donut-wrapper">
    <canvas ref="canvas"></canvas>
    <div class="donut-center">
      <div class="t-mono" style="font-size:1.1rem;font-weight:700;color:var(--col-text-primary)">{{ centerLabel }}</div>
      <div class="t-label text-muted">Total</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  Chart, DoughnutController, ArcElement, Tooltip
} from 'chart.js'

Chart.register(DoughnutController, ArcElement, Tooltip)

const props = defineProps({
  segments: { type: Array, required: true }, // [{ label, value, color }]
  centerLabel: { type: String, default: '' },
})

const canvas = ref(null)
let instance = null

function buildChart() {
  if (instance) instance.destroy()
  if (!canvas.value || !props.segments.length) return
  instance = new Chart(canvas.value, {
    type: 'doughnut',
    data: {
      labels: props.segments.map(s => s.label),
      datasets: [{
        data: props.segments.map(s => s.value),
        backgroundColor: props.segments.map(s => s.color),
        borderWidth: 0,
        hoverOffset: 6,
      }]
    },
    options: {
      cutout: '72%',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#131b2e',
          titleColor: '#9fa1a8',
          bodyColor: '#fff',
          padding: 10, cornerRadius: 8,
          titleFont: { family: 'Inter', size: 11 },
          bodyFont:  { family: 'Inter', size: 13, weight: '700' },
          callbacks: {
            label: ctx => ` $${ctx.parsed.toLocaleString()} (${Math.round(ctx.parsed / props.segments.reduce((a,b)=>a+b.value,0) * 100)}%)`
          }
        }
      }
    }
  })
}

onMounted(() => buildChart())
watch(() => props.segments, () => buildChart(), { deep: true })
onUnmounted(() => instance?.destroy())
</script>

<style scoped>
.donut-wrapper {
  position: relative;
  width: 140px; height: 140px;
  flex-shrink: 0;
}
.donut-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  pointer-events: none;
}
</style>
