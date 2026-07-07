<template>
  <div class="login-root">

    <!-- ── Header ─────────────────────────────────────────────── -->
    <header class="login-header">
      <div class="login-header-inner">
        <div class="brand">
          <img src="/logo.png" alt="FinanceBuddy" class="login-logo" />
        </div>
        <a class="btn btn-ghost" style="font-size:0.8125rem;font-weight:700" @click.prevent="$emit('go-register')">
          Create Account
        </a>
      </div>
    </header>

    <!-- ── Main ───────────────────────────────────────────────── -->
    <main class="login-main">
      <!-- Mesh gradient background -->
      <div class="login-bg" aria-hidden="true"></div>

      <!-- Floating shapes -->
      <div class="floating-shape shape-1" aria-hidden="true"></div>
      <div class="floating-shape shape-2" aria-hidden="true"></div>
      <div class="floating-shape shape-3" aria-hidden="true"></div>

      <!-- Card -->
      <section class="login-card-wrap">
        <div class="login-card">

          <!-- Lock icon -->
          <div class="login-icon-wrap">
            <div class="login-icon-ring">
              <span class="material-symbols-outlined login-icon-glyph">lock_open</span>
            </div>
          </div>

          <!-- Heading -->
          <div class="login-card-head">
            <h1 class="t-display" style="font-size:2rem;letter-spacing:-0.03em;color:var(--col-primary)">
              Welcome Back
            </h1>
            <p class="t-body text-muted" style="margin-top:4px">
              Sign in to your FinanceBuddy account
            </p>
          </div>

          <!-- Error banner -->
          <Transition name="fade-up">
            <div v-if="apiError" class="error-banner">
              <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-error)">error</span>
              {{ apiError }}
            </div>
          </Transition>

          <!-- Form -->
          <form class="login-form" @submit.prevent="handleSubmit" novalidate>

            <!-- Username -->
            <div class="field-group">
              <label class="t-label text-muted" for="login-username">USERNAME</label>
              <div class="input-wrap">
                <input
                  id="login-username"
                  v-model="form.username"
                  type="text"
                  class="login-input"
                  :class="{ 'input-error': errors.username }"
                  placeholder="Enter your username"
                  autocomplete="username"
                  @blur="validateField('username')"
                  @input="clearApiError"
                />
                <span class="material-symbols-outlined input-icon">person</span>
              </div>
              <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
            </div>

            <!-- Password -->
            <div class="field-group">
              <div class="password-label-row">
                <label class="t-label text-muted" for="login-password">PASSWORD</label>
                <button type="button" class="show-btn" @click="showPassword = !showPassword">
                  {{ showPassword ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
              <div class="input-wrap">
                <input
                  id="login-password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="login-input"
                  :class="{ 'input-error': errors.password }"
                  placeholder="••••••••"
                  autocomplete="current-password"
                  @blur="validateField('password')"
                  @input="clearApiError"
                  @keyup.enter="handleSubmit"
                />
                <span class="material-symbols-outlined input-icon">lock</span>
              </div>
              <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
            </div>

            <!-- Remember & Forgot -->
            <div class="login-options-row">
              <label class="remember-label">
                <input v-model="rememberMe" type="checkbox" class="remember-check" />
                <span class="t-label" style="color:var(--col-text-secondary);font-size:0.75rem;cursor:pointer">
                  Remember me
                </span>
              </label>
              <a href="#" class="forgot-link" @click.prevent>Forgot Password?</a>
            </div>

            <!-- Submit -->
            <button
              type="submit"
              class="btn-submit"
              :class="{ 'btn-loading': loading }"
              :disabled="loading"
            >
              <span v-if="loading" class="spinner"></span>
              <span v-else class="material-symbols-outlined icon-sm icon-filled">login</span>
              {{ loading ? 'Signing In…' : 'Sign In' }}
            </button>

            <!-- Success message -->
            <Transition name="fade-up">
              <div v-if="success" class="success-banner">
                <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-accent)">check_circle</span>
                Login successful! Redirecting to your dashboard…
              </div>
            </Transition>

          </form>

          <!-- Divider -->
          <div class="login-divider">
            <span class="login-divider-line"></span>
            <span class="t-label text-faint" style="font-size:0.65rem;letter-spacing:0.08em;text-transform:uppercase">
              New here?
            </span>
            <span class="login-divider-line"></span>
          </div>

          <!-- Footer link -->
          <div class="login-card-foot">
            <p class="t-body text-muted">
              Don't have an account?
              <a href="#" class="terms-link" style="font-weight:700;margin-left:4px" @click.prevent="$emit('go-register')">
                Create Account
              </a>
            </p>
          </div>

        </div>
      </section>
    </main>

    <!-- ── Footer ─────────────────────────────────────────────── -->
    <footer class="login-footer">
      <div class="login-footer-inner">
        <div>
          <div class="t-body" style="font-weight:700;color:var(--col-primary)">FinanceBuddy</div>
          <div class="t-label text-faint" style="margin-top:2px">© 2026 FinanceBuddy Financial. All rights reserved.</div>
        </div>
        <div class="footer-links">
          <a href="#" class="footer-link" @click.prevent>Privacy Policy</a>
          <a href="#" class="footer-link" @click.prevent>Terms of Service</a>
          <a href="#" class="footer-link" @click.prevent>Security</a>
          <a href="#" class="footer-link" @click.prevent>Contact</a>
        </div>
      </div>
    </footer>

  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['go-register', 'logged-in'])

// ── Form state ────────────────────────────────────────────────────
const form = ref({ username: '', password: '' })
const errors     = ref({})
const showPassword = ref(false)
const rememberMe   = ref(false)
const loading  = ref(false)
const success  = ref(false)
const apiError = ref('')

// ── Clear API error on input ──────────────────────────────────────
function clearApiError() {
  apiError.value = ''
}

// ── Validation ────────────────────────────────────────────────────
function validateField(field) {
  errors.value[field] = ''
  const f = form.value

  if (field === 'username') {
    if (!f.username.trim()) errors.value.username = 'Username is required'
  }
  if (field === 'password') {
    if (!f.password)        errors.value.password = 'Password is required'
  }
}

function validateAll() {
  ['username', 'password'].forEach(validateField)
  return !Object.values(errors.value).some(Boolean)
}

// ── Submit ────────────────────────────────────────────────────────
async function handleSubmit() {
  if (!validateAll()) return
  loading.value = true
  apiError.value = ''

  try {
    const res = await fetch('http://localhost:8000/api/finance-buddy/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.value.username,
        password: form.value.password,
      }),
    })

    const data = await res.json()

    if (res.ok) {
      // Store tokens
      localStorage.setItem('access_token', data.tokens.access)
      localStorage.setItem('refresh_token', data.tokens.refresh)
      if (data.user) {
        localStorage.setItem('user', JSON.stringify(data.user))
      }

      success.value = true
      loading.value = false

      // Navigate to dashboard after brief delay
      setTimeout(() => {
        emit('logged-in', data.user)
      }, 1200)
    } else {
      loading.value = false
      let errMsg = 'Invalid credentials. Please try again.'
      if (data.error) {
        errMsg = data.error
      } else if (data && typeof data === 'object') {
        errMsg = Object.entries(data)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : val}`)
          .join('; ')
      }
      apiError.value = errMsg
    }
  } catch (err) {
    loading.value = false
    apiError.value = 'Unable to connect to server. Please try again later.'
  }
}
</script>

<style scoped>
/* ── Shell ───────────────────────────────────────────────────── */
.login-root {
  min-height: 100vh;
  display: flex; flex-direction: column;
  background: var(--col-surface);
}

/* ── Header ─────────────────────────────────────────────────── */
.login-header {
  position: sticky; top: 0; z-index: 40;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--col-border);
}
.login-header-inner {
  max-width: 1320px; margin: 0 auto;
  padding: 10px 2rem;
  display: flex; justify-content: space-between; align-items: center;
}
.brand { display: flex; align-items: center; }
.login-logo { height: 44px; width: auto; object-fit: contain; }

/* ── Main ───────────────────────────────────────────────────── */
.login-main {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  padding: 3rem 1.5rem;
  position: relative; overflow: hidden;
}

/* Mesh gradient bg */
.login-bg {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-color: #f7f9fb;
  background-image:
    radial-gradient(at 0% 0%,   hsla(160,78%,90%,1) 0, transparent 50%),
    radial-gradient(at 100% 0%, hsla(210,70%,90%,1) 0, transparent 50%),
    radial-gradient(at 80% 100%, hsla(280,60%,92%,0.6) 0, transparent 40%);
}

/* Floating decorative shapes */
.floating-shape {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  opacity: 0.12;
  filter: blur(1px);
}
.shape-1 {
  width: 300px; height: 300px;
  background: linear-gradient(135deg, var(--col-primary), hsla(210,70%,60%,1));
  top: -80px; right: -60px;
  animation: float-1 8s ease-in-out infinite;
}
.shape-2 {
  width: 200px; height: 200px;
  background: linear-gradient(135deg, hsla(160,78%,50%,1), var(--col-accent));
  bottom: 10%; left: -40px;
  animation: float-2 10s ease-in-out infinite;
}
.shape-3 {
  width: 140px; height: 140px;
  background: linear-gradient(135deg, hsla(280,60%,60%,1), hsla(320,60%,65%,1));
  top: 50%; right: 15%;
  animation: float-3 7s ease-in-out infinite;
}

@keyframes float-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(-20px, 30px) scale(1.05); }
}
@keyframes float-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(25px, -20px) scale(1.08); }
}
@keyframes float-3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(-15px, 15px) scale(0.95); }
}

/* ── Card ───────────────────────────────────────────────────── */
.login-card-wrap { width: 100%; max-width: 448px; position: relative; z-index: 1; }
.login-card {
  background: #fff;
  border: 1px solid var(--col-border);
  border-radius: var(--r-xl);
  padding: 2.5rem 2rem;
  box-shadow: 0 10px 40px -10px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.08);
  animation: card-enter 0.5s var(--ease-out) both;
}
@keyframes card-enter {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

/* Lock icon */
.login-icon-wrap {
  display: flex; justify-content: center; margin-bottom: 1.25rem;
}
.login-icon-ring {
  width: 56px; height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--col-primary), hsla(210,50%,35%,1));
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 20px -4px rgba(19,27,46,0.25);
  animation: icon-pulse 2.5s ease-in-out infinite;
}
@keyframes icon-pulse {
  0%, 100% { box-shadow: 0 4px 20px -4px rgba(19,27,46,0.25); }
  50%      { box-shadow: 0 4px 28px -2px rgba(19,27,46,0.35); }
}
.login-icon-glyph {
  font-size: 26px; color: #fff;
}

.login-card-head { margin-bottom: 1.75rem; text-align: center; }

/* ── Error banner ─────────────────────────────────────────── */
.error-banner {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  background: var(--col-error-bg);
  border: 1px solid var(--col-error-border);
  border-radius: var(--r-md);
  font-size: 0.875rem; font-weight: 600;
  color: var(--col-error);
  margin-bottom: 1rem;
}

/* ── Form ───────────────────────────────────────────────────── */
.login-form { display: flex; flex-direction: column; gap: 1.125rem; }

.field-group { display: flex; flex-direction: column; gap: 5px; }

.input-wrap { position: relative; }
.login-input {
  width: 100%; padding: 11px 42px 11px 14px;
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
  font-family: inherit; font-size: 0.875rem;
  color: var(--col-text-primary);
  background: #fff;
  outline: none;
  transition: border-color var(--dur-fast), box-shadow var(--dur-fast);
}
.login-input:focus {
  border-color: var(--col-primary);
  box-shadow: 0 0 0 3px rgba(19,27,46,0.08);
}
.login-input.input-error { border-color: var(--col-error); }
.login-input.input-error:focus { box-shadow: 0 0 0 3px rgba(192,57,43,0.1); }
.login-input::placeholder { color: var(--col-text-faint); }

.input-icon {
  position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%);
  font-size: 20px; color: var(--col-text-faint);
  pointer-events: none;
  transition: color var(--dur-fast);
}
.login-input:focus ~ .input-icon { color: var(--col-primary); }

.field-error {
  font-size: 0.6875rem; font-weight: 600;
  color: var(--col-error); letter-spacing: 0.01em;
}

/* Password label row */
.password-label-row {
  display: flex; justify-content: space-between; align-items: center;
}
.show-btn {
  font-size: 0.6rem; font-weight: 700; letter-spacing: 0.08em;
  color: var(--col-primary); background: none; border: none;
  cursor: pointer; text-decoration: underline; text-underline-offset: 2px;
  font-family: inherit;
}

/* Remember / Forgot row */
.login-options-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 2px 0;
}
.remember-label {
  display: flex; align-items: center; gap: 8px; cursor: pointer;
}
.remember-check {
  width: 15px; height: 15px;
  border: 1.5px solid var(--col-border); border-radius: 4px;
  accent-color: var(--col-primary); cursor: pointer; flex-shrink: 0;
}
.forgot-link {
  font-size: 0.75rem; font-weight: 600;
  color: var(--col-primary);
  text-decoration: underline; text-underline-offset: 2px;
  text-decoration-color: rgba(19,27,46,0.25);
  transition: text-decoration-color var(--dur-fast);
}
.forgot-link:hover { text-decoration-color: var(--col-primary); }

.terms-link {
  color: var(--col-primary); font-weight: 600;
  text-decoration: underline; text-underline-offset: 2px;
  text-decoration-color: rgba(19,27,46,0.25);
}
.terms-link:hover { text-decoration-color: var(--col-primary); }

/* Submit button */
.btn-submit {
  width: 100%; padding: 14px;
  background: var(--col-primary); color: #fff;
  border: none; border-radius: var(--r-md);
  font-family: inherit; font-size: 1rem; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 4px;
  transition: opacity var(--dur-fast), transform var(--dur-fast), box-shadow var(--dur-fast);
}
.btn-submit:hover   { opacity: 0.9; box-shadow: 0 4px 16px -4px rgba(19,27,46,0.3); }
.btn-submit:active  { transform: scale(0.98); }
.btn-submit:disabled { opacity: 0.65; cursor: not-allowed; }

/* Spinner */
.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Success banner */
.success-banner {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  background: var(--col-accent-light);
  border: 1px solid rgba(0,108,73,0.2);
  border-radius: var(--r-md);
  font-size: 0.875rem; font-weight: 600; color: var(--col-accent);
}

/* ── Divider ──────────────────────────────────────────────── */
.login-divider {
  display: flex; align-items: center; gap: 12px;
  margin-top: 1.75rem; margin-bottom: 0.25rem;
}
.login-divider-line {
  flex: 1; height: 1px;
  background: var(--col-border);
}

/* Card footer */
.login-card-foot {
  margin-top: 1rem;
  text-align: center;
}

/* ── Page footer ────────────────────────────────────────────── */
.login-footer {
  background: var(--col-surface-low);
  border-top: 1px solid var(--col-border);
}
.login-footer-inner {
  max-width: 1320px; margin: 0 auto;
  padding: 2rem;
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 1rem;
}
.footer-links { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.footer-link {
  font-size: 0.6875rem; font-weight: 600;
  letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--col-text-muted); text-decoration: none;
  transition: color var(--dur-fast);
}
.footer-link:hover { color: var(--col-accent); }

/* Transition */
.fade-up-enter-active, .fade-up-leave-active { transition: all 0.35s var(--ease-out); }
.fade-up-enter-from, .fade-up-leave-to { opacity: 0; transform: translateY(6px); }
</style>
