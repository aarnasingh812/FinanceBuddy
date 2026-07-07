<template>
  <div class="txn-root">

    <!-- ── Page Header ──────────────────────────────────────────── -->
    <div class="page-heading fade-up">
      <div>
        <h1 class="t-display" style="font-size:2rem;color:var(--col-primary)">Transactions</h1>
        <p class="t-body text-muted" style="margin-top:4px">
          <template v-if="loading">Loading…</template>
          <template v-else-if="apiError" style="color:var(--col-error)">{{ apiError }}</template>
          <template v-else>
            Showing {{ filteredTransactions.length }} transactions
            <span v-if="filterLabel" class="filter-label-badge">{{ filterLabel }}</span>
          </template>
        </p>
      </div>
      <div class="heading-actions">
        <!-- ── Month / Year API filter ── -->
        <div class="api-filter-wrap">
          <select v-model="filterMode" class="cat-select" @change="onFilterModeChange">
            <option value="current_month">This Month</option>
            <option value="month">Specific Month</option>
            <option value="year">Full Year</option>
          </select>

          <!-- Month picker: YYYY-MM -->
          <template v-if="filterMode === 'month'">
            <input type="month" v-model="selectedMonth" class="date-input" style="width:140px"
                   @change="fetchTransactions" />
          </template>

          <!-- Year picker -->
          <template v-if="filterMode === 'year'">
            <select v-model="selectedYear" class="cat-select" @change="fetchTransactions">
              <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
            </select>
          </template>

          <button class="btn btn-ghost btn-icon" title="Refresh" @click="fetchTransactions" :disabled="loading">
            <span class="material-symbols-outlined icon-sm" :class="{ spinning: loading }">refresh</span>
          </button>
        </div>

        <!-- Bulk Upload split-button dropdown -->
        <div class="bulk-dropdown-wrap" v-click-outside="() => showBulkDropdown = false">
          <button class="btn btn-ghost bulk-main-btn" @click="showBulkDropdown = !showBulkDropdown">
            <span class="material-symbols-outlined icon-sm">upload</span>
            Bulk Upload
            <span class="material-symbols-outlined icon-sm" style="color:var(--col-text-faint);font-size:16px">
              {{ showBulkDropdown ? 'expand_less' : 'expand_more' }}
            </span>
          </button>

          <Transition name="dropdown">
            <div v-if="showBulkDropdown" class="bulk-dropdown-menu">
              <button class="bulk-dropdown-item" @click="onDownloadTemplate">
                <span class="material-symbols-outlined icon-sm">download</span>
                <div>
                  <div class="bulk-item-title">Download Template</div>
                  <div class="bulk-item-sub">Get the Excel file to fill in</div>
                </div>
              </button>
              <div class="bulk-dropdown-divider"></div>
              <button class="bulk-dropdown-item" @click="onUploadClick">
                <span class="material-symbols-outlined icon-sm">cloud_upload</span>
                <div>
                  <div class="bulk-item-title">Upload Transactions</div>
                  <div class="bulk-item-sub">Import from filled .xlsx file</div>
                </div>
              </button>
            </div>
          </Transition>
        </div>
        <button class="btn btn-primary" @click="openAddModal">
          <span class="material-symbols-outlined icon-sm">add</span>
          Add Transaction
        </button>
      </div>
    </div>

    <!-- ── Summary strip ─────────────────────────────────────────── -->
    <div class="summary-strip fade-up" style="animation-delay:60ms">
      <div class="summary-chip">
        <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-accent)">arrow_circle_down</span>
        <div>
          <div class="t-label text-muted">Total Income</div>
          <div class="t-mono" style="font-weight:700;color:var(--col-accent)">+₹{{ fmt(totalIncome) }}</div>
        </div>
      </div>
      <div class="summary-divider"></div>
      <div class="summary-chip">
        <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-error)">arrow_circle_up</span>
        <div>
          <div class="t-label text-muted">Total Expenses</div>
          <div class="t-mono" style="font-weight:700;color:var(--col-error)">–₹{{ fmt(totalExpenses) }}</div>
        </div>
      </div>
      <div class="summary-divider"></div>
      <div class="summary-chip">
        <span class="material-symbols-outlined icon-sm icon-filled"
              :style="{ color: netAmount >= 0 ? 'var(--col-accent)' : 'var(--col-error)' }">
          account_balance_wallet
        </span>
        <div>
          <div class="t-label text-muted">Net Flow</div>
          <div class="t-mono" style="font-weight:700"
               :style="{ color: netAmount >= 0 ? 'var(--col-accent)' : 'var(--col-error)' }">
            {{ netAmount >= 0 ? '+' : '–' }}₹{{ fmt(Math.abs(netAmount)) }}
          </div>
        </div>
      </div>
      <!-- Spacer to push tabs and filters to the right -->
      <div style="flex: 1"></div>
      <!-- Type tabs -->
      <div class="tab-strip">
        <button v-for="t in ['All','Income','Expense']" :key="t"
                :class="['tab-btn', { active: typeFilter === t }]"
                @click="typeFilter = t">{{ t }}</button>
      </div>
      <!-- Category -->
      <select v-model="categoryFilter" class="cat-select">
        <option value="">All Categories</option>
        <option v-for="c in allCategories" :key="c" :value="c">{{ capitalise(c) }}</option>
      </select>
    </div>

    <!-- ── Table ─────────────────────────────────────────────────── -->
    <div class="card txn-card fade-up" style="animation-delay:120ms;padding:0;overflow:hidden">

      <!-- Empty state -->
      <div v-if="filteredTransactions.length === 0" class="empty-state">
        <span class="material-symbols-outlined icon-lg text-faint">receipt_long</span>
        <div class="t-title text-muted">No transactions found</div>
        <div class="t-label text-faint">Try adjusting your filters or date range</div>
      </div>

      <div v-else class="table-wrap">
        <table class="txn-table">
          <thead>
            <tr>
              <th @click="setSort('title')" class="th-sortable">
                Title <span class="sort-icon">{{ sortIcon('title') }}</span>
              </th>
              <th>Category</th>
              <th>Type</th>
              <th @click="setSort('date')" class="th-sortable">
                Date <span class="sort-icon">{{ sortIcon('date') }}</span>
              </th>
              <th @click="setSort('amount')" class="th-sortable text-right">
                Amount <span class="sort-icon">{{ sortIcon('amount') }}</span>
              </th>
            </tr>
          </thead>

          <tbody>
            <template v-for="(group, date) in groupedTransactions" :key="date">
              <!-- Date group header row -->
              <tr class="group-row">
                <td colspan="5">
                  <div class="group-header">
                    <span class="t-label" style="font-weight:700">{{ fmtDate(date) }}</span>
                    <span class="t-label text-faint">{{ group.length }} txn{{ group.length > 1 ? 's' : '' }}</span>
                    <div class="group-divider"></div>
                    <span class="t-mono" style="font-size:0.7rem;font-weight:700"
                          :style="{ color: dateNet(group) >= 0 ? 'var(--col-accent)' : 'var(--col-error)' }">
                      {{ dateNet(group) >= 0 ? '+' : '–' }}₹{{ fmt(Math.abs(dateNet(group))) }}
                    </span>
                  </div>
                </td>
              </tr>
              <!-- Transaction rows -->
              <tr v-for="txn in group" :key="txn.title+txn.date+txn.amount"
                  class="txn-row" @click="selectedTxn = txn">
                <!-- Title -->
                <td class="td-title">
                  <div class="txn-title-cell">
                    <div class="txn-icon" :style="{ background: txn.transaction_type === 'Income' ? 'var(--col-accent-light)' : catBg(txn.category) }">
                      <span class="material-symbols-outlined icon-filled"
                            style="font-size:16px"
                            :style="{ color: txn.transaction_type === 'Income' ? 'var(--col-accent)' : catColor(txn.category) }">
                        {{ catIcon(txn.category, txn.transaction_type) }}
                      </span>
                    </div>
                    <span class="t-body" style="font-weight:600;color:var(--col-primary)">{{ txn.title }}</span>
                  </div>
                </td>
                <!-- Category -->
                <td class="td-cat">
                  <span class="badge badge-neutral" style="text-transform:capitalize">{{ txn.category }}</span>
                </td>
                <!-- Type -->
                <td>
                  <span :class="['type-pill', txn.transaction_type === 'Income' ? 'type-income' : 'type-expense']">
                    {{ txn.transaction_type }}
                  </span>
                </td>
                <!-- Date -->
                <td class="td-date t-body text-muted">{{ fmtDateShort(txn.date) }}</td>
                <!-- Amount -->
                <td class="td-amount">
                  <span class="t-mono"
                        style="font-size:1rem;font-weight:700"
                        :style="{ color: txn.transaction_type === 'Income' ? 'var(--col-accent)' : 'var(--col-error)' }">
                    {{ txn.transaction_type === 'Income' ? '+' : '–' }}₹{{ fmt(parseFloat(txn.amount)) }}
                  </span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Table footer -->
      <div v-if="filteredTransactions.length > 0" class="table-footer">
        <span class="t-label text-muted">
          {{ filteredTransactions.length }} of {{ transactions.length }} transactions
        </span>
        <span class="t-label text-muted">
          Net: <span class="t-mono" style="font-weight:700"
               :style="{ color: netAmount >= 0 ? 'var(--col-accent)' : 'var(--col-error)' }">
            {{ netAmount >= 0 ? '+' : '–' }}₹{{ fmt(Math.abs(netAmount)) }}
          </span>
        </span>
      </div>
    </div>

    <!-- ── Transaction detail drawer (click a row) ────────────────── -->
    <Transition name="drawer">
      <div v-if="selectedTxn" class="drawer-overlay" @click.self="selectedTxn = null">
        <div class="drawer">
          <div class="drawer-header">
            <div class="txn-icon-lg" :style="{ background: selectedTxn.transaction_type === 'Income' ? 'var(--col-accent-light)' : catBg(selectedTxn.category) }">
              <span class="material-symbols-outlined icon-filled icon-lg"
                    :style="{ color: selectedTxn.transaction_type === 'Income' ? 'var(--col-accent)' : catColor(selectedTxn.category) }">
                {{ catIcon(selectedTxn.category, selectedTxn.transaction_type) }}
              </span>
            </div>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-icon" @click="editTransaction(selectedTxn)" title="Edit">
                <span class="material-symbols-outlined icon-sm">edit</span>
              </button>
              <button class="btn btn-icon text-error" @click="deleteTransaction(selectedTxn.id)" title="Delete" :disabled="isDeleting === selectedTxn.id">
                <span v-if="isDeleting === selectedTxn.id" class="material-symbols-outlined icon-sm spinning">refresh</span>
                <span v-else class="material-symbols-outlined icon-sm">delete</span>
              </button>
              <button class="btn btn-icon" @click="selectedTxn = null" title="Close">
                <span class="material-symbols-outlined icon-sm">close</span>
              </button>
            </div>
          </div>
          <div class="drawer-body">
            <div class="t-headline" style="font-size:1.25rem;margin-bottom:4px">{{ selectedTxn.title }}</div>
            <div class="t-metric" style="font-size:1.75rem;margin-bottom:var(--space-lg)"
                 :style="{ color: selectedTxn.transaction_type === 'Income' ? 'var(--col-accent)' : 'var(--col-error)' }">
              {{ selectedTxn.transaction_type === 'Income' ? '+' : '–' }}₹{{ fmt(parseFloat(selectedTxn.amount)) }}
            </div>
            <div class="drawer-rows">
              <div class="drawer-row">
                <span class="t-label text-muted">Type</span>
                <span :class="['type-pill', selectedTxn.transaction_type === 'Income' ? 'type-income' : 'type-expense']">
                  {{ selectedTxn.transaction_type }}
                </span>
              </div>
              <div class="drawer-row">
                <span class="t-label text-muted">Category</span>
                <span class="badge badge-neutral" style="text-transform:capitalize">{{ selectedTxn.category }}</span>
              </div>
              <div class="drawer-row">
                <span class="t-label text-muted">Date</span>
                <span class="t-body" style="font-weight:600">{{ fmtDate(selectedTxn.date) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Add Transaction Modal ─────────────────────────────────────── -->
    <Transition name="modal">
      <div v-if="showAddModal" class="modal-backdrop" @click.self="closeAddModal">
        <div class="modal-panel" role="dialog" aria-modal="true" aria-label="Add Transaction">

          <!-- Header -->
          <div class="modal-header">
            <div class="modal-title-wrap">
              <div class="modal-icon-wrap">
                <span class="material-symbols-outlined icon-filled" style="font-size:20px;color:var(--col-accent)">add_circle</span>
              </div>
              <div>
                <div class="t-headline" style="font-size:1.1rem">{{ editingTxnId ? 'Edit Transaction' : 'Add Transaction' }}</div>
                <div class="t-label text-muted">{{ editingTxnId ? 'Update transaction details' : 'Record a new income or expense' }}</div>
              </div>
            </div>
            <button class="btn btn-icon" @click="closeAddModal">
              <span class="material-symbols-outlined icon-sm">close</span>
            </button>
          </div>

          <!-- Body -->
          <form class="modal-body" @submit.prevent="submitTransaction" novalidate>

            <!-- Type toggle -->
            <div class="form-group">
              <label class="form-label">Type <span class="req">*</span></label>
              <div class="type-toggle">
                <button type="button"
                        :class="['type-toggle-btn', form.transaction_type === 'Income' ? 'active-income' : '']"
                        @click="form.transaction_type = 'Income'">
                  <span class="material-symbols-outlined icon-sm icon-filled">arrow_circle_down</span>
                  Income
                </button>
                <button type="button"
                        :class="['type-toggle-btn', form.transaction_type === 'Expense' ? 'active-expense' : '']"
                        @click="form.transaction_type = 'Expense'">
                  <span class="material-symbols-outlined icon-sm icon-filled">arrow_circle_up</span>
                  Expense
                </button>
              </div>
              <span v-if="formErrors.transaction_type" class="field-error">{{ formErrors.transaction_type }}</span>
            </div>

            <!-- Title -->
            <div class="form-group">
              <label class="form-label" for="txn-title">Title <span class="req">*</span></label>
              <input id="txn-title" v-model.trim="form.title" type="text"
                     class="form-input" :class="{ 'input-error': formErrors.title }"
                     placeholder="e.g. Monthly Salary, Grocery Shopping" />
              <span v-if="formErrors.title" class="field-error">{{ formErrors.title }}</span>
            </div>

            <!-- Amount -->
            <div class="form-group">
              <label class="form-label" for="txn-amount">Amount (₹) <span class="req">*</span></label>
              <div class="amount-wrap">
                <span class="amount-prefix">₹</span>
                <input id="txn-amount" v-model="form.amount" type="number" min="0.01" step="0.01"
                       class="form-input amount-input" :class="{ 'input-error': formErrors.amount }"
                       placeholder="0.00" />
              </div>
              <span v-if="formErrors.amount" class="field-error">{{ formErrors.amount }}</span>
            </div>

            <!-- Category -->
            <div class="form-group">
              <label class="form-label" for="txn-category">Category <span class="req">*</span></label>
              <div class="cat-input-wrap">
                <select id="txn-category" v-model="form.category"
                        class="form-input" :class="{ 'input-error': formErrors.category }"
                        @change="customCategory = ''">
                  <option value="" disabled>Select a category</option>
                  <optgroup label="Common">
                    <option v-for="c in CATEGORIES" :key="c" :value="c">{{ capitalise(c) }}</option>
                  </optgroup>
                  <option value="__custom__">+ Custom category…</option>
                </select>
              </div>
              <!-- Custom category input -->
              <input v-if="form.category === '__custom__'" v-model.trim="customCategory"
                     type="text" class="form-input" style="margin-top:6px"
                     placeholder="Enter custom category" />
              <span v-if="formErrors.category" class="field-error">{{ formErrors.category }}</span>
            </div>

            <!-- Date -->
            <div class="form-group">
              <label class="form-label" for="txn-date">Date <span class="req">*</span></label>
              <input id="txn-date" v-model="form.date" type="date"
                     class="form-input" :class="{ 'input-error': formErrors.date }"
                     :max="todayISO" />
              <span v-if="formErrors.date" class="field-error">{{ formErrors.date }}</span>
            </div>

            <!-- Submit error -->
            <div v-if="submitError" class="submit-error">
              <span class="material-symbols-outlined icon-sm">error</span>
              {{ submitError }}
            </div>

            <!-- Actions -->
            <div class="modal-actions">
              <button type="button" class="btn btn-ghost" @click="closeAddModal" :disabled="submitting">Cancel</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                <span v-if="submitting" class="material-symbols-outlined icon-sm spinning">refresh</span>
                <span v-else class="material-symbols-outlined icon-sm">check_circle</span>
                {{ submitting ? 'Saving…' : (editingTxnId ? 'Save Changes' : 'Add Transaction') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- ── Bulk Upload Modal (upload + results only) ────────────────── -->
    <Transition name="modal">
      <div v-if="showBulkModal" class="modal-backdrop" @click.self="closeBulkModal">
        <div class="modal-panel bulk-modal-panel" role="dialog" aria-modal="true" aria-label="Bulk Upload">

          <!-- Header -->
          <div class="modal-header">
            <div class="modal-title-wrap">
              <div class="modal-icon-wrap" style="background:var(--col-surface-mid)">
                <span class="material-symbols-outlined icon-filled" style="font-size:20px;color:var(--col-text-secondary)">cloud_upload</span>
              </div>
              <div>
                <div class="t-headline" style="font-size:1.1rem">Upload Transactions</div>
                <div class="t-label text-muted">Import up to 500 transactions from your .xlsx file</div>
              </div>
            </div>
            <button class="btn btn-icon" @click="closeBulkModal" :disabled="bulkUploading">
              <span class="material-symbols-outlined icon-sm">close</span>
            </button>
          </div>

          <div class="modal-body">

            <!-- Upload state -->
            <template v-if="!bulkDone">
              <!-- Drop zone -->
              <div class="drop-zone"
                   :class="{ 'drop-hover': isDragOver, 'file-chosen': !!bulkFile }"
                   @dragover.prevent="isDragOver = true"
                   @dragleave="isDragOver = false"
                   @drop.prevent="onFileDrop"
                   @click="$refs.fileInput.click()">
                <input ref="fileInput" type="file" accept=".xlsx" style="display:none"
                       @change="onFileChange" />
                <template v-if="!bulkFile">
                  <span class="material-symbols-outlined" style="font-size:40px;color:var(--col-text-faint)">upload_file</span>
                  <div class="t-body" style="font-weight:600;color:var(--col-text-secondary)">Drop your .xlsx file here</div>
                  <div class="t-label text-muted">or click to browse &nbsp;·&nbsp; .xlsx only</div>
                </template>
                <template v-else>
                  <span class="material-symbols-outlined" style="font-size:36px;color:var(--col-accent)">check_circle</span>
                  <div class="t-body" style="font-weight:700;color:var(--col-text-primary)">{{ bulkFile.name }}</div>
                  <div class="t-label text-muted">{{ (bulkFile.size / 1024).toFixed(1) }} KB &nbsp;·&nbsp; Click to change</div>
                </template>
              </div>

              <div v-if="bulkFileError" class="submit-error">
                <span class="material-symbols-outlined icon-sm">error</span>
                {{ bulkFileError }}
              </div>

              <div class="modal-actions">
                <button class="btn btn-ghost" @click="closeBulkModal" :disabled="bulkUploading">Cancel</button>
                <button class="btn btn-primary" @click="uploadFile" :disabled="!bulkFile || bulkUploading">
                  <span v-if="bulkUploading" class="material-symbols-outlined icon-sm spinning">refresh</span>
                  <span v-else class="material-symbols-outlined icon-sm">cloud_upload</span>
                  {{ bulkUploading ? 'Uploading…' : 'Upload File' }}
                </button>
              </div>
            </template>

            <!-- Results state -->
            <template v-else>
              <!-- Success -->
              <div v-if="bulkResult.success" class="bulk-result-success">
                <span class="material-symbols-outlined" style="font-size:52px;color:var(--col-accent)">task_alt</span>
                <div class="t-headline" style="font-size:1.2rem;color:var(--col-accent)">Upload Successful!</div>
                <div class="t-body text-muted">
                  <strong style="color:var(--col-text-primary)">{{ bulkResult.count }}</strong> transactions imported successfully.
                </div>
              </div>

              <!-- Error -->
              <div v-else class="bulk-result-error">
                <div class="bulk-error-header">
                  <span class="material-symbols-outlined" style="font-size:28px;color:var(--col-error)">error</span>
                  <div>
                    <div class="t-title" style="color:var(--col-error)">Validation Failed</div>
                    <div class="t-label text-muted">Fix the errors and re-upload. No transactions were saved.</div>
                  </div>
                </div>
                <div class="bulk-error-list">
                  <div v-for="(errs, rowKey) in bulkResult.rowErrors" :key="rowKey" class="bulk-error-row">
                    <span class="bulk-row-label">{{ rowKey.replace('_', ' ').toUpperCase() }}</span>
                    <div class="bulk-row-msgs">
                      <span v-for="(msgs, field) in errs" :key="field" class="bulk-row-msg">
                        <strong>{{ field }}:</strong> {{ Array.isArray(msgs) ? msgs.join(', ') : msgs }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="modal-actions">
                <button class="btn btn-ghost" @click="resetBulk">Upload Another File</button>
                <button class="btn btn-primary" @click="closeBulkModal">Done</button>
              </div>
            </template>

          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// ── v-click-outside directive (closes dropdown when clicking away) ─
const vClickOutside = {
  mounted(el, binding) {
    el.__clickOutside__ = (e) => { if (!el.contains(e.target)) binding.value(e) }
    document.addEventListener('pointerdown', el.__clickOutside__)
  },
  unmounted(el) {
    document.removeEventListener('pointerdown', el.__clickOutside__)
    delete el.__clickOutside__
  },
}

// ── API base URL ──────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000/api/finance-buddy'

// ── Auth helper ───────────────────────────────────────────────────
function getAuthHeaders() {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ── Server-side filter state ──────────────────────────────────────
const now = new Date()
const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const currentYear      = now.getFullYear()

const filterMode    = ref('current_month')   // 'current_month' | 'month' | 'year'
const selectedMonth = ref(currentYearMonth)  // YYYY-MM
const selectedYear  = ref(currentYear)       // YYYY (number)

// Years available in the selector (last 5 years up to current)
const availableYears = computed(() => {
  const yrs = []
  for (let y = currentYear; y >= currentYear - 4; y--) yrs.push(y)
  return yrs
})

// Human-readable label shown next to count
const filterLabel = computed(() => {
  if (filterMode.value === 'month') {
    const [y, m] = selectedMonth.value.split('-')
    const d = new Date(+y, +m - 1, 1)
    return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
  }
  if (filterMode.value === 'year') return `Year ${selectedYear.value}`
  const d = new Date()
  return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
})

// ── API loading state ─────────────────────────────────────────────
const loading  = ref(false)
const apiError = ref('')

// ── Transaction data ──────────────────────────────────────────────
const transactions = ref([])

async function fetchTransactions() {
  loading.value  = true
  apiError.value = ''

  // Build query string
  const params = new URLSearchParams()
  if (filterMode.value === 'month') {
    params.set('month', selectedMonth.value)
  } else if (filterMode.value === 'year') {
    params.set('year', String(selectedYear.value))
  }
  // current_month → no params (backend defaults to current month)

  const qs = params.toString() ? `?${params.toString()}` : ''
  try {
    const res = await fetch(`${API_BASE}/transaction/list${qs}`, {
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.error || `Server error ${res.status}`)
    }
    const data = await res.json()
    transactions.value = data.transactions || []
  } catch (err) {
    apiError.value = err.message || 'Failed to load transactions'
  } finally {
    loading.value = false
  }
}

function onFilterModeChange() {
  fetchTransactions()
}

onMounted(() => fetchTransactions())

// ── Add Transaction Modal ─────────────────────────────────────────
const CATEGORIES = [
  'food/grocery', 'utilities/bills', 'travel', 'education', 'EMIs',
  'health', 'personal expenses', 'rental', 'investment/SIPs',
  'salary', 'incentives/bonus', 'entertainment', 'shopping', 'other',
]

const todayISO = new Date().toISOString().slice(0, 10)

const showAddModal  = ref(false)
const submitting    = ref(false)
const submitError   = ref('')
const customCategory = ref('')
const editingTxnId  = ref(null)
const isDeleting    = ref(null)

const form = ref({
  title: '',
  amount: '',
  transaction_type: 'Expense',
  category: '',
  date: todayISO,
})

const formErrors = ref({
  title: '', amount: '', transaction_type: '', category: '', date: ''
})

function openAddModal() {
  editingTxnId.value = null
  form.value = { title: '', amount: '', transaction_type: 'Expense', category: '', date: todayISO }
  formErrors.value = { title: '', amount: '', transaction_type: '', category: '', date: '' }
  customCategory.value = ''
  submitError.value = ''
  showAddModal.value = true
}

function editTransaction(txn) {
  editingTxnId.value = txn.id
  form.value = {
    title: txn.title,
    amount: parseFloat(txn.amount).toString(),
    transaction_type: txn.transaction_type,
    category: CATEGORIES.includes(txn.category) ? txn.category : '__custom__',
    date: txn.date.slice(0, 10),
  }
  if (!CATEGORIES.includes(txn.category)) {
    customCategory.value = txn.category
  } else {
    customCategory.value = ''
  }
  formErrors.value = { title: '', amount: '', transaction_type: '', category: '', date: '' }
  submitError.value = ''
  selectedTxn.value = null // Close drawer
  showAddModal.value = true
}

async function deleteTransaction(id) {
  if (!confirm('Are you sure you want to delete this transaction?')) return
  isDeleting.value = id
  try {
    const res = await fetch(`${API_BASE}/transaction`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ id }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.error || `Server error ${res.status}`)
    }
    if (selectedTxn.value && selectedTxn.value.id === id) {
      selectedTxn.value = null
    }
    await fetchTransactions()
  } catch (err) {
    alert(err.message || 'Failed to delete transaction.')
  } finally {
    isDeleting.value = null
  }
}

function closeAddModal() {
  showAddModal.value = false
}

function validateForm() {
  const e = { title: '', amount: '', transaction_type: '', category: '', date: '' }
  let ok = true
  if (!form.value.title) { e.title = 'Title is required.'; ok = false }
  if (!form.value.amount || parseFloat(form.value.amount) <= 0) { e.amount = 'Enter a valid positive amount.'; ok = false }
  if (!form.value.transaction_type) { e.transaction_type = 'Select Income or Expense.'; ok = false }
  const cat = form.value.category === '__custom__' ? customCategory.value : form.value.category
  if (!cat) { e.category = 'Category is required.'; ok = false }
  if (!form.value.date) { e.date = 'Date is required.'; ok = false }
  formErrors.value = e
  return ok
}

async function submitTransaction() {
  if (!validateForm()) return
  submitting.value = true
  submitError.value = ''

  const resolvedCategory = form.value.category === '__custom__' ? customCategory.value : form.value.category

  const payload = {
    title: form.value.title,
    amount: parseFloat(form.value.amount).toFixed(2),
    transaction_type: form.value.transaction_type,
    category: resolvedCategory,
    date: form.value.date,
  }

  if (editingTxnId.value) {
    payload.id = editingTxnId.value
  }

  try {
    const res = await fetch(`${API_BASE}/transaction`, {
      method: editingTxnId.value ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.error || JSON.stringify(body) || `Server error ${res.status}`)
    }
    closeAddModal()
    await fetchTransactions()   // refresh list
  } catch (err) {
    submitError.value = err.message || 'Failed to create transaction.'
  } finally {
    submitting.value = false
  }
}

// ── Bulk Upload Modal ──────────────────────────────────────────────
const showBulkDropdown = ref(false)
const showBulkModal    = ref(false)
const bulkDone         = ref(false)
const bulkFile         = ref(null)
const bulkFileError    = ref('')
const bulkUploading    = ref(false)
const bulkDownloading  = ref(false)
const isDragOver       = ref(false)
const bulkResult       = ref({ success: false, count: 0, rowErrors: {} })

function onDownloadTemplate() {
  showBulkDropdown.value = false
  downloadTemplate()
}
function onUploadClick() {
  showBulkDropdown.value = false
  resetBulk()
  showBulkModal.value = true
}
function closeBulkModal() {
  showBulkModal.value = false
}
function resetBulk() {
  bulkDone.value      = false
  bulkFile.value      = null
  bulkFileError.value = ''
  bulkResult.value    = { success: false, count: 0, rowErrors: {} }
  isDragOver.value    = false
}

function onFileChange(e) {
  const file = e.target.files[0]
  setFile(file)
}
function onFileDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  setFile(file)
}
function setFile(file) {
  bulkFileError.value = ''
  if (!file) return
  if (!file.name.endsWith('.xlsx')) {
    bulkFileError.value = 'Only .xlsx files are accepted. Please download the template and use Excel.'
    bulkFile.value = null
    return
  }
  bulkFile.value = file
}

async function downloadTemplate() {
  bulkDownloading.value = true
  try {
    const res = await fetch(`${API_BASE}/transaction/bulk?mode=download`, {
      headers: { ...getAuthHeaders() },
    })
    if (!res.ok) throw new Error(`Server error ${res.status}`)
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = 'transaction_template.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    bulkFileError.value = err.message || 'Failed to download template.'
  } finally {
    bulkDownloading.value = false
  }
}

async function uploadFile() {
  if (!bulkFile.value) return
  bulkUploading.value = true
  bulkFileError.value = ''
  const fd = new FormData()
  fd.append('file', bulkFile.value)
  try {
    const res = await fetch(`${API_BASE}/transaction/bulk?mode=upload`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },   // no Content-Type — browser sets multipart boundary
      body: fd,
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      bulkResult.value = { success: true, count: data.transactions?.length ?? 0, rowErrors: {} }
      await fetchTransactions()  // refresh list
    } else {
      bulkResult.value = {
        success: false,
        count: 0,
        rowErrors: data.row_errors || {},
        message: data.error || 'Upload failed.',
      }
    }
    bulkDone.value = true
  } catch (err) {
    bulkFileError.value = err.message || 'Upload failed. Please try again.'
  } finally {
    bulkUploading.value = false
  }
}

// ── Client-side filter state ──────────────────────────────────────
const searchQuery    = ref('')
const typeFilter     = ref('All')
const categoryFilter = ref('')
const sortField      = ref('date')
const sortDir        = ref('desc')
const selectedTxn    = ref(null)

// ── Filtering (client-side on top of API results) ────────────────
const filteredTransactions = computed(() => {
  let list = [...transactions.value]

  // Text search
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(t => t.title.toLowerCase().includes(q) || t.category.toLowerCase().includes(q))
  }
  // Type
  if (typeFilter.value !== 'All') list = list.filter(t => t.transaction_type === typeFilter.value)
  // Category
  if (categoryFilter.value) list = list.filter(t => t.category === categoryFilter.value)

  // Sort
  list.sort((a, b) => {
    let va, vb
    if (sortField.value === 'date')   { va = a.date;                vb = b.date }
    if (sortField.value === 'amount') { va = parseFloat(a.amount);  vb = parseFloat(b.amount) }
    if (sortField.value === 'title')  { va = a.title.toLowerCase(); vb = b.title.toLowerCase() }
    if (va < vb) return sortDir.value === 'asc' ? -1 : 1
    if (va > vb) return sortDir.value === 'asc' ? 1 : -1
    return 0
  })
  return list
})

// ── Group by date ─────────────────────────────────────────────────
const groupedTransactions = computed(() => {
  const groups = {}
  for (const t of filteredTransactions.value) {
    if (!groups[t.date]) groups[t.date] = []
    groups[t.date].push(t)
  }
  return groups
})

// ── Sorting ───────────────────────────────────────────────────────
function setSort(field) {
  if (sortField.value === field) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else { sortField.value = field; sortDir.value = 'desc' }
}
function sortIcon(field) {
  if (sortField.value !== field) return '↕'
  return sortDir.value === 'asc' ? '↑' : '↓'
}

// ── Computed totals ───────────────────────────────────────────────
const totalIncome   = computed(() => filteredTransactions.value.filter(t => t.transaction_type === 'Income').reduce((s,t) => s+parseFloat(t.amount), 0))
const totalExpenses = computed(() => filteredTransactions.value.filter(t => t.transaction_type === 'Expense').reduce((s,t) => s+parseFloat(t.amount), 0))
const netAmount     = computed(() => totalIncome.value - totalExpenses.value)

// ── Helpers ───────────────────────────────────────────────────────
const allCategories = computed(() => [...new Set(transactions.value.map(t => t.category))].sort())
function dateNet(group) { return group.reduce((s,t) => s + (t.transaction_type==='Income' ? 1 : -1) * parseFloat(t.amount), 0) }
function capitalise(s)  { return s.split(' ').map(w => w[0].toUpperCase()+w.slice(1)).join(' ') }
function fmt(v)         { return Number(v).toLocaleString('en-IN', { minimumFractionDigits:2, maximumFractionDigits:2 }) }
function fmtDate(iso)   {
  return new Date(iso).toLocaleDateString('en-IN', { weekday:'short', day:'numeric', month:'long', year:'numeric' })
}
function fmtDateShort(iso) {
  return new Date(iso).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })
}

// ── Category palette ──────────────────────────────────────────────
const CAT = {
  'food/grocery':     { bg:'#e8f5e9', col:'#2e7d32', icon:'restaurant'      },
  'utilities/bills':  { bg:'#e3f2fd', col:'#1565c0', icon:'bolt'            },
  'travel':           { bg:'#fff8e1', col:'#f57f17', icon:'flight_takeoff'  },
  'education':        { bg:'#f3e5f5', col:'#7b1fa2', icon:'school'          },
  'EMIs':             { bg:'#fce4ec', col:'#c62828', icon:'account_balance' },
  'health':           { bg:'#e8f5e9', col:'#1b5e20', icon:'favorite'        },
  'personal expenses':{ bg:'#fff3e0', col:'#e65100', icon:'shopping_bag'    },
  'rental':           { bg:'#e8eaf6', col:'#283593', icon:'home'            },
  'investment/SIPs':  { bg:'#e0f7fa', col:'#006064', icon:'trending_up'     },
  'salary':           { bg:'#e8f5e9', col:'#1b5e20', icon:'payments'        },
  'incentives/bonus': { bg:'#fffde7', col:'#f57f17', icon:'star'            },
}
const DP = { bg:'var(--col-surface-mid)', col:'var(--col-text-muted)', icon:'receipt' }
function catBg(c)       { return (CAT[c]||DP).bg }
function catColor(c)    { return (CAT[c]||DP).col }
function catIcon(c, tp) { return tp === 'Income' ? 'arrow_circle_down' : (CAT[c]||DP).icon }
</script>

<style scoped>
.txn-root { display: flex; flex-direction: column; gap: var(--space-lg); }

/* Page heading */
.page-heading {
  display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: var(--space-md);
  position: relative;
  z-index: 10;
}
.heading-actions { display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; }

/* API filter bar */
.api-filter-wrap {
  display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap;
}

/* Filter label badge shown next to transaction count */
.filter-label-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--col-accent-light);
  color: var(--col-accent);
  border-radius: var(--r-full);
  font-size: 0.7rem; font-weight: 700;
  margin-left: 6px;
}

/* Spinning refresh icon */
@keyframes spin { to { transform: rotate(360deg); } }
.spinning { animation: spin 0.8s linear infinite; }


.date-input {
  padding: 7px 10px;
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
  font-family: inherit; font-size: 0.8125rem;
  color: var(--col-text-primary);
  background: var(--col-surface-low);
  outline: none; cursor: pointer; width: 100%;
}
.date-input:focus { border-color: var(--col-accent); }
.date-picker-actions { display: flex; justify-content: space-between; align-items: center; }
.quick-ranges { display: flex; flex-wrap: wrap; gap: 4px; }
.quick-btn {
  padding: 3px 8px;
  border: 1px solid var(--col-border);
  border-radius: var(--r-full);
  background: var(--col-surface-low);
  font-family: inherit; font-size: 0.625rem; font-weight: 600;
  color: var(--col-text-secondary);
  cursor: pointer; white-space: nowrap;
  transition: background var(--dur-fast), border-color var(--dur-fast), color var(--dur-fast);
}
.quick-btn:hover { background: var(--col-accent-light); border-color: var(--col-accent); color: var(--col-accent); }
.api-params-preview {
  padding: 6px 8px;
  background: var(--col-surface-low);
  border-radius: var(--r-sm);
  border: 1px dashed var(--col-border);
  display: flex; align-items: center; gap: 4px;
  overflow-x: auto;
}

/* Summary strip */
.summary-strip {
  display: flex; align-items: center; gap: var(--space-md); flex-wrap: wrap;
  padding: var(--space-md) var(--space-lg);
  background: var(--col-surface-card);
  border: 1px solid var(--col-border);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-card);
}
.summary-chip { display: flex; align-items: center; gap: 8px; }
.summary-divider { width:1px; height:28px; background:var(--col-border); flex-shrink:0; }

/* Search */
.search-wrap {
  display: flex; align-items: center;
  background: var(--col-surface-low);
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
  padding: 0 8px;
  flex: 1; min-width: 160px;
}
.search-input {
  flex:1; border:none; background:transparent;
  padding: 6px 6px; font-family:inherit; font-size:0.875rem;
  color:var(--col-text-primary); outline:none;
}
.search-input::placeholder { color:var(--col-text-faint); }
.cat-select {
  padding: 6px 10px;
  border: 1px solid var(--col-border); border-radius: var(--r-md);
  background: var(--col-surface-low);
  font-family: inherit; font-size: 0.75rem; font-weight: 600;
  color: var(--col-text-primary); cursor: pointer; outline: none;
}
.cat-select:focus { border-color: var(--col-accent); }

/* Table card */
.txn-card {}
.table-wrap { overflow-x: auto; }
.txn-table { width: 100%; border-collapse: collapse; }

/* Table header */
.txn-table thead tr {
  background: var(--col-surface-low);
  border-bottom: 1px solid var(--col-border);
}
.txn-table th {
  padding: 12px 20px;
  font-size: 0.625rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--col-text-faint);
  white-space: nowrap;
}
.th-sortable { cursor: pointer; user-select: none; }
.th-sortable:hover { color: var(--col-text-primary); }
.sort-icon { margin-left: 2px; font-size: 0.7rem; color: var(--col-text-faint); }
.text-right { text-align: right; }

/* Group header row */
.group-row td { padding: 0; }
.group-header {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 20px;
  background: var(--col-surface-low);
  border-top: 1px solid var(--col-border);
  border-bottom: 1px solid var(--col-border-muted);
  position: sticky; top: 68px; z-index: 5;
}
.group-divider { flex:1; height:1px; background:var(--col-border); }

/* Transaction row */
.txn-row {
  border-bottom: 1px solid var(--col-border-muted);
  transition: background var(--dur-fast);
  cursor: pointer;
}
.txn-row:last-of-type { border-bottom: none; }
.txn-row:hover { background: var(--col-surface-low); }
.txn-row td { padding: 13px 20px; vertical-align: middle; }
.td-title { min-width: 200px; }
.td-cat   { white-space: nowrap; }
.td-date  { white-space: nowrap; font-size: 0.8125rem; }
.td-amount{ text-align: right; white-space: nowrap; }

.txn-title-cell { display: flex; align-items: center; gap: 10px; }
.txn-icon {
  width: 34px; height: 34px; border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

/* Type pills */
.type-pill {
  display: inline-block; padding: 2px 8px; border-radius: var(--r-full);
  font-size: 0.625rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.type-income  { background: var(--col-accent-light); color: var(--col-accent); }
.type-expense { background: var(--col-error-bg);     color: var(--col-error); }

/* Table footer */
.table-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 20px;
  border-top: 1px solid var(--col-border);
  background: var(--col-surface-low);
}

/* Empty state */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-sm); padding: var(--space-2xl);
}

/* Drawer */
.drawer-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(19,27,46,0.3);
  backdrop-filter: blur(2px);
  display: flex; justify-content: flex-end;
}
.drawer {
  width: 360px; max-width: 95vw;
  background: var(--col-surface-card);
  height: 100%;
  box-shadow: -4px 0 32px rgba(0,0,0,0.12);
  display: flex; flex-direction: column;
  overflow-y: auto;
}
.drawer-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--col-border);
}
.txn-icon-lg {
  width: 56px; height: 56px; border-radius: var(--r-lg);
  display: flex; align-items: center; justify-content: center;
}
.drawer-body { padding: var(--space-lg); display: flex; flex-direction: column; gap: var(--space-md); }
.drawer-rows { display: flex; flex-direction: column; gap: 12px; }
.drawer-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--col-border-muted); }
.drawer-row:last-child { border-bottom: none; }

/* Drawer transition */
.drawer-enter-active, .drawer-leave-active { transition: transform 0.25s var(--ease-out), opacity 0.25s; }
.drawer-enter-from { transform: translateX(100%); opacity: 0; }
.drawer-leave-to   { transform: translateX(100%); opacity: 0; }

/* ── Add Transaction Modal ─────────────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(10,14,30,0.55);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  padding: var(--space-md);
}
.modal-panel {
  background: var(--col-surface-card);
  border: 1px solid var(--col-border);
  border-radius: var(--r-xl, 20px);
  box-shadow: 0 24px 64px rgba(0,0,0,0.22);
  width: 100%; max-width: 480px;
  max-height: 92vh;
  overflow-y: auto;
  display: flex; flex-direction: column;
}

/* Modal header */
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--col-border);
  position: sticky; top: 0; z-index: 1;
  background: var(--col-surface-card);
  border-radius: var(--r-xl, 20px) var(--r-xl, 20px) 0 0;
}
.modal-title-wrap { display: flex; align-items: center; gap: 12px; }
.modal-icon-wrap {
  width: 40px; height: 40px; border-radius: var(--r-md);
  background: var(--col-accent-light);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

/* Modal body / form */
.modal-body {
  padding: var(--space-lg);
  display: flex; flex-direction: column; gap: var(--space-md);
}
.form-group { display: flex; flex-direction: column; gap: 5px; }
.form-label {
  font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em;
  color: var(--col-text-secondary); text-transform: uppercase;
}
.req { color: var(--col-error); margin-left: 2px; }
.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1.5px solid var(--col-border);
  border-radius: var(--r-md);
  font-family: inherit; font-size: 0.9rem;
  color: var(--col-text-primary);
  background: var(--col-surface-low);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}
.form-input:focus {
  border-color: var(--col-accent);
  box-shadow: 0 0 0 3px rgba(var(--col-accent-rgb, 34,197,94), 0.12);
}
.form-input.input-error { border-color: var(--col-error); }
.field-error { font-size: 0.72rem; color: var(--col-error); }

/* Type toggle */
.type-toggle { display: flex; gap: 8px; }
.type-toggle-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 10px 12px;
  border: 1.5px solid var(--col-border);
  border-radius: var(--r-md);
  background: var(--col-surface-low);
  font-family: inherit; font-size: 0.875rem; font-weight: 600;
  color: var(--col-text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.type-toggle-btn:hover { border-color: var(--col-accent); color: var(--col-text-primary); }
.type-toggle-btn.active-income {
  border-color: var(--col-accent);
  background: var(--col-accent-light);
  color: var(--col-accent);
}
.type-toggle-btn.active-expense {
  border-color: var(--col-error);
  background: var(--col-error-bg);
  color: var(--col-error);
}

/* Amount field with ₹ prefix */
.amount-wrap { position: relative; display: flex; align-items: center; }
.amount-prefix {
  position: absolute; left: 12px;
  font-size: 0.95rem; font-weight: 700;
  color: var(--col-text-muted);
  pointer-events: none;
}
.amount-input { padding-left: 28px; }

/* Category select */
.cat-input-wrap { position: relative; }
.cat-input-wrap select.form-input { appearance: auto; }

/* Submit error */
.submit-error {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 12px;
  background: var(--col-error-bg);
  border: 1px solid var(--col-error);
  border-radius: var(--r-md);
  font-size: 0.8125rem; color: var(--col-error);
}

/* Modal actions */
.modal-actions {
  display: flex; justify-content: flex-end; gap: var(--space-sm);
  padding-top: var(--space-sm);
  border-top: 1px solid var(--col-border);
  margin-top: var(--space-xs, 4px);
}

/* Modal transition */
.modal-enter-active { transition: opacity 0.2s, transform 0.22s var(--ease-out); }
.modal-leave-active { transition: opacity 0.18s, transform 0.18s ease-in; }
.modal-enter-from { opacity: 0; transform: scale(0.95) translateY(12px); }
.modal-leave-to   { opacity: 0; transform: scale(0.97) translateY(8px); }

/* ── Bulk Upload Modal ─────────────────────────────────────────── */
.bulk-modal-panel { max-width: 540px; }

/* Step indicator */
.bulk-steps {
  display: flex; align-items: center; gap: 0;
  padding: var(--space-sm) 0 var(--space-md);
  margin-bottom: var(--space-xs, 4px);
}
.bulk-step {
  display: flex; align-items: center; gap: 8px;
  flex: 1; position: relative;
}
.bulk-step:not(:last-child)::after {
  content: '';
  position: absolute; left: calc(100% - 10px); top: 50%;
  width: calc(100% - 20px); height: 2px;
  background: var(--col-border);
  transform: translateY(-50%);
  z-index: 0;
}
.bulk-step.done:not(:last-child)::after { background: var(--col-accent); }
.bulk-step-num {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700;
  background: var(--col-surface-mid);
  color: var(--col-text-muted);
  border: 2px solid var(--col-border);
  flex-shrink: 0; z-index: 1; position: relative;
  transition: all 0.2s;
}
.bulk-step.active .bulk-step-num {
  background: var(--col-accent-light);
  color: var(--col-accent);
  border-color: var(--col-accent);
}
.bulk-step.done .bulk-step-num {
  background: var(--col-accent);
  color: #fff;
  border-color: var(--col-accent);
}
.bulk-step .t-label { font-size: 0.68rem; color: var(--col-text-faint); white-space: nowrap; }
.bulk-step.active .t-label { color: var(--col-accent); font-weight: 700; }
.bulk-step.done .t-label { color: var(--col-text-muted); }

.bulk-step-body { display: flex; flex-direction: column; gap: var(--space-md); }

/* Info box */
.bulk-info-box {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px 14px;
  background: var(--col-accent-light);
  border: 1px solid var(--col-accent);
  border-radius: var(--r-md);
}

/* Column chips */
.bulk-col-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.bulk-col-chip {
  padding: 3px 10px;
  background: var(--col-surface-low);
  border: 1px solid var(--col-border);
  border-radius: var(--r-full);
  font-size: 0.72rem; font-weight: 600;
  color: var(--col-text-secondary);
  font-family: monospace;
}

/* Drag-and-drop zone */
.drop-zone {
  border: 2px dashed var(--col-border);
  border-radius: var(--r-lg);
  padding: var(--space-xl) var(--space-lg);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--col-surface-low);
  min-height: 160px;
}
.drop-zone:hover, .drop-zone.drop-hover {
  border-color: var(--col-accent);
  background: var(--col-accent-light);
}
.drop-zone.file-chosen {
  border-color: var(--col-accent);
  border-style: solid;
  background: var(--col-accent-light);
}

/* Success result */
.bulk-result-success {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-sm);
  padding: var(--space-xl) 0;
  text-align: center;
}

/* Error result */
.bulk-result-error { display: flex; flex-direction: column; gap: var(--space-md); }
.bulk-error-header { display: flex; align-items: flex-start; gap: 10px; }
.bulk-error-list {
  display: flex; flex-direction: column; gap: 6px;
  max-height: 220px; overflow-y: auto;
  padding: 6px;
  background: var(--col-surface-low);
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
}
.bulk-error-row {
  display: flex; gap: 8px; flex-direction: column;
  padding: 8px 10px;
  background: var(--col-error-bg);
  border: 1px solid var(--col-error);
  border-radius: var(--r-sm);
}
.bulk-row-label {
  font-size: 0.65rem; font-weight: 800; letter-spacing: 0.07em;
  color: var(--col-error);
}
.bulk-row-msgs { display: flex; flex-direction: column; gap: 2px; }
.bulk-row-msg { font-size: 0.78rem; color: var(--col-text-primary); }

/* Accent button (Next step) */
.btn-accent {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px;
  background: var(--col-surface-mid);
  border: 1.5px solid var(--col-border);
  border-radius: var(--r-md);
  font-family: inherit; font-size: 0.8125rem; font-weight: 600;
  color: var(--col-text-secondary);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.btn-accent:hover {
  background: var(--col-accent-light);
  border-color: var(--col-accent);
  color: var(--col-accent);
}

/* ── Bulk Upload dropdown \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 */
.bulk-dropdown-wrap {
  position: relative;
}
.bulk-main-btn {
  display: inline-flex; align-items: center; gap: 5px;
}
.bulk-dropdown-menu {
  position: absolute; top: calc(100% + 6px); right: 0; z-index: 80;
  min-width: 220px;
  background: var(--col-surface-card);
  border: 1px solid var(--col-border);
  border-radius: var(--r-lg);
  box-shadow: 0 8px 32px rgba(0,0,0,0.14);
  padding: 6px;
  display: flex; flex-direction: column; gap: 2px;
}
.bulk-dropdown-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 10px 12px;
  border: none; border-radius: var(--r-md);
  background: transparent;
  font-family: inherit; text-align: left; cursor: pointer;
  transition: background 0.12s;
  color: var(--col-text-primary);
}
.bulk-dropdown-item:hover { background: var(--col-surface-low); }
.bulk-dropdown-item .material-symbols-outlined {
  color: var(--col-text-muted); flex-shrink: 0;
}
.bulk-item-title { font-size: 0.875rem; font-weight: 600; line-height: 1.2; }
.bulk-item-sub   { font-size: 0.72rem; color: var(--col-text-faint); margin-top: 1px; }
.bulk-dropdown-divider {
  height: 1px; background: var(--col-border); margin: 2px 4px;
}

/* dropdown open/close animation */
.dropdown-enter-active { transition: opacity 0.15s, transform 0.15s; }
.dropdown-leave-active { transition: opacity 0.1s, transform 0.1s; }
.dropdown-enter-from { opacity: 0; transform: scale(0.96) translateY(-4px); }
.dropdown-leave-to   { opacity: 0; transform: scale(0.97) translateY(-2px); }
</style>
