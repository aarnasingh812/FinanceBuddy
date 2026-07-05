<template>
  <div class="insights-root">

    <!-- ── Page Header ────────────────────────────────────────── -->
    <div class="page-heading fade-up">
      <div>
        <h1 class="t-display" style="color:var(--col-primary)">Financial Insights</h1>
        <p class="t-body text-muted" style="margin-top:4px">
          AI-driven intelligence and financial planning guidance.
        </p>
      </div>
      <button @click="$emit('trigger-ml-compute')" class="btn btn-primary" :disabled="mlComputing || loading">
        <span class="material-symbols-outlined icon-sm" :class="{ spinning: mlComputing }">sync</span>
        {{ mlComputing ? 'Re-computing…' : 'Refresh Insights' }}
      </button>
    </div>

    <!-- ── Loading State ──────────────────────────────────────── -->
    <div v-if="loading" class="insights-loading fade-up">
      <div class="loading-spinner"></div>
      <p class="t-body text-muted">Loading insights…</p>
    </div>

    <!-- ── Empty / No Data State ──────────────────────────────── -->
    <div v-else-if="!insightsApi || noData" class="insights-empty fade-up">
      <span class="material-symbols-outlined" style="font-size:48px;color:var(--col-text-faint)">analytics</span>
      <div class="t-title" style="margin-top:var(--space-md)">No Insights Available</div>
      <p class="t-body text-muted" style="margin-top:var(--space-sm);max-width:420px;text-align:center;margin-bottom:var(--space-md)">
        {{ insightsApi?.message || "Click 'Refresh Insights' above to compute ML features and generate personalised insights." }}
      </p>
      <button @click="$emit('trigger-ml-compute')" class="btn btn-primary" :disabled="mlComputing || loading">
        <span class="material-symbols-outlined icon-sm" :class="{ spinning: mlComputing }">sync</span>
        {{ mlComputing ? 'Re-computing…' : 'Compute Insights' }}
      </button>
    </div>

    <!-- ── Main Insights Content ──────────────────────────────── -->
    <template v-else>

    <!-- ── Critical Alert Banner ─────────────────────────────── -->
    <div v-if="portfolioInsight" class="alert-banner-insights fade-up">
      <div class="alert-left">
        <h2 class="t-headline" style="margin-bottom:4px">Critical Alert: Financial Health</h2>
        <div style="display:flex;align-items:center;gap:8px">
          <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-error)">warning</span>
          <p class="t-body">{{ portfolioInsight?.insight }}</p>
        </div>
      </div>
      <div v-if="insightsApi.spend_optimization" class="alert-stat-box">
        <div class="t-label" style="opacity:.8;letter-spacing:.06em;text-transform:uppercase">Avg Monthly Savings</div>
        <div class="t-headline" style="font-weight:700;margin-top:4px;font-feature-settings:'tnum'">
          –₹{{ fmt(Math.abs(insightsApi.spend_optimization.monthly_expense_avg - insightsApi.spend_optimization.monthly_income_avg)) }}/mo
        </div>
      </div>
    </div>

    <!-- ── Summary Stats ──────────────────────────────────────── -->
    <div v-if="insightsApi.spend_optimization || insightsApi.savings_opportunities" class="summary-grid fade-up" style="animation-delay:60ms">
      <div v-if="insightsApi.spend_optimization" class="summary-stat card">
        <div class="t-label text-muted" style="margin-bottom:4px">Avg Monthly Expense</div>
        <div class="t-metric">₹{{ fmt(insightsApi.spend_optimization.monthly_expense_avg) }}</div>
      </div>
      <div v-if="insightsApi.spend_optimization" class="summary-stat card">
        <div class="t-label text-muted" style="margin-bottom:4px">Current Month Expense</div>
        <div class="t-metric">₹{{ fmt(insightsApi.spend_optimization.current_month_expense) }}</div>
        <div v-if="currentMonthVsAvgPct !== null" class="t-label" :class="currentMonthVsAvgPct > 0 ? 'text-error' : 'text-accent'" style="margin-top:4px;font-weight:600">
          {{ currentMonthVsAvgPct > 0 ? '▲' : '▼' }} {{ Math.abs(currentMonthVsAvgPct) }}% vs avg
        </div>
      </div>
      <div v-if="insightsApi.spend_optimization" class="summary-stat card">
        <div class="t-label text-muted" style="margin-bottom:4px">Avg Monthly Income</div>
        <div class="t-metric">₹{{ fmt(insightsApi.spend_optimization.monthly_income_avg) }}</div>
      </div>
      <div v-if="insightsApi.savings_opportunities" class="summary-stat card highlight-recovery">
        <div class="t-label" style="margin-bottom:4px;color:var(--col-accent)">Potential Monthly Recovery</div>
        <div class="t-metric text-accent">₹{{ fmt(insightsApi.savings_opportunities.total_potential_monthly_savings) }}</div>
        <div class="t-label text-muted" style="margin-top:4px">
          {{ (insightsApi.savings_opportunities.recommendations || []).length }} savings identified
        </div>
      </div>
    </div>

    <!-- ── Middle Row: Opportunities + Trends ────────────────── -->
    <div v-if="insightsApi.savings_opportunities || insightsApi.spend_optimization" class="middle-grid fade-up" style="animation-delay:120ms">

      <!-- Savings Opportunities table (2/3) -->
      <div v-if="insightsApi.savings_opportunities && (insightsApi.savings_opportunities.recommendations || []).length" class="card opps-card">
        <div class="opps-header">
          <div class="t-title">Savings Opportunities</div>
          <span class="badge badge-success">
            Total ₹{{ fmt(insightsApi.savings_opportunities.total_potential_monthly_savings) }}/mo
          </span>
        </div>

        <div class="opps-table-wrap">
          <table class="opps-table">
            <thead>
              <tr>
                <th>Recommendation</th>
                <th>Type</th>
                <th>Priority</th>
                <th class="text-right">Monthly Saving</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in insightsApi.savings_opportunities.recommendations"
                  :key="rec.title"
                  class="opp-row">
                <td class="opp-main">
                  <div class="t-body" style="font-weight:600">{{ rec.title }}</div>
                  <div class="t-label text-muted opp-detail">{{ rec.detail }}</div>
                </td>
                <td>
                  <span class="badge badge-neutral" style="text-transform:capitalize">
                    {{ rec.type === 'anomaly_reduction' ? 'Anomaly' : 'Discretionary' }}
                  </span>
                </td>
                <td>
                  <span :class="['badge', rec.priority === 'high' ? 'badge-error' : 'badge-warn']"
                        style="text-transform:capitalize">
                    {{ rec.priority }}
                  </span>
                </td>
                <td class="opp-saving">
                  <div class="t-mono text-accent" style="font-weight:700;font-size:0.9rem">
                    +₹{{ fmt(rec.estimated_monthly_savings) }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Right column: Top Categories + Rising Spend -->
      <div v-if="insightsApi.spend_optimization" class="side-col">

        <!-- Top categories -->
        <div v-if="(insightsApi.spend_optimization.top_categories || []).length" class="card">
          <div class="t-title" style="margin-bottom:var(--space-md)">Top Spend Categories</div>
          <div class="categories-list">
            <div v-for="cat in insightsApi.spend_optimization.top_categories"
                 :key="cat.category" class="cat-row">
              <div class="cat-label-row">
                <span class="t-body" style="font-weight:600;text-transform:capitalize">
                  {{ cat.category }}
                </span>
                <div style="display:flex;align-items:baseline;gap:6px">
                  <span class="t-mono" style="font-size:0.8rem;font-weight:700">
                    ₹{{ fmtK(cat.avg_monthly_spend) }}
                  </span>
                  <span class="t-label text-muted" style="font-size:0.65rem">
                    avg/mo
                  </span>
                </div>
              </div>
              <div class="progress-track">
                <div class="progress-fill"
                     :style="{ width: catWidth(cat.avg_monthly_spend) + '%', background: catColor(cat) }">
                </div>
              </div>
              <div class="cat-meta">
                <span class="t-label text-muted" style="font-size:0.7rem">
                  This month: ₹{{ fmtK(cat.current_month_spend) }}
                </span>
                <span v-if="cat.month_over_month_change_percent != null"
                      :class="['t-label', 'mom-badge', cat.month_over_month_change_percent > 0 ? 'mom-up' : cat.month_over_month_change_percent < 0 ? 'mom-down' : '']">
                  {{ cat.month_over_month_change_percent > 0 ? '+' : '' }}{{ cat.month_over_month_change_percent }}%
                </span>
                <span :class="['t-label', trendClass(cat.trend)]">{{ cat.trend }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Rising spend -->
        <div v-if="(insightsApi.spend_optimization.rising_spend_categories || []).length" class="card rising-card">
          <div class="card-header-row">
            <div class="t-title">Rising Spend</div>
            <span class="badge badge-error">{{ insightsApi.spend_optimization.rising_spend_categories.length }} categories</span>
          </div>
          <div class="rising-chips">
            <div v-for="cat in insightsApi.spend_optimization.rising_spend_categories"
                 :key="cat.category" class="rising-chip">
              <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-error)">trending_up</span>
              <div style="flex:1">
                <div class="t-body" style="font-weight:600;text-transform:capitalize;font-size:0.8rem">
                  {{ cat.category }}
                </div>
                <div class="t-mono text-muted" style="font-size:0.7rem">
                  Avg ₹{{ fmtK(cat.avg_monthly) }}/mo
                </div>
              </div>
              <div class="t-mono" style="font-size:0.75rem;font-weight:700;color:var(--col-error);white-space:nowrap">
                ₹{{ fmtK(cat.current_month) }}
                <span class="t-label text-muted" style="font-weight:400;font-size:0.6rem">this mo</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- ── LLM Insights Section ───────────────────────────────── -->
    <section v-if="insightsApi.llm_insights" class="fade-up" style="animation-delay:160ms">

      <!-- Overall Summary -->
      <div v-if="insightsApi.llm_insights.overall_summary" class="card llm-summary-card">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:var(--space-md)">
          <span class="material-symbols-outlined icon-sm" style="color:var(--col-accent)">smart_toy</span>
          <div class="t-title">AI-Powered Summary</div>
        </div>
        <p class="t-body" style="line-height:1.7;color:var(--col-text-secondary)">{{ insightsApi.llm_insights.overall_summary }}</p>
      </div>

      <!-- Savings Narrative -->
      <div v-if="insightsApi.llm_insights.savings_narrative" class="card llm-narrative-card" style="margin-top:var(--space-lg)">
        <div class="t-title" style="margin-bottom:var(--space-sm)">
          {{ insightsApi.llm_insights.savings_narrative.headline || 'Savings Narrative' }}
        </div>
        <div v-if="(insightsApi.llm_insights.savings_narrative.personalized_tips || []).length" class="llm-tips-list">
          <div v-for="tip in insightsApi.llm_insights.savings_narrative.personalized_tips"
               :key="tip.rec_index" class="llm-tip-item">
            <div class="t-body" style="font-weight:600;font-size:0.85rem">{{ tip.personalized_detail }}</div>
            <div v-if="tip.motivation" class="t-label text-accent" style="margin-top:4px;font-style:italic">
              💡 {{ tip.motivation }}
            </div>
          </div>
        </div>
        <div v-if="insightsApi.llm_insights.savings_narrative.coaching_note" class="llm-coaching-note">
          <span class="material-symbols-outlined icon-sm" style="color:var(--col-warn);flex-shrink:0">tips_and_updates</span>
          <p class="t-body" style="font-size:0.8125rem;color:var(--col-text-secondary)">
            {{ insightsApi.llm_insights.savings_narrative.coaching_note }}
          </p>
        </div>
      </div>

      <!-- Spend Narrative -->
      <div v-if="insightsApi.llm_insights.spend_narrative" class="card llm-narrative-card" style="margin-top:var(--space-lg)">
        <div class="t-title" style="margin-bottom:var(--space-sm)">
          {{ insightsApi.llm_insights.spend_narrative.headline || 'Spending Analysis' }}
        </div>
        <div v-if="(insightsApi.llm_insights.spend_narrative.category_insights || []).length" class="llm-category-insights">
          <div v-for="ci in insightsApi.llm_insights.spend_narrative.category_insights"
               :key="ci.category" class="llm-cat-insight">
            <div class="t-label" style="font-weight:700;text-transform:capitalize;color:var(--col-text-primary)">{{ ci.category }}</div>
            <p class="t-body" style="font-size:0.8125rem;color:var(--col-text-secondary);margin-top:2px">{{ ci.narrative }}</p>
          </div>
        </div>
        <div v-if="insightsApi.llm_insights.spend_narrative.trend_alert" class="llm-trend-alert">
          <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-error);flex-shrink:0">trending_up</span>
          <p class="t-body" style="font-size:0.8125rem;font-weight:600">{{ insightsApi.llm_insights.spend_narrative.trend_alert }}</p>
        </div>
      </div>

      <!-- Goal Narratives -->
      <div v-if="(insightsApi.llm_insights.goal_narratives || []).length" class="llm-goal-narratives" style="margin-top:var(--space-lg)">
        <div class="t-headline" style="margin-bottom:var(--space-md)">Personalised Goal Coaching</div>
        <div class="llm-goal-grid">
          <div v-for="gn in insightsApi.llm_insights.goal_narratives"
               :key="gn.goal_id" class="card llm-goal-card">
            <div class="t-title" style="text-transform:capitalize;margin-bottom:var(--space-sm)">
              {{ getGoalName(gn.goal_id) || `Goal #${gn.goal_id}` }}
            </div>
            <p class="t-body" style="font-size:0.8125rem;color:var(--col-text-secondary);line-height:1.6">
              {{ gn.personalized_insight }}
            </p>
            <div v-if="(gn.action_plan || []).length" class="gi-actions" style="margin-top:var(--space-sm)">
              <div class="t-label" style="font-weight:700;letter-spacing:.05em;margin-bottom:6px;color:var(--col-accent)">
                ACTION PLAN
              </div>
              <ul class="action-list">
                <li v-for="(item, i) in gn.action_plan" :key="i" class="action-item">
                  <span class="action-dot" style="background:var(--col-accent)"></span>
                  <span class="t-body" style="font-size:0.8125rem">{{ item }}</span>
                </li>
              </ul>
            </div>
            <div v-if="gn.encouragement" class="llm-encouragement">
              <span class="t-label text-accent" style="font-style:italic">🎯 {{ gn.encouragement }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Goal Insights ──────────────────────────────────────── -->
    <section v-if="(insightsApi.goal_insights || []).length" class="fade-up" style="animation-delay:200ms">
      <div class="section-header" style="margin-bottom:var(--space-md)">
        <div class="t-headline">Goal Insights</div>
        <span class="badge badge-error">
          {{ insightsApi.goal_insights.filter(g => g.status === 'off_track').length }} off track
        </span>
      </div>

      <div class="goal-insights-grid">
        <div v-for="goal in goalForecasts" :key="goal.goal_id" class="goal-insight-card">

          <!-- Header -->
          <div class="gi-header">
            <div>
              <div class="t-title" style="text-transform:capitalize">{{ goal.goal_name }}</div>
              <div class="t-label text-muted" style="margin-top:2px">
                Progress: <span :style="{ color: goal.progress_percent < 0 ? 'var(--col-error)' : 'var(--col-accent)' }">
                  {{ goal.progress_percent?.toFixed(2) }}%
                </span>
              </div>
            </div>
            <span :class="['badge', goal.status === 'off_track' ? 'badge-error' : 'badge-success']"
                  style="text-transform:capitalize">
              {{ goal.status.replace('_', ' ') }}
            </span>
          </div>

          <!-- Extra time needed -->
          <div v-if="goal.extra_time_needed_months" class="t-label text-warn" style="font-weight:600">
            ⏰ {{ goal.extra_time_needed_months }} extra month{{ goal.extra_time_needed_months > 1 ? 's' : '' }} needed
          </div>

          <!-- Insight text -->
          <div class="gi-insight">
            <span class="material-symbols-outlined icon-sm" style="color:var(--col-warn);flex-shrink:0;margin-top:1px">info</span>
            <p class="t-body" style="font-size:0.8125rem;color:var(--col-text-secondary)">{{ goal.insight }}</p>
          </div>

          <!-- Action items -->
          <div v-if="goal.action_items?.length" class="gi-actions">
            <div class="t-label text-error" style="font-weight:700;letter-spacing:.05em;margin-bottom:6px">
              ACTION ITEMS
            </div>
            <ul class="action-list">
              <li v-for="(item, i) in goal.action_items" :key="i" class="action-item">
                <span class="action-dot"></span>
                <span class="t-body" style="font-size:0.8125rem">{{ item }}</span>
              </li>
            </ul>
          </div>

        </div>
      </div>
    </section>

    <!-- ── LLM footer ─────────────────────────────────────────── -->
    <div v-if="insightsApi.llm_insights" class="llm-footer fade-up" style="animation-delay:260ms">
      <span class="material-symbols-outlined icon-sm text-faint">smart_toy</span>
      <span class="t-label text-faint">
        Insights generated by {{ insightsApi.llm_insights.model_used }} ·
        {{ fmtTs(insightsApi.llm_insights.generated_at) }}
      </span>
    </div>

    <!-- ── Computed At footer (when no LLM) ────────────────────── -->
    <div v-else-if="insightsApi.computed_at" class="llm-footer fade-up" style="animation-delay:260ms">
      <span class="material-symbols-outlined icon-sm text-faint">schedule</span>
      <span class="t-label text-faint">
        Computed {{ fmtTs(insightsApi.computed_at) }}
      </span>
    </div>

    </template><!-- /main content -->

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  insightsData: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  mlComputing: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['trigger-ml-compute'])

// ── API response (from parent via props) ─────────────────────────
const insightsApi = computed(() => props.insightsData)

// Check if the API returned data but all sections are null (no ML results yet)
const noData = computed(() => {
  if (!insightsApi.value) return true
  const d = insightsApi.value
  return !d.savings_opportunities && !d.spend_optimization && !d.goal_insights && !d.llm_insights
})

// Portfolio summary (first item with goal_id null)
const portfolioInsight = computed(() =>
  (insightsApi.value?.goal_insights || []).find(g => g.goal_id === null)
)

// Only individual goal forecasts (not the summary row)
const goalForecasts = computed(() =>
  (insightsApi.value?.goal_insights || []).filter(g => g.goal_id !== null)
)

// Current month expense vs avg percentage
const currentMonthVsAvgPct = computed(() => {
  const so = insightsApi.value?.spend_optimization
  if (!so || so.monthly_expense_avg == null || so.current_month_expense == null) return null
  if (so.monthly_expense_avg === 0) return null
  return Math.round(((so.current_month_expense - so.monthly_expense_avg) / so.monthly_expense_avg) * 100)
})

// Helpers
function fmt(v) {
  if (v == null) return '0.00'
  return Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtK(v) {
  if (v == null) return '0k'
  if (v >= 100000) return (v / 1000).toFixed(0) + 'k'
  if (v >= 10000)  return (v / 1000).toFixed(1) + 'k'
  return (v / 1000).toFixed(1) + 'k'
}
function fmtTs(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

// Category bar width relative to max
const maxCatSpend = computed(() => {
  const cats = insightsApi.value?.spend_optimization?.top_categories || []
  if (!cats.length) return 1
  return Math.max(...cats.map(c => c.avg_monthly_spend))
})
function catWidth(spend) {
  return Math.round((spend / maxCatSpend.value) * 100)
}
function catColor(cat) {
  if (cat.trend === 'falling') return 'var(--col-accent)'
  if (cat.trend === 'rising')  return 'var(--col-error)'
  return 'var(--col-blue)'
}
function trendClass(trend) {
  if (trend === 'falling') return 'text-accent'
  if (trend === 'rising')  return 'text-error'
  return 'text-muted'
}

// Helper to find goal name from goal_insights by ID (for LLM goal narratives)
function getGoalName(goalId) {
  const goals = insightsApi.value?.goal_insights || []
  const match = goals.find(g => g.goal_id === goalId)
  return match?.goal_name || null
}
</script>

<style scoped>
.insights-root {
  display: flex; flex-direction: column; gap: var(--space-xl);
}

/* Loading state */
.insights-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-md);
  padding: var(--space-2xl) 0;
  min-height: 300px;
}
.loading-spinner {
  width: 40px; height: 40px;
  border: 3px solid var(--col-border);
  border-top-color: var(--col-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty state */
.insights-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: var(--space-2xl) var(--space-xl);
  min-height: 300px;
  background: var(--col-surface-card);
  border: 1px dashed var(--col-border);
  border-radius: var(--r-xl);
}

/* Alert banner */
.alert-banner-insights {
  display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-lg);
  padding: var(--space-lg);
  background: var(--col-error-bg);
  border: 1px solid var(--col-error-border);
  border-radius: var(--r-xl);
}
@media (max-width: 700px) { .alert-banner-insights { flex-direction: column; } }
.alert-stat-box {
  flex-shrink: 0;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(8px);
  padding: var(--space-md);
  border-radius: var(--r-lg);
  border: 1px solid var(--col-error-border);
  text-align: right;
}

/* Summary stats */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-lg);
}
@media (max-width: 1000px) { .summary-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) { .summary-grid { grid-template-columns: 1fr; } }
.summary-stat { display: flex; flex-direction: column; }
.highlight-recovery {
  border-color: var(--col-accent-light) !important;
  background: linear-gradient(135deg, #fff 60%, var(--col-accent-light));
}

/* Middle grid */
.middle-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: var(--space-lg);
  align-items: start;
}
@media (max-width: 1100px) { .middle-grid { grid-template-columns: 1fr; } }

/* Opportunities card */
.opps-card { padding: 0; overflow: hidden; }
.opps-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--col-border);
}
.opps-table-wrap { overflow-x: auto; }
.opps-table {
  width: 100%; border-collapse: collapse;
  font-size: 0.8125rem;
}
.opps-table thead tr {
  border-bottom: 1px solid var(--col-border);
}
.opps-table th {
  padding: 10px 16px;
  text-align: left;
  font-size: 0.625rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--col-text-faint);
  white-space: nowrap;
}
.opp-row {
  border-bottom: 1px solid var(--col-border-muted);
  transition: background var(--dur-fast), transform var(--dur-fast);
  cursor: pointer;
}
.opp-row:last-child { border-bottom: none; }
.opp-row:hover {
  background: var(--col-surface-low);
  transform: translateX(4px);
}
.opp-row td { padding: 12px 16px; vertical-align: top; }
.opp-main { max-width: 340px; }
.opp-detail {
  margin-top: 3px; line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.opp-saving { text-align: right; white-space: nowrap; }

/* Side column */
.side-col { display: flex; flex-direction: column; gap: var(--space-md); }

/* Categories */
.categories-list { display: flex; flex-direction: column; gap: var(--space-sm); }
.cat-row { display: flex; flex-direction: column; gap: 4px; }
.cat-label-row { display: flex; justify-content: space-between; align-items: baseline; }
.cat-meta { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }

/* Month-over-month badge */
.mom-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--r-sm);
}
.mom-up {
  color: var(--col-error);
  background: var(--col-error-bg);
}
.mom-down {
  color: var(--col-accent);
  background: var(--col-accent-light);
}

/* Rising spend */
.rising-card {}
.card-header-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: var(--space-md);
}
.rising-chips { display: flex; flex-direction: column; gap: 8px; }
.rising-chip {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px;
  background: var(--col-error-bg);
  border: 1px solid var(--col-error-border);
  border-radius: var(--r-md);
}

/* LLM Insights */
.llm-summary-card {
  border-left: 4px solid var(--col-accent);
}
.llm-narrative-card {
  border-left: 4px solid var(--col-blue);
}
.llm-tips-list {
  display: flex; flex-direction: column; gap: var(--space-sm);
}
.llm-tip-item {
  padding: var(--space-sm) var(--space-md);
  background: var(--col-surface-low);
  border-radius: var(--r-md);
  border: 1px solid var(--col-border-muted);
}
.llm-coaching-note {
  display: flex; gap: 6px; align-items: flex-start;
  padding: var(--space-sm) var(--space-md);
  background: var(--col-warn-bg);
  border: 1px solid #fde68a;
  border-radius: var(--r-md);
  margin-top: var(--space-sm);
}
.llm-category-insights {
  display: flex; flex-direction: column; gap: var(--space-sm);
}
.llm-cat-insight {
  padding: var(--space-sm) var(--space-md);
  background: var(--col-surface-low);
  border-radius: var(--r-md);
  border: 1px solid var(--col-border-muted);
}
.llm-trend-alert {
  display: flex; gap: 6px; align-items: center;
  padding: var(--space-sm) var(--space-md);
  background: var(--col-error-bg);
  border: 1px solid var(--col-error-border);
  border-radius: var(--r-md);
  margin-top: var(--space-sm);
}
.llm-goal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-md);
}
.llm-goal-card {
  border-left: 4px solid var(--col-accent);
}
.llm-encouragement {
  margin-top: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  background: linear-gradient(135deg, var(--col-accent-light) 0%, transparent 100%);
  border-radius: var(--r-md);
}

/* Goal insights grid */
.section-header { display: flex; align-items: center; gap: var(--space-sm); }
.goal-insights-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
}
@media (max-width: 1000px) { .goal-insights-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 640px)  { .goal-insights-grid { grid-template-columns: 1fr; } }

.goal-insight-card {
  display: flex; flex-direction: column; gap: var(--space-sm);
  padding: var(--space-md);
  background: var(--col-surface-card);
  border: 1px solid var(--col-border);
  border-left: 4px solid var(--col-error);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--dur-base);
}
.goal-insight-card:hover { box-shadow: var(--shadow-elevated); }

.gi-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.gi-insight {
  display: flex; gap: 6px; align-items: flex-start;
  padding: 8px 10px;
  background: var(--col-warn-bg);
  border: 1px solid #fde68a;
  border-radius: var(--r-md);
}
.gi-actions {
  padding: 10px 12px;
  background: var(--col-error-bg);
  border: 1px solid var(--col-error-border);
  border-radius: var(--r-md);
}
.action-list { display: flex; flex-direction: column; gap: 6px; list-style: none; }
.action-item { display: flex; align-items: flex-start; gap: 8px; }
.action-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--col-error);
  flex-shrink: 0; margin-top: 6px;
}

/* LLM footer */
.llm-footer {
  display: flex; align-items: center; gap: 6px;
  padding: var(--space-sm) 0;
  border-top: 1px solid var(--col-border);
}

/* Page heading */
.page-heading {
  display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: var(--space-md);
  margin-bottom: var(--space-md);
}

/* Spinning animation */
.spinning {
  animation: spin 1s linear infinite;
}
</style>
