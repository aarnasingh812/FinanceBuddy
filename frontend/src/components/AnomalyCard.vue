<template>
  <div :class="['anomaly-card', severityClass]">

    <!-- Top row: score ring + header + amount -->
    <div class="anomaly-top">

      <!-- Score ring -->
      <div class="score-ring">
        <svg viewBox="0 0 36 36" class="ring-svg">
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--col-surface-high)" stroke-width="3"/>
          <circle cx="18" cy="18" r="15.5" fill="none" :stroke="ringColor" stroke-width="3"
                  stroke-dasharray="97.4" :stroke-dashoffset="97.4 * (1 - anomaly.anomaly_score)"
                  stroke-linecap="round" transform="rotate(-90 18 18)"/>
        </svg>
        <span class="ring-label t-mono" :style="{ color: ringColor }">
          {{ anomaly.anomaly_score.toFixed(2) }}
        </span>
      </div>

      <!-- Title + meta -->
      <div class="anomaly-meta">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <span class="t-body" style="font-weight:700">{{ anomaly.title }}</span>
          <span v-if="anomaly.ml_contributed" class="badge badge-blue" title="ML model flagged this">
            <span class="material-symbols-outlined" style="font-size:9px">smart_toy</span>
            ML
          </span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:2px">
          <span class="badge badge-neutral" style="text-transform:capitalize">{{ anomaly.category }}</span>
          <span class="t-label text-muted">{{ fmtDate(anomaly.date) }}</span>
        </div>
      </div>

      <!-- Amount -->
      <div class="anomaly-amount">
        <div class="t-mono" :style="{ color: ringColor, fontWeight: 700, fontSize: '1rem' }">
          ₹{{ anomaly.amount.toLocaleString('en-IN') }}
        </div>
        <div class="t-label" :style="{ color: ringColor, textAlign:'right' }">
          {{ severityLabel }}
        </div>
      </div>
    </div>

    <!-- Score bar -->
    <div class="score-bar-wrap">
      <div class="progress-track" style="height:3px">
        <div class="progress-fill" :style="{ width: (anomaly.anomaly_score * 100) + '%', background: ringColor }"></div>
      </div>
      <span class="t-label text-faint" style="white-space:nowrap">
        Score {{ (anomaly.anomaly_score * 100).toFixed(0) }}/100
      </span>
    </div>

    <!-- Reasons / signals -->
    <div class="reasons-list">
      <div v-for="reason in anomaly.anomaly_reasons" :key="reason.signal" class="reason-row">
        <div class="reason-signal">
          <span class="material-symbols-outlined icon-sm" :style="{ color: signalColor(reason.score) }">
            {{ signalIcon(reason.signal) }}
          </span>
          <span class="t-label" style="font-weight:700;text-transform:uppercase;letter-spacing:0.05em"
                :style="{ color: signalColor(reason.score) }">
            {{ formatSignal(reason.signal) }}
          </span>
          <span class="badge" :class="scoreBadgeClass(reason.score)" style="margin-left:auto">
            {{ reason.score.toFixed(2) }}
          </span>
        </div>
        <p class="t-label text-muted reason-detail">{{ reason.detail }}</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  anomaly: { type: Object, required: true }
})

const ringColor = computed(() => {
  const s = props.anomaly.anomaly_score
  if (s >= 0.8) return 'var(--col-error)'
  if (s >= 0.6) return 'var(--col-warn)'
  if (s >= 0.4) return 'var(--col-blue)'
  return 'var(--col-text-muted)'
})

const severityClass = computed(() => {
  const s = props.anomaly.anomaly_score
  if (s >= 0.8) return 'severity-high'
  if (s >= 0.6) return 'severity-med'
  return 'severity-low'
})

const severityLabel = computed(() => {
  const s = props.anomaly.anomaly_score
  if (s >= 0.8) return 'High Risk'
  if (s >= 0.6) return 'Medium Risk'
  if (s >= 0.4) return 'Low Risk'
  return 'Minimal'
})

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatSignal(signal) {
  const map = {
    category_spike: 'Category Spike',
    daily_spike:    'Daily Spike',
    lof:            'Anomaly (LOF)',
    amount_outlier: 'Amount Outlier',
  }
  return map[signal] || signal.replace(/_/g, ' ')
}

function signalIcon(signal) {
  const map = {
    category_spike: 'bar_chart',
    daily_spike:    'bolt',
    lof:            'scatter_plot',
    amount_outlier: 'straighten',
  }
  return map[signal] || 'info'
}

function signalColor(score) {
  if (score >= 0.7) return 'var(--col-error)'
  if (score >= 0.4) return 'var(--col-warn)'
  return 'var(--col-blue)'
}

function scoreBadgeClass(score) {
  if (score >= 0.7) return 'badge-error'
  if (score >= 0.4) return 'badge-warn'
  return 'badge-blue'
}
</script>

<style scoped>
.anomaly-card {
  display: flex; flex-direction: column; gap: var(--space-sm);
  padding: var(--space-md);
  border: 1px solid var(--col-border);
  border-radius: var(--r-lg);
  background: var(--col-surface-card);
  transition: border-color var(--dur-fast), box-shadow var(--dur-base);
}
.anomaly-card:hover { box-shadow: var(--shadow-elevated); }

/* Severity border accent */
.severity-high { border-left: 3px solid var(--col-error); }
.severity-med  { border-left: 3px solid var(--col-warn); }
.severity-low  { border-left: 3px solid var(--col-blue); }

/* Top row */
.anomaly-top {
  display: flex; align-items: flex-start; gap: var(--space-sm);
}
.anomaly-meta { flex: 1; min-width: 0; }
.anomaly-amount { text-align: right; flex-shrink: 0; }

/* Score ring */
.score-ring {
  position: relative; width: 46px; height: 46px; flex-shrink: 0;
}
.ring-svg { width: 100%; height: 100%; }
.ring-label {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.5rem; font-weight: 800;
}

/* Score bar */
.score-bar-wrap {
  display: flex; align-items: center; gap: var(--space-sm);
}

/* Reasons */
.reasons-list {
  display: flex; flex-direction: column; gap: 6px;
  border-top: 1px solid var(--col-border);
  padding-top: var(--space-sm);
}
.reason-row {
  background: var(--col-surface-low);
  border-radius: var(--r-sm);
  padding: 6px 8px;
  display: flex; flex-direction: column; gap: 3px;
}
.reason-signal {
  display: flex; align-items: center; gap: 5px;
}
.reason-detail {
  line-height: 1.45;
  padding-left: 23px; /* indent under icon */
}
</style>
