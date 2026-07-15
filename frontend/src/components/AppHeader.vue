<template>
  <header class="app-header">
    <div class="header-inner">

      <!-- Brand -->
      <div class="brand">
        <img src="/logo.png" alt="FinanceBuddy" class="brand-logo-img" />
      </div>

      <!-- Nav -->
      <nav class="main-nav">
        <a v-for="item in navItems" :key="item.label"
           href="#"
           :class="['nav-link', { active: activePage === item.label }]"
           @click.prevent="$emit('navigate', item.label)">
          <span class="material-symbols-outlined icon-sm">{{ item.icon }}</span>
          <span class="t-label">{{ item.label }}</span>
        </a>
      </nav>

      <!-- Right actions -->
      <div class="header-actions">
        <!-- User -->
        <div class="user-menu-container">
          <div class="user-chip" @click="showDropdown = !showDropdown">
            <div class="user-info">
              <div class="t-body" style="font-weight:600;line-height:1.2">
                {{ user ? user.username : 'User' }}
              </div>
              <div class="t-label text-faint" style="font-size:0.6rem;text-transform:lowercase">
                {{ user ? user.email : 'Member' }}
              </div>
            </div>
            <div class="avatar">{{ userInitials }}</div>
          </div>

          <!-- Dropdown menu -->
          <Transition name="fade-up">
            <div v-if="showDropdown" class="user-dropdown">
              <div class="dropdown-header">
                <div class="t-body" style="font-weight:700;color:var(--col-primary)">
                  {{ user ? user.username : 'User' }}
                </div>
                <div class="t-label text-faint" style="font-size:0.75rem;margin-top:2px;text-transform:lowercase">
                  {{ user ? user.email : '' }}
                </div>
              </div>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item text-error" @click="handleLogout">
                <span class="material-symbols-outlined icon-sm">logout</span>
                Logout
              </button>
            </div>
          </Transition>
        </div>
      </div>

    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  activePage: { type: String, default: 'Dashboard' },
  user: { type: Object, default: null }
})

const emit = defineEmits(['navigate', 'logout'])

const showDropdown = ref(false)

const userInitials = computed(() => {
  if (!props.user || !props.user.username) return 'U'
  const name = props.user.username.trim()
  if (name.length <= 2) return name.toUpperCase()
  return name.slice(0, 2).toUpperCase()
})

function handleLogout() {
  showDropdown.value = false
  emit('logout')
}

const navItems = [
  { label: 'Dashboard',    icon: 'dashboard'    },
  { label: 'Transactions', icon: 'receipt_long' },
  { label: 'Goals',        icon: 'flag'         },
  { label: 'Insights',     icon: 'insights'     },
]
</script>

<style scoped>
.app-header {
  position: sticky; top: 0; z-index: 40;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--col-border);
}
.header-inner {
  max-width: 1320px; margin: 0 auto;
  height: 68px;
  padding: 0 var(--space-xl);
  display: flex; align-items: center; gap: var(--space-xl);
}

/* Brand */
.brand { display: flex; align-items: center; }
.brand-logo-img {
  height: 46px;
  width: auto;
  max-width: 220px;
  object-fit: contain;
  /* transparent bg — no blend mode needed */
}

/* Nav */
.main-nav {
  display: flex; align-items: center; gap: 2px;
  flex: 1;
}
@media (max-width: 900px) { .main-nav { display: none; } }

.nav-link {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: var(--r-md);
  text-decoration: none;
  color: var(--col-text-muted);
  transition: color var(--dur-fast), background var(--dur-fast);
}
.nav-link:hover {
  background: var(--col-surface-low);
  color: var(--col-text-primary);
}
.nav-link.active {
  background: var(--col-accent-light);
  color: var(--col-accent);
}
.nav-link.active .material-symbols-outlined {
  font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 20;
}

/* Actions */
.header-actions {
  display: flex; align-items: center; gap: var(--space-xs);
  margin-left: auto;
}




/* User chip */
.user-menu-container {
  position: relative;
}
.user-chip {
  display: flex; align-items: center; gap: var(--space-sm);
  padding: 4px 4px 4px 10px;
  border: 1px solid var(--col-border);
  border-radius: var(--r-full);
  cursor: pointer;
  transition: border-color var(--dur-fast);
}
.user-chip:hover { border-color: #c0c3ca; }
.user-info { text-align: right; }
.avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: var(--col-primary);
  color: #fff; font-size: 0.6875rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.user-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 50;
  background: #fff;
  border: 1px solid var(--col-border);
  border-radius: var(--r-md);
  box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 0 1px rgba(0,0,0,0.05);
  min-width: 180px;
  padding: 6px 0;
  animation: dropdown-enter 0.2s ease-out;
}
@keyframes dropdown-enter {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.dropdown-header {
  padding: 10px 16px;
  text-align: left;
}
.dropdown-divider {
  height: 1px;
  background: var(--col-border);
  margin: 4px 0;
}
.dropdown-item {
  width: 100%;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  font-family: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--col-text-secondary);
  cursor: pointer;
  text-align: left;
  transition: background var(--dur-fast), color var(--dur-fast);
}
.dropdown-item:hover {
  background: var(--col-surface-low);
  color: var(--col-primary);
}
.dropdown-item.text-error {
  color: var(--col-error);
}
.dropdown-item.text-error:hover {
  background: var(--col-error-bg);
  color: var(--col-error);
}
</style>
