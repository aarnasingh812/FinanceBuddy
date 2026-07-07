<template>
  <div class="register-root">

    <!-- ── Header ─────────────────────────────────────────────── -->
    <header class="reg-header">
      <div class="reg-header-inner">
        <div class="brand">
          <img src="/logo.png" alt="FinanceBuddy" class="reg-logo" />
        </div>
        <a class="btn btn-ghost" style="font-size:0.8125rem;font-weight:700" @click.prevent="$emit('go-login')">
          Sign In
        </a>
      </div>
    </header>

    <!-- ── Main ───────────────────────────────────────────────── -->
    <main class="reg-main">
      <!-- Mesh gradient background -->
      <div class="reg-bg" aria-hidden="true"></div>

      <!-- Floating shapes -->
      <div class="floating-shape shape-1" aria-hidden="true"></div>
      <div class="floating-shape shape-2" aria-hidden="true"></div>
      <div class="floating-shape shape-3" aria-hidden="true"></div>

      <!-- Card -->
      <section class="reg-card-wrap">
        <div class="reg-card">

          <!-- Icon -->
          <div class="reg-icon-wrap">
            <div class="reg-icon-ring">
              <span class="material-symbols-outlined reg-icon-glyph">person_add</span>
            </div>
          </div>

          <!-- Heading -->
          <div class="reg-card-head">
            <h1 class="t-display" style="font-size:2rem;letter-spacing:-0.03em;color:var(--col-primary)">
              Create Account
            </h1>
            <p class="t-body text-muted" style="margin-top:4px">
              Join FinanceBuddy to start your financial journey
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
          <form class="reg-form" @submit.prevent="handleSubmit" novalidate>

            <!-- Username -->
            <div class="field-group">
              <label class="t-label text-muted" for="username">USERNAME</label>
              <div class="input-wrap">
                <input
                  id="username"
                  v-model="form.username"
                  type="text"
                  class="reg-input"
                  :class="{ 'input-error': errors.username }"
                  placeholder="Enter your username"
                  autocomplete="username"
                  @blur="validateField('username')"
                />
                <span class="material-symbols-outlined input-icon">person</span>
              </div>
              <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
            </div>

            <!-- Email -->
            <div class="field-group">
              <label class="t-label text-muted" for="email">EMAIL ADDRESS</label>
              <div class="input-wrap">
                <input
                  id="email"
                  v-model="form.email"
                  type="email"
                  class="reg-input"
                  :class="{ 'input-error': errors.email }"
                  placeholder="name@example.com"
                  autocomplete="email"
                  @blur="validateField('email')"
                />
                <span class="material-symbols-outlined input-icon">mail</span>
              </div>
              <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
            </div>

            <!-- Password -->
            <div class="field-group">
              <div class="password-label-row">
                <label class="t-label text-muted" for="password">PASSWORD</label>
                <button type="button" class="show-btn" @click="showPassword = !showPassword">
                  {{ showPassword ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
              <div class="input-wrap">
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="reg-input"
                  :class="{ 'input-error': errors.password }"
                  placeholder="••••••••"
                  autocomplete="new-password"
                  @blur="validateField('password')"
                />
                <span class="material-symbols-outlined input-icon">lock</span>
              </div>

              <!-- Strength meter -->
              <div class="strength-wrap">
                <div class="strength-track">
                  <div
                    class="strength-fill"
                    :style="{ width: strength.pct + '%', background: strength.color }"
                  ></div>
                </div>
                <div class="strength-segments">
                  <div v-for="i in 4" :key="i"
                       class="strength-seg"
                       :style="{ background: i * 25 <= strength.pct ? strength.color : 'var(--col-surface-high)' }">
                  </div>
                </div>
                <span class="t-label" :style="{ color: strength.color, fontWeight:700, fontSize:'0.6rem', textTransform:'uppercase', letterSpacing:'.06em' }">
                  Security: {{ strength.label }}
                </span>
              </div>

              <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
            </div>

            <!-- Confirm Password -->
            <div class="field-group">
              <label class="t-label text-muted" for="confirm">CONFIRM PASSWORD</label>
              <div class="input-wrap">
                <input
                  id="confirm"
                  v-model="form.confirm"
                  :type="showPassword ? 'text' : 'password'"
                  class="reg-input"
                  :class="{ 'input-error': errors.confirm }"
                  placeholder="••••••••"
                  autocomplete="new-password"
                  @blur="validateField('confirm')"
                />
                <span class="material-symbols-outlined input-icon"
                      :style="{ color: form.confirm && form.confirm === form.password ? 'var(--col-accent)' : '' }">
                  {{ form.confirm && form.confirm === form.password ? 'check_circle' : 'lock' }}
                </span>
              </div>
              <span v-if="errors.confirm" class="field-error">{{ errors.confirm }}</span>
            </div>

            <!-- Terms -->
            <div class="terms-row">
              <input
                id="terms"
                v-model="form.terms"
                type="checkbox"
                class="terms-check"
              />
              <label for="terms" class="t-label" style="color:var(--col-text-secondary);font-size:0.75rem;line-height:1.5;cursor:pointer">
                I agree to the
                <a href="#" class="terms-link" @click.prevent>Terms of Service</a>
                and
                <a href="#" class="terms-link" @click.prevent>Privacy Policy</a>
              </label>
            </div>
            <span v-if="errors.terms" class="field-error">{{ errors.terms }}</span>

            <!-- Submit -->
            <button
              type="submit"
              class="btn-submit"
              :class="{ 'btn-loading': loading }"
              :disabled="loading"
            >
              <span v-if="loading" class="spinner"></span>
              <span v-else class="material-symbols-outlined icon-sm icon-filled">person_add</span>
              {{ loading ? 'Creating Account…' : 'Create Account' }}
            </button>

            <!-- Success message -->
            <Transition name="fade-up">
              <div v-if="success" class="success-banner">
                <span class="material-symbols-outlined icon-sm icon-filled" style="color:var(--col-accent)">check_circle</span>
                Account created! Redirecting to your dashboard…
              </div>
            </Transition>

          </form>

          <!-- Divider -->
          <div class="reg-divider">
            <span class="reg-divider-line"></span>
            <span class="t-label text-faint" style="font-size:0.65rem;letter-spacing:0.08em;text-transform:uppercase">
              Already a member?
            </span>
            <span class="reg-divider-line"></span>
          </div>

          <!-- Footer link -->
          <div class="reg-card-foot">
            <p class="t-body text-muted">
              Already have an account?
              <a href="#" class="terms-link" style="font-weight:700;margin-left:4px" @click.prevent="$emit('go-login')">
                Sign In
              </a>
            </p>
          </div>

        </div>
      </section>
    </main>

    <!-- ── Footer ─────────────────────────────────────────────── -->
    <footer class="reg-footer">
      <div class="reg-footer-inner">
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
import { ref, computed } from 'vue'

const emit = defineEmits(['go-login', 'registered'])

// ── Form state ────────────────────────────────────────────────────
const form = ref({ username: '', email: '', password: '', confirm: '', terms: false })
const errors   = ref({})
const showPassword = ref(false)
const loading  = ref(false)
const success  = ref(false)
const apiError = ref('')

// ── Password strength ─────────────────────────────────────────────
const strength = computed(() => {
  const v = form.value.password
  let pct = 0
  if (v.length > 5)           pct += 25
  if (/[A-Z]/.test(v))        pct += 25
  if (/[0-9]/.test(v))        pct += 25
  if (/[^a-zA-Z0-9]/.test(v)) pct += 25

  if (pct === 0)   return { pct: 0,   label: 'None',     color: 'var(--col-text-faint)' }
  if (pct <= 25)   return { pct,       label: 'Weak',     color: 'var(--col-error)' }
  if (pct <= 50)   return { pct,       label: 'Fair',     color: 'var(--col-warn)' }
  if (pct <= 75)   return { pct,       label: 'Moderate', color: '#3980f4' }
  return               { pct: 100,   label: 'Strong',   color: 'var(--col-accent)' }
})

// ── Validation ────────────────────────────────────────────────────
function validateField(field) {
  errors.value[field] = ''
  const f = form.value

  if (field === 'username') {
    if (!f.username.trim())         errors.value.username = 'Username is required'
    else if (f.username.length < 3) errors.value.username = 'Must be at least 3 characters'
  }
  if (field === 'email') {
    if (!f.email.trim())            errors.value.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email))
                                    errors.value.email = 'Enter a valid email address'
  }
  if (field === 'password') {
    if (!f.password)                errors.value.password = 'Password is required'
    else if (f.password.length < 6) errors.value.password = 'Must be at least 6 characters'
  }
  if (field === 'confirm') {
    if (!f.confirm)                 errors.value.confirm = 'Please confirm your password'
    else if (f.confirm !== f.password) errors.value.confirm = 'Passwords do not match'
  }
  if (field === 'terms') {
    if (!f.terms)                   errors.value.terms = 'You must agree to the Terms of Service'
  }
}

function validateAll() {
  ['username', 'email', 'password', 'confirm', 'terms'].forEach(validateField)
  return !Object.values(errors.value).some(Boolean)
}

// ── Submit ────────────────────────────────────────────────────────
async function handleSubmit() {
  if (!validateAll()) return
  loading.value = true
  apiError.value = ''

  try {
    const res = await fetch('http://localhost:8000/api/finance-buddy/register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.value.username,
        email: form.value.email,
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
        emit('registered', data.user)
      }, 1200)
    } else {
      loading.value = false
      let errMsg = 'Failed to register account. Please try again.'
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
.register-root {
  min-height: 100vh;
  display: flex; flex-direction: column;
  background: var(--col-surface);
}

/* ── Header ─────────────────────────────────────────────────── */
.reg-header {
  position: sticky; top: 0; z-index: 40;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--col-border);
}
.reg-header-inner {
  max-width: 1320px; margin: 0 auto;
  padding: 10px 2rem;
  display: flex; justify-content: space-between; align-items: center;
}
.brand { display: flex; align-items: center; }
.reg-logo { height: 44px; width: auto; object-fit: contain; }

/* ── Main ───────────────────────────────────────────────────── */
.reg-main {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  padding: 3rem 1.5rem;
  position: relative; overflow: hidden;
}

/* Mesh gradient bg */
.reg-bg {
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
.reg-card-wrap { width: 100%; max-width: 448px; position: relative; z-index: 1; }
.reg-card {
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

/* Icon ring */
.reg-icon-wrap {
  display: flex; justify-content: center; margin-bottom: 1.25rem;
}
.reg-icon-ring {
  width: 56px; height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--col-accent), hsla(160,50%,35%,1));
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 20px -4px rgba(0,108,73,0.3);
  animation: icon-pulse 2.5s ease-in-out infinite;
}
@keyframes icon-pulse {
  0%, 100% { box-shadow: 0 4px 20px -4px rgba(0,108,73,0.3); }
  50%      { box-shadow: 0 4px 28px -2px rgba(0,108,73,0.45); }
}
.reg-icon-glyph {
  font-size: 26px; color: #fff;
}

.reg-card-head { margin-bottom: 1.75rem; text-align: center; }

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
.reg-form { display: flex; flex-direction: column; gap: 1.125rem; }

.field-group { display: flex; flex-direction: column; gap: 5px; }

.input-wrap { position: relative; }
.reg-input {
  width: 100%; padding: 11px 42px 11px 14px;
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
  font-family: inherit; font-size: 0.875rem;
  color: var(--col-text-primary);
  background: #fff;
  outline: none;
  transition: border-color var(--dur-fast), box-shadow var(--dur-fast);
}
.reg-input:focus {
  border-color: var(--col-primary);
  box-shadow: 0 0 0 3px rgba(19,27,46,0.08);
}
.reg-input.input-error { border-color: var(--col-error); }
.reg-input.input-error:focus { box-shadow: 0 0 0 3px rgba(192,57,43,0.1); }
.reg-input::placeholder { color: var(--col-text-faint); }

.input-icon {
  position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%);
  font-size: 20px; color: var(--col-text-faint);
  pointer-events: none;
  transition: color var(--dur-fast);
}
.reg-input:focus ~ .input-icon { color: var(--col-primary); }

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

/* Strength meter */
.strength-wrap { display: flex; flex-direction: column; gap: 4px; padding-top: 6px; }
.strength-track {
  width: 100%; height: 4px;
  background: var(--col-surface-high); border-radius: 2px;
  overflow: hidden;
}
.strength-fill {
  height: 100%; border-radius: 2px;
  transition: width 0.3s var(--ease-out), background 0.3s;
}
.strength-segments {
  display: flex; gap: 3px;
}
.strength-seg {
  flex: 1; height: 3px; border-radius: 2px;
  transition: background 0.3s;
}

/* Terms */
.terms-row {
  display: flex; align-items: flex-start; gap: 10px; padding: 4px 0;
}
.terms-check {
  width: 16px; height: 16px; margin-top: 1px;
  border: 1.5px solid var(--col-border); border-radius: 4px;
  accent-color: var(--col-primary); cursor: pointer; flex-shrink: 0;
}
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
  transition: opacity var(--dur-fast), transform var(--dur-fast);
}
.btn-submit:hover   { opacity: 0.9; }
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

/* Divider */
.reg-divider {
  display: flex; align-items: center; gap: 12px;
  margin-top: 1.75rem; margin-bottom: 0.25rem;
}
.reg-divider-line {
  flex: 1; height: 1px;
  background: var(--col-border);
}

/* Card footer */
.reg-card-foot {
  margin-top: 1rem;
  text-align: center;
}

/* ── Page footer ────────────────────────────────────────────── */
.reg-footer {
  background: var(--col-surface-low);
  border-top: 1px solid var(--col-border);
}
.reg-footer-inner {
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
