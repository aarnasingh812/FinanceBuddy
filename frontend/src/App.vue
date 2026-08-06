<template>
  <div class="app-root">
    <!-- ── Toast notification ──────────────────────────────────── -->
    <Transition name="toast">
      <div
        v-if="toast"
        :class="['toast-popup', `toast-${toast.type}`]"
        role="alert"
        aria-live="assertive"
      >
        <span class="toast-icon">
          {{ toast.type === 'warning' ? '⚠️' : toast.type === 'error' ? '❌' : 'ℹ️' }}
        </span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="dismissToast" aria-label="Dismiss">✕</button>
      </div>
    </Transition>
    <!-- Login screen -->
    <LoginPage
      v-if="currentScreen === 'login'"
      @go-register="currentScreen = 'register'"
      @logged-in="handleLoggedIn"
    />

    <!-- Register screen -->
    <RegisterPage
      v-if="currentScreen === 'register'"
      @go-login="currentScreen = 'login'"
      @registered="handleRegistered"
    />

    <!-- Main app -->
    <template v-if="currentScreen === 'app'">
    <AppHeader :active-page="activePage" :user="currentUser" @navigate="activePage = $event" @logout="handleLogout" />

    <main class="dashboard">
      <!-- Insights page -->
      <div v-if="activePage === 'Actionable Insights'" class="dash-inner" style="padding-top:var(--space-xl)">
        <InsightsPage
          :insights-data="insightsData"
          :loading="insightsLoading"
          :ml-computing="mlComputing"
          @trigger-ml-compute="triggerMlCompute"
        />
      </div>

      <!-- Transactions page -->
      <div v-if="activePage === 'Transactions'" class="dash-inner" style="padding-top:var(--space-xl)">
        <TransactionsPage />
      </div>

      <!-- Goals page -->
      <div v-if="activePage === 'Goals'" class="dash-inner" style="padding-top:var(--space-xl)">
        <GoalsPage />
      </div>

      <!-- Dashboard page -->
      <div v-if="activePage === 'Dashboard'">
      <div class="dash-inner">

        <!-- ── Page heading ──────────────────────────────── -->
        <div class="page-heading fade-up">
          <div>
            <h1 class="t-display" style="color:var(--col-primary)">Dashboard</h1>
            <p class="t-body text-muted">{{ dashboardMonthLabel }} · Last updated {{ lastUpdatedLabel }}</p>
          </div>
          <div class="heading-actions">
            <div class="month-toggle">
              <button
                :class="['month-toggle-btn', { active: dashboardMonthMode === 'current' }]"
                @click="switchDashboardMonth('current')"
              >
                <span class="material-symbols-outlined icon-xs">today</span>
                Current Month
              </button>
              <button
                :class="['month-toggle-btn', { active: dashboardMonthMode === 'last' }]"
                @click="switchDashboardMonth('last')"
              >
                <span class="material-symbols-outlined icon-xs">event</span>
                Last Month
              </button>
            </div>
          </div>
        </div>

        <!-- Onboarding banner for new user (no data in DB) -->
        <div v-if="dashboardData && !dashboardData.has_transactions" class="info-banner fade-up" style="animation-delay:50ms">
          <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-blue)">info</span>
          <span class="t-body" style="font-weight:600">Upload your last 2 months of transactions to unlock personalized guidance from your Finance Buddy.</span>
          <button class="btn btn-primary" style="margin-left:auto;padding:6px 12px;font-size:0.75rem;font-weight:600" @click="activePage = 'Transactions'">
            Go to Transactions
          </button>
        </div>

        <!-- ── Alert banner (overspent) ─────────────────── -->
        <div v-if="dashboardSummary.net_savings < 0" class="alert-banner fade-up" style="animation-delay:50ms">
          <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-error)">warning</span>
          <span class="t-body" style="font-weight:600">{{ dashboardMonthMode === 'last' ? 'You overspent last month.' : "You're overspending this month." }}</span>
          <span class="t-body text-muted">Expenses exceed income by {{ fmtCurrency(Math.abs(dashboardSummary.net_savings)) }} — check your Goal Forecast below.</span>
          <button class="btn btn-ghost" style="margin-left:auto;padding:4px 10px;font-size:0.75rem">
            Review Goals
          </button>
        </div>

        <!-- ── Metric cards ───────────────────────────────── -->
        <section class="metrics-grid">
          <MetricCard
            label="This month's Income"
            :value="fmtCurrency(dashboardSummary.total_income)"
            icon="trending_up"
            :delta="fmtDelta(dashboardSummary.income_change_pct)"
            variant="income"
            :delay="0"
          />
          <MetricCard
            label="This month's Expenses"
            :value="fmtCurrency(dashboardSummary.total_expense)"
            icon="trending_down"
            :delta="fmtDelta(dashboardSummary.expense_change_pct)"
            variant="expense"
            :delay="80"
          />
          <MetricCard
            label="Net Savings"
            :value="dashboardSummary.net_savings < 0 ? `–${fmtCurrency(Math.abs(dashboardSummary.net_savings))}` : fmtCurrency(dashboardSummary.net_savings)"
            icon="account_balance_wallet"
            :delta="dashboardSummary.net_savings < 0 ? 'Overspent' : fmtDelta(dashboardSummary.savings_change_pct)"
            :variant="dashboardSummary.net_savings < 0 ? 'negative' : 'savings'"
            :delay="160"
          />
        </section>

        <!-- ── Charts row ─────────────────────────────────── -->
        <div class="charts-grid">

          <!-- Expense Overview -->
          <div class="card fade-up" style="animation-delay:100ms">
            <div class="card-header">
              <div>
                <div class="t-title">Expense Overview</div>
                <div class="t-label text-muted" style="margin-top:2px">Weekly breakdown · April 2026</div>
              </div>
              <div class="tab-strip">
                <button v-for="t in ['1M','3M','6M']" :key="t"
                        :class="['tab-btn', { active: expenseTab === t }]"
                        @click="expenseTab = t">{{ t }}</button>
              </div>
            </div>
            <LineChart
              :labels="expenseChartData.labels"
              :datasets="expenseChartData.datasets"
              :height="200"
            />
          </div>

          <!-- Savings Trend -->
          <div class="card fade-up" style="animation-delay:160ms">
            <div class="card-header">
              <div>
                <div class="t-title">Savings Trend</div>
                <div class="t-label text-muted" style="margin-top:2px">Monthly trajectory</div>
              </div>
              <div class="tab-strip">
                <button v-for="t in ['1M','3M','6M']" :key="t"
                        :class="['tab-btn', { active: savingsTab === t }]"
                        @click="savingsTab = t">{{ t }}</button>
              </div>
            </div>
            <LineChart
              :labels="savingsChartData.labels"
              :datasets="savingsChartData.datasets"
              :height="200"
            />
          </div>

        </div>

        <!-- ── Spending breakdown + Allocation ──────────── -->
        <div class="breakdown-row">

          <!-- Donut breakdown -->
          <div class="card breakdown-card fade-up" style="animation-delay:200ms">
            <div class="t-title" style="margin-bottom:var(--space-md)">Spending Breakdown</div>
            <div v-if="spendingSegments.length" class="breakdown-inner">
              <DonutChart
                :segments="spendingSegments"
                :center-label="spendingCenterLabel"
              />
              <div class="segment-legend">
                <div v-for="seg in spendingSegments" :key="seg.label" class="legend-row">
                  <div class="legend-dot" :style="{ background: seg.color }"></div>
                  <div class="legend-label t-label text-muted">{{ seg.label }}</div>
                  <div class="legend-value t-mono">{{ fmtCurrency(seg.value) }}</div>
                  <div class="legend-pct t-label text-faint">
                    {{ Math.round(seg.value / spendingTotal * 100) }}%
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="t-body text-muted" style="padding:var(--space-xl) 0;text-align:center">
              No expenses this month
            </div>
          </div>
        </div>

      </div>
      </div><!-- /dashboard -->
    </main>
    </template><!-- /main app -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import LoginPage        from './components/LoginPage.vue'
import RegisterPage     from './components/RegisterPage.vue'
import AppHeader        from './components/AppHeader.vue'
import MetricCard       from './components/MetricCard.vue'
import LineChart        from './components/LineChart.vue'
import DonutChart       from './components/DonutChart.vue'
import InsightsPage     from './components/InsightsPage.vue'
import TransactionsPage from './components/TransactionsPage.vue'
import GoalsPage        from './components/GoalsPage.vue'

// ── Screen routing & Auth state ──────────────────────────────────
const currentScreen = ref('login')
const activePage    = ref('Dashboard')
const currentUser   = ref(null)

// ── Toast notification ───────────────────────────────────────────
const toast = ref(null)   // { message, type: 'warning'|'error'|'info' }
let toastTimer = null

function showToast(message, type = 'warning', durationMs = 8000) {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { message, type }
  toastTimer = setTimeout(() => { toast.value = null }, durationMs)
}
function dismissToast() {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = null
}

function handleUnauthorized() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  currentUser.value = null
  currentScreen.value = 'login'
}

// ── Fetch Interceptor for HTTP cookies and automatic token refreshing ──
const originalFetch = window.fetch
let isRefreshing = false
let refreshSubscribers = []

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb)
}

function onRefreshed(token) {
  refreshSubscribers.forEach(cb => cb(token))
  refreshSubscribers = []
}

window.fetch = async function (url, options = {}) {
  const urlString = typeof url === 'string' ? url : (url instanceof Request ? url.url : '')

  if (urlString.includes('/api/token/refresh/')) {
    return originalFetch(url, options)
  }

  if (urlString.includes('http://localhost:8000/api/')) {
    options.credentials = 'include'
  }

  let res = await originalFetch(url, options)

  if (res.status === 401 && urlString.includes('http://localhost:8000/api/')) {
    if (!isRefreshing) {
      isRefreshing = true
      try {
        const refreshRes = await originalFetch('http://localhost:8000/api/token/refresh/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        })
        if (refreshRes.ok) {
          const data = await refreshRes.json()
          localStorage.setItem('access_token', data.access)
          isRefreshing = false
          onRefreshed(data.access)
        } else {
          isRefreshing = false
          handleUnauthorized()
          return res
        }
      } catch (err) {
        isRefreshing = false
        handleUnauthorized()
        return res
      }
    }

    const retryWithNewToken = new Promise((resolve) => {
      subscribeTokenRefresh((token) => {
        const newOptions = { ...options }
        if (newOptions.headers) {
          if (newOptions.headers instanceof Headers) {
            newOptions.headers.set('Authorization', `Bearer ${token}`)
          } else if (Array.isArray(newOptions.headers)) {
            const idx = newOptions.headers.findIndex(h => h[0].toLowerCase() === 'authorization')
            if (idx > -1) newOptions.headers[idx][1] = `Bearer ${token}`
            else newOptions.headers.push(['Authorization', `Bearer ${token}`])
          } else {
            newOptions.headers['Authorization'] = `Bearer ${token}`
          }
        } else {
          newOptions.headers = { 'Authorization': `Bearer ${token}` }
        }
        resolve(originalFetch(url, newOptions))
      })
    })

    return retryWithNewToken
  }

  return res
}

onMounted(async () => {
  const token = localStorage.getItem('access_token')
  const userJson = localStorage.getItem('user')
  if (token && userJson) {
    try {
      currentUser.value = JSON.parse(userJson)
      // Validate token by making a test API call before showing the app
      const resp = await fetch('http://localhost:8000/api/finance-buddy/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        dashboardData.value = await resp.json()
        lastUpdated.value = new Date()
        currentScreen.value = 'app'
      } else {
        // Token expired or invalid — force login
        handleUnauthorized()
      }
    } catch (e) {
      // Network error or bad JSON — force login
      handleUnauthorized()
    }
  }
})

function handleLoggedIn(user) {
  currentUser.value = user
  currentScreen.value = 'app'
  fetchDashboard()
}

function handleRegistered(user) {
  currentUser.value = user
  currentScreen.value = 'app'
  fetchDashboard()
}

async function handleLogout() {
  const accessToken = localStorage.getItem('access_token')

  // Clear local state first for immediate UI response
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  currentUser.value = null
  currentScreen.value = 'login'

  if (accessToken) {
    try {
      await fetch('http://localhost:8000/api/finance-buddy/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        }
      })
    } catch (err) {
      console.error('Logout API failed:', err)
    }
  }
}

const dashboardData = ref(null)
const dashboardLoading = ref(false)
const lastUpdated = ref(null)

const mlComputing  = ref(false)

// ── Month toggle (current vs last month) ─────────────────────────
const dashboardMonthMode = ref('current')   // 'current' | 'last'

function _getLastMonthYear() {
  const now = new Date()
  let y = now.getFullYear()
  let m = now.getMonth()   // 0-indexed: Jan=0
  if (m === 0) { m = 12; y -= 1 } // wrap to Dec of previous year
  return `${y}-${String(m).padStart(2, '0')}`
}

function switchDashboardMonth(mode) {
  if (mode === dashboardMonthMode.value) return
  dashboardMonthMode.value = mode
  fetchDashboard()
}

async function fetchDashboard() {
  const token = localStorage.getItem('access_token')
  if (!token) { handleUnauthorized(); return }
  dashboardLoading.value = true
  try {
    let url = 'http://localhost:8000/api/finance-buddy/dashboard'
    if (dashboardMonthMode.value === 'last') {
      url += `?month_year=${_getLastMonthYear()}`
    }
    const resp = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (resp.status === 401) {
      handleUnauthorized()
      return
    }
    if (resp.ok) {
      dashboardData.value = await resp.json()
      lastUpdated.value = new Date()
    }
  } catch (err) {
    console.error('Dashboard fetch failed:', err)
  } finally {
    dashboardLoading.value = false
  }
}

async function triggerMlCompute() {
  const token = localStorage.getItem('access_token')
  if (!token || mlComputing.value) return
  mlComputing.value = true
  try {
    const resp = await fetch('http://localhost:8000/api/finance-buddy/ml/compute', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    if (resp.ok) {
      const data = await resp.json()
      if (data.task_id) {
        pollMlStatus(data.task_id)
      } else {
        mlComputing.value = false
      }
    } else if (resp.status === 429) {
      // Rate limit hit — tell the user clearly, don't leave spinner running
      mlComputing.value = false
      showToast(
        'You\'ve triggered too many analyses. Please wait an hour before refreshing insights again.',
        'warning'
      )
    } else {
      mlComputing.value = false
    }
  } catch (err) {
    console.error('ML compute trigger failed:', err)
    mlComputing.value = false
  }
}

async function pollMlStatus(taskId) {
  const token = localStorage.getItem('access_token')
  if (!token) {
    mlComputing.value = false
    return
  }
  try {
    const resp = await fetch(`http://localhost:8000/api/finance-buddy/ml/compute/status/${taskId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (resp.ok) {
      const data = await resp.json()
      if (data.state === 'SUCCESS') {
        await fetchDashboard()
        if (activePage.value === 'Actionable Insights') {
          await fetchInsights()
        } else {
          insightsFetched = false
        }
        mlComputing.value = false
      } else if (data.state === 'FAILURE' || data.state === 'REVOKED') {
        console.error('ML computation failed on worker:', data)
        mlComputing.value = false
      } else {
        setTimeout(() => pollMlStatus(taskId), 2000)
      }
    } else {
      setTimeout(() => pollMlStatus(taskId), 2000)
    }
  } catch (err) {
    console.error('ML poll failed:', err)
    setTimeout(() => pollMlStatus(taskId), 2000)
  }
}

// ── Insights / Recommendations API data ─────────────────────────
const insightsData = ref(null)
const insightsLoading = ref(false)
let insightsFetched = false

async function fetchInsights() {
  const token = localStorage.getItem('access_token')
  if (!token) return
  insightsLoading.value = true
  try {
    const resp = await fetch('http://localhost:8000/api/finance-buddy/recommendations', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (resp.ok) {
      insightsData.value = await resp.json()
      insightsFetched = true
    }
  } catch (err) {
    console.error('Insights fetch failed:', err)
  } finally {
    insightsLoading.value = false
  }
}

// Fetch insights when navigating to the Insights tab
watch(activePage, (newPage) => {
  if (newPage === 'Actionable Insights' && !insightsFetched) {
    fetchInsights()
  }
})

const dashboardSummary = computed(() => {
  if (!dashboardData.value?.summary) {
    return { total_income: 0, total_expense: 0, net_savings: 0, income_change_pct: null, expense_change_pct: null, savings_change_pct: null }
  }
  return dashboardData.value.summary
})

const dashboardMonthLabel = computed(() => {
  if (!dashboardData.value?.month) {
    const now = new Date()
    return now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }
  const [y, m] = dashboardData.value.month.split('-')
  const d = new Date(parseInt(y), parseInt(m) - 1)
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
})

const lastUpdatedLabel = computed(() => {
  if (!lastUpdated.value) return 'just now'
  const diff = Math.floor((Date.now() - lastUpdated.value.getTime()) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
})

function fmtCurrency(val) {
  if (val == null) return '$0.00'
  return '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtDelta(pct) {
  if (pct == null) return 'No data'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct}% vs last month`
}

// ── Tabs ────────────────────────────────────────────────────────
const expenseTab = ref('1M')
const savingsTab = ref('1M')

// ── Expense chart (from API) ─────────────────────────────────────
const expenseChartData = computed(() => {
  const chartData = dashboardData.value?.chart_data
  const tabKey = expenseTab.value.toLowerCase()
  if (!chartData || !chartData[tabKey]) {
    return { labels: [], datasets: [] }
  }
  const d = chartData[tabKey]
  return {
    labels: d.labels,
    datasets: [{ label: 'Expenses', data: d.expense, color: '#c0392b' }]
  }
})

// ── Savings trend chart (from API) ───────────────────────────────
const savingsChartData = computed(() => {
  const chartData = dashboardData.value?.chart_data
  const tabKey = savingsTab.value.toLowerCase()
  if (!chartData || !chartData[tabKey]) {
    return { labels: [], datasets: [] }
  }
  const d = chartData[tabKey]
  return {
    labels: d.labels,
    datasets: [
      { label: 'Net Savings', data: d.savings, color: '#3980f4' },
    ]
  }
})

// ── Spending donut (from API) ────────────────────────────────────
const CATEGORY_COLORS = {
  'food/grocery':      '#e67e22',
  'entertainment':     '#e74c3c',
  'emis':              '#c0392b',
  'health':            '#d97706',
  'education':         '#8b5cf6',
  'travel':            '#0ea5e9',
  'personal expenses': '#ec4899',
  'investment/sips':   '#006c49',
  'salary':            '#10b981',
  'rentals':           '#3980f4',
  'utilities/bills':   '#0891b2',
  'incentives/bonus':  '#f59e0b',
  'other':             '#9ca3af',
}
const FALLBACK_COLORS = ['#6366f1', '#14b8a6', '#f43f5e', '#a855f7', '#64748b']

const spendingSegments = computed(() => {
  const breakdown = dashboardData.value?.spending_breakdown
  if (!breakdown || !breakdown.length) return []
  return breakdown.map((item, i) => ({
    label: item.category,
    value: item.amount,
    color: CATEGORY_COLORS[item.category] || FALLBACK_COLORS[i % FALLBACK_COLORS.length],
  }))
})
const spendingTotal = computed(() => spendingSegments.value.reduce((a, b) => a + b.value, 0))
const spendingCenterLabel = computed(() => {
  const total = spendingTotal.value
  if (total >= 1000) return `$${(total / 1000).toFixed(1)}k`
  return `$${total.toFixed(0)}`
})


</script>

<style scoped>
.app-root { min-height: 100vh; display: flex; flex-direction: column; }

.dashboard { flex: 1; padding: var(--space-xl) 0 var(--space-2xl); }
.dash-inner {
  max-width: 1320px; margin: 0 auto;
  padding: 0 var(--space-xl);
  display: flex; flex-direction: column; gap: var(--space-xl);
}

.page-heading { display: flex; justify-content: space-between; align-items: flex-end; }
.heading-actions { display: flex; gap: var(--space-sm); align-items: center; }

/* Month toggle switch */
.month-toggle {
  display: inline-flex;
  background: var(--col-surface-alt, rgba(255,255,255,0.04));
  border: 1px solid var(--col-border, rgba(255,255,255,0.08));
  border-radius: var(--r-lg, 12px);
  padding: 3px;
  gap: 2px;
}
.month-toggle-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 16px;
  border: none;
  border-radius: var(--r-md, 8px);
  background: transparent;
  color: var(--col-text-secondary, #9ca3af);
  font-size: 0.82rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
}
.month-toggle-btn:hover:not(.active) {
  color: var(--col-text-primary, #e5e7eb);
  background: rgba(255,255,255,0.04);
}
.month-toggle-btn.active {
  background: var(--col-primary, #3980f4);
  color: #fff;
  box-shadow: 0 1px 6px rgba(57, 128, 244, 0.35);
}
.icon-xs {
  font-size: 16px !important;
}
@media (max-width: 640px) {
  .month-toggle-btn { padding: 6px 10px; font-size: 0.75rem; }
  .month-toggle-btn .icon-xs { display: none; }
}

.alert-banner {
  display: flex; align-items: center; gap: var(--space-sm);
  padding: 10px var(--space-md);
  background: var(--col-error-bg);
  border: 1px solid var(--col-error-border);
  border-radius: var(--r-lg);
}
.info-banner {
  display: flex; align-items: center; gap: var(--space-sm);
  padding: 10px var(--space-md);
  background: var(--col-blue-light);
  border: 1px solid rgba(57, 128, 244, 0.2);
  border-radius: var(--r-lg);
}

.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-lg); }
@media (max-width: 860px) { .metrics-grid { grid-template-columns: 1fr; } }

.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg); }
@media (max-width: 900px) { .charts-grid { grid-template-columns: 1fr; } }

.card-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: var(--space-md);
}

.breakdown-row { display: grid; grid-template-columns: 1fr; gap: var(--space-lg); }

.breakdown-inner { display: flex; align-items: center; gap: var(--space-xl); }
.segment-legend { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.legend-row { display: grid; grid-template-columns: 10px 1fr auto auto; align-items: center; gap: 8px; }
.legend-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.legend-label { overflow: hidden; white-space: nowrap; }
.legend-value { font-weight: 600; color: var(--col-text-primary); text-align: right; }
.legend-pct   { width: 28px; text-align: right; }

/* ── Toast notification ────────────────────────────────────────── */
.toast-popup {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border-radius: 12px;
  border: 1px solid transparent;
  max-width: 480px;
  width: calc(100% - 48px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.35);
  font-size: 0.9rem;
  font-weight: 500;
  backdrop-filter: blur(8px);
}
.toast-warning {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.35);
  color: #fcd34d;
}
.toast-error {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.35);
  color: #fca5a5;
}
.toast-info {
  background: rgba(57, 128, 244, 0.15);
  border-color: rgba(57, 128, 244, 0.35);
  color: #93c5fd;
}
.toast-icon { font-size: 1.1rem; flex-shrink: 0; }
.toast-message { flex: 1; line-height: 1.45; }
.toast-close {
  background: transparent;
  border: none;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 2px 4px;
  border-radius: 4px;
  transition: opacity 0.2s;
  flex-shrink: 0;
}
.toast-close:hover { opacity: 1; }

/* slide-up enter/leave animation */
.toast-enter-active, .toast-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.toast-enter-from { opacity: 0; transform: translateX(-50%) translateY(16px); }
.toast-leave-to   { opacity: 0; transform: translateX(-50%) translateY(16px); }
</style>
