<template>
  <div class="goals-root">

    <!-- ── Page Header ────────────────────────────────────────── -->
    <div class="page-heading fade-up">
      <div>
        <h1 class="t-display" style="color:var(--col-primary)">Financial Goals</h1>
        <p class="t-body text-muted" style="margin-top:4px">
          <template v-if="loading">Loading…</template>
          <template v-else-if="apiError" style="color:var(--col-error)">{{ apiError }}</template>
          <template v-else>Tracking your journey to financial freedom.</template>
        </p>
      </div>
      <button class="btn btn-primary" @click="showAddModal = true">
        <span class="material-symbols-outlined icon-sm">add</span>
        Add New Goal
      </button>
    </div>

    <!-- ── Summary cards ─────────────────────────────────────── -->
    <div class="summary-grid fade-up" style="animation-delay:60ms">
      <div class="card summary-card">
        <div class="summary-icon" style="background:rgba(19,27,46,0.06)">
          <span class="material-symbols-outlined icon-filled icon-md" style="color:var(--col-primary)">flag</span>
        </div>
        <div>
          <div class="t-label text-muted" style="text-transform:uppercase;letter-spacing:.06em">Total Goals</div>
          <div class="t-metric" style="font-size:1.625rem">{{ goals.length }} Active</div>
        </div>
      </div>

      <div class="card summary-card" style="border-left:4px solid var(--col-error)">
        <div class="summary-icon" style="background:var(--col-error-bg)">
          <span class="material-symbols-outlined icon-md" style="color:var(--col-error)">trending_down</span>
        </div>
        <div>
          <div class="t-label text-muted" style="text-transform:uppercase;letter-spacing:.06em">Achievable</div>
          <div class="t-metric text-error" style="font-size:1.625rem">0 on track</div>
        </div>
      </div>

      <div class="card summary-card">
        <div class="summary-icon" style="background:var(--col-accent-light)">
          <span class="material-symbols-outlined icon-filled icon-md" style="color:var(--col-accent)">savings</span>
        </div>
        <div>
          <div class="t-label text-muted" style="text-transform:uppercase;letter-spacing:.06em">Savings Gap</div>
          <div class="t-metric" :style="{ fontSize: '1.625rem', color: savingsGap >= 0 ? 'var(--col-accent)' : 'var(--col-error)' }">
            {{ savingsGap >= 0 ? '+' : '–' }}₹{{ fmtAmt(Math.abs(savingsGap)) }}
          </div>
        </div>
      </div>
    </div>

    <!-- ── Goals list ─────────────────────────────────────────── -->
    <section class="fade-up" style="animation-delay:120ms">
      <div class="list-header">
        <h2 class="t-headline">Your Savings Goals</h2>
        <div class="tab-strip">
          <button :class="['tab-btn', { active: statusFilter === 'Active' }]"
                  @click="statusFilter = 'Active'">Active</button>
          <button :class="['tab-btn', { active: statusFilter === 'Archived' }]"
                  @click="statusFilter = 'Archived'">Archived</button>
        </div>
      </div>

      <div class="goals-list">
        <div v-for="goal in filteredGoals" :key="goal.id" class="goal-item card">

          <!-- Left: icon -->
          <div class="goal-icon-wrap" :style="{ background: goalIconBg(goal) }">
            <span class="material-symbols-outlined icon-filled icon-md"
                  :style="{ color: goalIconColor(goal) }">
              {{ goalIcon(goal) }}
            </span>
          </div>

          <!-- Centre: info -->
          <div class="goal-info">
            <div class="goal-name-row">
              <h3 class="t-title" style="color:var(--col-primary)">{{ capitaliseName(goal.name) }}</h3>
              <span class="badge badge-success">{{ capitalise(goal.status) }}</span>
              <span class="badge badge-error">
                <span class="material-symbols-outlined" style="font-size:10px">warning</span>
                Off Track
              </span>
            </div>

            <div class="goal-meta">
              <div class="goal-meta-item">
                <span class="material-symbols-outlined icon-sm text-muted">calendar_today</span>
                <span class="t-body text-muted">{{ fmtDeadline(goal.deadline) }}</span>
              </div>
              <div class="goal-meta-item">
                <span class="material-symbols-outlined icon-sm text-muted">payments</span>
                <span class="t-body text-muted">Target: ₹{{ fmtAmt(goal.target_amount) }}</span>
              </div>
              <div class="goal-meta-item">
                <span class="material-symbols-outlined icon-sm text-muted">schedule</span>
                <span class="t-body text-muted">{{ monthsLeft(goal.deadline) }} months left</span>
              </div>
            </div>

            <!-- Progress bar -->
            <div class="goal-progress">
              <div class="progress-track" style="height:6px">
                <div class="progress-fill"
                     style="width:0%;background:var(--col-error)"></div>
              </div>
              <div style="display:flex;justify-content:space-between;margin-top:4px">
                <span class="t-label text-error" style="font-weight:700">0% — Off Track</span>
                <span class="t-label text-muted t-mono">₹0 / ₹{{ fmtAmt(goal.target_amount) }}</span>
              </div>
            </div>
          </div>

          <!-- Right: actions -->
          <div class="goal-actions">
            <button class="btn btn-icon" title="Edit goal" @click="openEdit(goal)">
              <span class="material-symbols-outlined icon-sm text-muted">edit</span>
            </button>
            <button class="btn btn-icon" title="Delete goal" @click="confirmDelete(goal)">
              <span class="material-symbols-outlined icon-sm" style="color:var(--col-error)">delete</span>
            </button>
          </div>

        </div>

        <!-- Empty state -->
        <div v-if="filteredGoals.length === 0" class="empty-goals">
          <span class="material-symbols-outlined icon-lg text-faint">flag</span>
          <div class="t-title text-muted">No goals yet</div>
          <div class="t-label text-faint">Add a new goal to start tracking your savings</div>
          <button class="btn btn-primary" style="margin-top:var(--space-md)" @click="showAddModal = true">
            <span class="material-symbols-outlined icon-sm">add</span>
            Add First Goal
          </button>
        </div>
      </div>
    </section>

    <!-- ── Insight + Forecast row ─────────────────────────────── -->
    <div class="insight-row fade-up" style="animation-delay:200ms">

      <!-- Smart Insight card (2/3) -->
      <div class="card insight-card">
        <span class="badge badge-neutral" style="background:var(--col-primary);color:#fff;margin-bottom:var(--space-md)">
          Smart Insight
        </span>
        <h2 class="t-headline" style="margin-bottom:var(--space-sm)">Closing the Savings Gap</h2>
        <p class="t-body text-muted" style="line-height:1.6;margin-bottom:var(--space-lg)">
          Based on your current spending pattern and 3 active goals, you have a monthly shortfall of
          <strong style="color:var(--col-error)">₹12,406</strong>.
          Implementing the recommended savings opportunities
          (<strong style="color:var(--col-accent)">+₹14,307/month</strong>)
          could make all goals achievable within their deadlines.
        </p>
        <button class="t-body" style="font-weight:700;color:var(--col-primary);display:flex;align-items:center;gap:6px;
          background:none;border:none;cursor:pointer;text-decoration:underline;text-underline-offset:3px;
          text-decoration-color:rgba(19,27,46,0.2)">
          View Detailed Recommendations
          <span class="material-symbols-outlined icon-sm">arrow_forward</span>
        </button>
      </div>

      <!-- Quick Forecast card (1/3) -->
      <div class="forecast-dark-card">
        <div>
          <h3 class="t-title" style="color:#fff;margin-bottom:8px">Quick Forecast</h3>
          <p style="color:rgba(255,255,255,0.7);font-size:0.875rem;line-height:1.55">
            By maintaining current savings, Emergency Fund will be reached by
            <strong style="color:var(--col-accent-dim)">Jan 2028</strong>
            instead of Aug 2027.
          </p>
        </div>
        <div class="forecast-goals-mini">
          <div v-for="g in goals" :key="g.id" class="mini-goal-row">
            <span class="t-label" style="color:rgba(255,255,255,0.7);text-transform:capitalize;flex:1">
              {{ capitaliseName(g.name) }}
            </span>
            <span class="badge badge-error" style="font-size:0.55rem">Off Track</span>
          </div>
        </div>
        <button class="btn" style="background:rgba(255,255,255,0.12);color:#fff;padding:8px 16px;font-size:0.8125rem;
          border:1px solid rgba(255,255,255,0.15);margin-top:var(--space-md)">
          <span class="material-symbols-outlined icon-sm">insights</span>
          Full Insights
        </button>
      </div>

    </div>

    <!-- ── Add / Edit Goal Modal ──────────────────────────────── -->
    <Transition name="modal">
      <div v-if="showAddModal || editGoal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-box">
          <div class="modal-header">
            <h3 class="t-title">{{ editGoal ? 'Edit Goal' : 'Add New Goal' }}</h3>
            <button class="btn btn-icon" @click="closeModal">
              <span class="material-symbols-outlined icon-sm">close</span>
            </button>
          </div>
          <div class="modal-body">
            <div class="form-field">
              <label class="t-label text-muted">Goal Name</label>
              <input v-model="form.name" type="text" class="form-input" placeholder="e.g. MacBook Pro" />
            </div>
            <div class="form-field">
              <label class="t-label text-muted">Target Amount (₹)</label>
              <input v-model="form.target_amount" type="number" class="form-input" placeholder="e.g. 150000" min="1" />
            </div>
            <div class="form-field">
              <label class="t-label text-muted">Deadline</label>
              <input v-model="form.deadline" type="date" class="form-input" />
            </div>
            <div v-if="editGoal" class="form-field">
              <label class="t-label text-muted">Status</label>
              <select v-model="form.status" class="form-input">
                <option value="current">Current</option>
                <option value="achieved">Achieved</option>
                <option value="archive">Archive</option>
              </select>
            </div>
            <!-- Preview -->
            <div v-if="form.name && form.target_amount && form.deadline" class="form-preview">
              <div class="t-label text-muted" style="margin-bottom:6px">Preview</div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span class="t-body" style="font-weight:600;text-transform:capitalize">{{ form.name }}</span>
                <span class="t-mono" style="font-weight:700">₹{{ Number(form.target_amount).toLocaleString('en-IN') }}</span>
              </div>
              <div class="t-label text-muted">Due: {{ fmtDeadline(form.deadline) }} · {{ monthsLeft(form.deadline) }} months</div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="closeModal">Cancel</button>
            <button class="btn btn-primary" :disabled="!formValid" @click="saveGoal">
              <span class="material-symbols-outlined icon-sm">{{ editGoal ? 'save' : 'add' }}</span>
              {{ editGoal ? 'Save Changes' : 'Add Goal' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Delete confirmation ────────────────────────────────── -->
    <Transition name="modal">
      <div v-if="deleteGoal" class="modal-overlay" @click.self="deleteGoal = null">
        <div class="modal-box" style="max-width:400px">
          <div class="modal-header">
            <h3 class="t-title">Delete Goal</h3>
            <button class="btn btn-icon" @click="deleteGoal = null">
              <span class="material-symbols-outlined icon-sm">close</span>
            </button>
          </div>
          <div class="modal-body">
            <div style="display:flex;gap:var(--space-md);align-items:flex-start">
              <div style="background:var(--col-error-bg);border-radius:var(--r-md);padding:10px;flex-shrink:0">
                <span class="material-symbols-outlined icon-md icon-filled" style="color:var(--col-error)">delete</span>
              </div>
              <div>
                <div class="t-body" style="font-weight:600;margin-bottom:4px">
                  Delete "{{ capitaliseName(deleteGoal.name) }}"?
                </div>
                <div class="t-body text-muted">
                  This will permanently remove this goal. This action cannot be undone.
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="deleteGoal = null">Cancel</button>
            <button class="btn" style="background:var(--col-error);color:#fff" @click="removeGoal">
              Delete Goal
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Toast ──────────────────────────────────────────────── -->
    <Transition name="toast">
      <div v-if="toast" class="toast">
        <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-accent)">check_circle</span>
        {{ toast }}
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// ── API base URL ──────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000/api/finance-buddy'

// ── Auth helper ───────────────────────────────────────────────────
function getAuthHeaders() {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ── State ─────────────────────────────────────────────────────────
const goals        = ref([])
const totalSavings = ref(0)
const totalTarget  = ref(0)
const loading      = ref(false)
const apiError     = ref('')
const statusFilter = ref('Active')
const showAddModal = ref(false)
const editGoal     = ref(null)
const deleteGoal   = ref(null)
const toast        = ref('')

const emptyForm = () => ({ name: '', target_amount: '', deadline: '', status: 'current' })
const form = ref(emptyForm())

// ── Fetch Goals ───────────────────────────────────────────────────
async function fetchGoals() {
  loading.value  = true
  apiError.value = ''
  try {
    const res = await fetch(`${API_BASE}/goal/list`, {
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.error || `Server error ${res.status}`)
    }
    const data = await res.json()
    goals.value    = data.goals || []
    totalSavings.value = data.total_savings ?? 0
    totalTarget.value  = data.total_target ?? 0
  } catch (err) {
    apiError.value = err.message || 'Failed to load goals'
  } finally {
    loading.value = false
  }
}

onMounted(() => fetchGoals())

// ── Computed ──────────────────────────────────────────────────────
const filteredGoals = computed(() =>
  // All API goals have status "current" → shown under Active tab
  statusFilter.value === 'Active'
    ? goals.value.filter(g => g.status === 'current')
    : goals.value.filter(g => g.status !== 'current')
)

const savingsGap = computed(() => totalSavings.value - totalTarget.value)

const formValid = computed(() =>
  form.value.name.trim() &&
  parseFloat(form.value.target_amount) > 0 &&
  form.value.deadline
)

// ── Helpers ───────────────────────────────────────────────────────
function capitaliseName(name) {
  if (!name) return ''
  return name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}
function capitalise(s) {
  if (!s) return ''
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function fmtDeadline(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })
}

function fmtAmt(v) {
  const n = parseFloat(v)
  if (isNaN(n)) return '0'
  if (n >= 100000) return (n/1000).toFixed(0) + 'k'
  if (n >= 10000)  return (n/1000).toFixed(1) + 'k'
  return n.toLocaleString('en-IN')
}

function monthsLeft(deadline) {
  if (!deadline) return 0
  const now  = new Date()
  const end  = new Date(deadline)
  const diff = (end.getFullYear() - now.getFullYear()) * 12 + (end.getMonth() - now.getMonth())
  return Math.max(0, diff)
}

// ── Goal icon / colour per name ───────────────────────────────────
const GOAL_ICONS = {
  macbook:            { bg: '#e3f2fd', col: '#1565c0', icon: 'laptop_mac'  },
  emergency:          { bg: '#fff8e1', col: '#f57f17', icon: 'health_and_safety' },
  dyson:              { bg: '#f3e5f5', col: '#7b1fa2', icon: 'dry'         },
  default:            { bg: 'var(--col-accent-light)', col: 'var(--col-accent)', icon: 'savings' },
}
function goalPalette(goal) {
  const n = goal.name ? goal.name.toLowerCase() : ''
  if (n.includes('macbook') || n.includes('laptop')) return GOAL_ICONS.macbook
  if (n.includes('emergency')) return GOAL_ICONS.emergency
  if (n.includes('dyson') || n.includes('hair'))     return GOAL_ICONS.dyson
  return GOAL_ICONS.default
}
function goalIconBg(g)    { return goalPalette(g).bg }
function goalIconColor(g) { return goalPalette(g).col }
function goalIcon(g)      { return goalPalette(g).icon }

// ── Modal actions ─────────────────────────────────────────────────
function openEdit(goal) {
  editGoal.value = goal
  form.value = { name: goal.name, target_amount: parseFloat(goal.target_amount).toString(), deadline: goal.deadline, status: goal.status || 'current' }
}
function closeModal() {
  showAddModal.value = false
  editGoal.value = null
  form.value = emptyForm()
}
async function saveGoal() {
  if (!formValid.value) return
  const payload = {
    name: form.value.name,
    target_amount: parseFloat(form.value.target_amount).toFixed(2),
    deadline: form.value.deadline,
    status: editGoal.value ? form.value.status : 'current',
  }
  
  if (editGoal.value) {
    payload.id = editGoal.value.id
  }

  try {
    const res = await fetch(`${API_BASE}/goal`, {
      method: editGoal.value ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.error || JSON.stringify(body) || `Server error ${res.status}`)
    }
    showToast(editGoal.value ? 'Goal updated successfully!' : 'Goal added successfully!')
    closeModal()
    await fetchGoals()
  } catch (err) {
    alert(err.message || 'Failed to save goal.')
  }
}
function confirmDelete(goal) { deleteGoal.value = goal }
async function removeGoal() {
  if (!deleteGoal.value) return
  try {
    const res = await fetch(`${API_BASE}/goal`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ id: deleteGoal.value.id }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.error || `Server error ${res.status}`)
    }
    showToast('Goal deleted.')
    deleteGoal.value = null
    await fetchGoals()
  } catch (err) {
    alert(err.message || 'Failed to delete goal.')
  }
}
function showToast(msg) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 3000)
}
</script>

<style scoped>
.goals-root { display: flex; flex-direction: column; gap: var(--space-xl); }

/* Page heading */
.page-heading { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: var(--space-md); }

/* Summary */
.summary-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-lg);
}
@media (max-width: 700px) { .summary-grid { grid-template-columns: 1fr; } }
.summary-card { display: flex; align-items: center; gap: var(--space-md); }
.summary-icon {
  width: 48px; height: 48px; border-radius: var(--r-md); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}

/* List header */
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md); }

/* Goals list */
.goals-list { display: flex; flex-direction: column; gap: var(--space-md); }

.goal-item {
  display: flex; align-items: flex-start; gap: var(--space-md);
  padding: var(--space-lg);
  transition: box-shadow var(--dur-base), transform var(--dur-base);
}
.goal-item:hover { box-shadow: var(--shadow-elevated); transform: translateY(-1px); }

.goal-icon-wrap {
  width: 48px; height: 48px; border-radius: var(--r-md); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.goal-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }

.goal-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.goal-meta { display: flex; align-items: center; gap: var(--space-lg); flex-wrap: wrap; }
.goal-meta-item { display: flex; align-items: center; gap: 5px; }

.goal-progress { display: flex; flex-direction: column; }

.goal-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }

/* Empty state */
.empty-goals {
  display: flex; flex-direction: column; align-items: center; padding: var(--space-2xl);
  gap: var(--space-sm);
  background: var(--col-surface-card); border: 1px solid var(--col-border);
  border-radius: var(--r-lg);
}

/* Insight row */
.insight-row {
  display: grid; grid-template-columns: 2fr 1fr; gap: var(--space-lg);
}
@media (max-width: 900px) { .insight-row { grid-template-columns: 1fr; } }

.insight-card { position: relative; overflow: hidden; }

/* Dark forecast card */
.forecast-dark-card {
  background: var(--col-primary);
  border-radius: var(--r-lg);
  padding: var(--space-lg);
  display: flex; flex-direction: column; gap: var(--space-md);
}
.forecast-goals-mini { display: flex; flex-direction: column; gap: 8px; margin-top: var(--space-sm); }
.mini-goal-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: rgba(255,255,255,0.08);
  border-radius: var(--r-md);
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(19,27,46,0.35); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; padding: var(--space-lg);
}
.modal-box {
  background: var(--col-surface-card);
  border-radius: var(--r-xl);
  width: 100%; max-width: 480px;
  box-shadow: var(--shadow-elevated);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--col-border);
}
.modal-body { padding: var(--space-lg); display: flex; flex-direction: column; gap: var(--space-md); }
.modal-footer {
  display: flex; justify-content: flex-end; gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  border-top: 1px solid var(--col-border);
  background: var(--col-surface-low);
}

/* Form */
.form-field { display: flex; flex-direction: column; gap: 5px; }
.form-input {
  padding: 9px 12px;
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
  font-family: inherit; font-size: 0.875rem;
  color: var(--col-text-primary);
  background: var(--col-surface-low);
  outline: none; transition: border-color var(--dur-fast);
}
.form-input:focus { border-color: var(--col-accent); background: #fff; }
.form-input:disabled { opacity: 0.5; cursor: not-allowed; }
.form-preview {
  padding: var(--space-md);
  background: var(--col-accent-light);
  border: 1px solid rgba(0,108,73,0.2);
  border-radius: var(--r-md);
}

/* Toast */
.toast {
  position: fixed; bottom: 2rem; right: 2rem; z-index: 200;
  display: flex; align-items: center; gap: 8px;
  padding: 12px 20px;
  background: var(--col-primary); color: #fff;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-elevated);
  font-size: 0.875rem; font-weight: 600;
}
.toast-enter-active, .toast-leave-active { transition: all 0.3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }

/* Modal transition */
.modal-enter-active, .modal-leave-active { transition: all 0.25s var(--ease-out); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-box, .modal-leave-to .modal-box { transform: scale(0.96) translateY(8px); }
</style>
