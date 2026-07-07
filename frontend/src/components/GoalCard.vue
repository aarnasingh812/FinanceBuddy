<template>
  <div :class="['goal-card', { 'goal-critical': isCritical }]">

    <!-- Header -->
    <div class="goal-header">
      <div style="min-width:0">
        <div class="t-body" style="font-weight:700;color:var(--col-text-primary)">
          {{ capitaliseName(goal.name) }}
        </div>
        <div class="t-label text-muted" style="margin-top:2px">
          Deadline: {{ goal.deadline }}
          <span v-if="goal.monthsRemaining !== null">· {{ goal.monthsRemaining }}mo left</span>
        </div>
      </div>
      <span :class="['badge', statusBadge]" style="flex-shrink:0">{{ goal.status }}</span>
    </div>

    <!-- Target + remaining -->
    <div class="goal-amounts">
      <div class="goal-amount-block">
        <div class="t-label text-muted">Target</div>
        <div class="t-mono" style="font-weight:700;font-size:0.9rem">{{ fmtCurrency(goal.target) }}</div>
      </div>
      <div class="goal-amount-sep"></div>
      <div class="goal-amount-block">
        <div class="t-label text-muted">Remaining</div>
        <div class="t-mono text-error" style="font-weight:700;font-size:0.9rem">{{ fmtCurrency(goal.remaining) }}</div>
      </div>
      <div class="goal-amount-sep"></div>
      <div class="goal-amount-block">
        <div class="t-label text-muted">Confidence</div>
        <div class="t-mono" :style="{ fontWeight:700, fontSize:'0.9rem', color: goal.confidence > 0 ? 'var(--col-accent)' : 'var(--col-error)' }">
          {{ goal.confidence.toFixed(0) }}%
        </div>
      </div>
    </div>

    <!-- Progress bar -->
    <div>
      <div class="progress-track">
        <div class="progress-fill"
             :style="{ width: Math.max(0, goal.progress) + '%', background: progressColor }">
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:4px;align-items:center">
        <span class="t-label" :style="{ color: isCritical ? 'var(--col-error)' : 'var(--col-text-muted)', fontWeight: isCritical ? 700 : 400 }">
          {{ goal.progress.toFixed(2) }}% progress
        </span>
        <span class="t-label text-muted">
          Saved: <span class="t-mono" :style="{ color: goal.currentSavings < 0 ? 'var(--col-error)' : 'var(--col-accent)' }">
            {{ goal.currentSavings < 0 ? '–' : '' }}{{ fmtCurrency(Math.abs(goal.currentSavings)) }}
          </span>
        </span>
      </div>
    </div>

    <!-- Monthly stats -->
    <div class="goal-stats">
      <div class="goal-stat">
        <div class="t-label text-muted">Monthly Required</div>
        <div class="t-mono" style="font-weight:700;color:var(--col-text-primary)">
          {{ fmtCurrency(goal.monthlyRequired) }}
        </div>
      </div>
      <div class="goal-stat">
        <div class="t-label text-muted">Current Allocation</div>
        <div class="t-mono" :style="{ fontWeight:700, color: goal.currentAlloc === 0 ? 'var(--col-error)' : 'var(--col-accent)' }">
          {{ goal.currentAlloc === 0 ? 'None' : fmtCurrency(goal.currentAlloc) }}
        </div>
      </div>
    </div>

    <!-- Projections -->
    <div class="goal-projections">
      <div class="t-label text-faint" style="margin-bottom:6px;letter-spacing:0.06em">PROJECTIONS</div>
      <div v-for="proj in goal.projections" :key="proj.type" class="proj-row">
        <div class="proj-scenario">
          <span class="proj-dot" :style="{ background: projColor(proj) }"></span>
          <span class="t-body" :style="{ fontWeight:600, color: projColor(proj) }">{{ proj.type }}</span>
        </div>
        <div class="proj-detail">
          <template v-if="proj.achievable">
            <span class="t-mono" style="font-size:0.75rem;font-weight:600;color:var(--col-text-primary)">
              {{ proj.date }}
            </span>
            <span class="badge badge-neutral" style="font-size:0.55rem">{{ proj.monthsToGoal }}mo</span>
          </template>
          <template v-else>
            <span class="t-label text-error" style="font-style:italic;font-weight:600">Not Achievable</span>
            <span class="t-mono text-error" style="font-size:0.7rem">
              {{ fmtRate(proj.monthlySavingsRate) }}/mo
            </span>
          </template>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  goal: { type: Object, required: true }
})

const isCritical = computed(() => props.goal.status === 'Off Track')

const statusBadge = computed(() => {
  if (props.goal.status === 'Off Track') return 'badge badge-error'
  if (props.goal.status === 'On Track')  return 'badge badge-success'
  return 'badge badge-warn'
})

const progressColor = computed(() => {
  if (props.goal.progress <= 0)   return 'var(--col-error)'
  if (props.goal.progress > 60)   return 'var(--col-accent)'
  return 'var(--col-warn)'
})

function projColor (proj) {
  if (proj.type === 'Optimistic')  return proj.achievable ? 'var(--col-accent)' : 'var(--col-error)'
  if (proj.type === 'Realistic')   return proj.achievable ? 'var(--col-blue)'   : 'var(--col-error)'
  return proj.achievable ? 'var(--col-text-muted)' : 'var(--col-error)'
}

function capitaliseName (name) {
  if (!name) return ''
  return name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function fmtRate (v) {
  const sign = v < 0 ? '–' : '+'
  return sign + '$' + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

function fmtCurrency (v) {
  if (v >= 100000) return '$' + (v / 1000).toFixed(0) + 'k'
  if (v >= 10000)  return '$' + (v / 1000).toFixed(1) + 'k'
  return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.goal-card {
  border: 1px solid var(--col-border);
  border-radius: var(--r-lg);
  background: var(--col-surface-card);
  padding: var(--space-md);
  display: flex; flex-direction: column; gap: var(--space-sm);
  transition: border-color var(--dur-base), box-shadow var(--dur-base);
}
.goal-card:hover { border-color: #c8ccd4; box-shadow: var(--shadow-card); }
.goal-critical { border-color: var(--col-error-border); }
.goal-critical:hover { border-color: #e0a0a0; }

.goal-header {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;
}

/* Amount row */
.goal-amounts {
  display: flex; gap: 0;
  background: var(--col-surface-low);
  border-radius: var(--r-md);
  overflow: hidden;
  border: 1px solid var(--col-border);
}
.goal-amount-block {
  flex: 1; padding: 6px 10px; display: flex; flex-direction: column; gap: 2px;
}
.goal-amount-sep {
  width: 1px; background: var(--col-border); flex-shrink: 0;
}

/* Monthly stats */
.goal-stats {
  display: flex; gap: var(--space-lg);
  padding: var(--space-sm) 0;
  border-top: 1px solid var(--col-border);
  border-bottom: 1px solid var(--col-border);
}
.goal-stat { display: flex; flex-direction: column; gap: 2px; }

/* Projections */
.goal-projections { display: flex; flex-direction: column; gap: 5px; }
.proj-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 8px;
  border-radius: var(--r-sm);
  background: var(--col-surface-low);
}
.proj-scenario { display: flex; align-items: center; gap: 6px; }
.proj-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.proj-detail { display: flex; align-items: center; gap: 6px; }
</style>
