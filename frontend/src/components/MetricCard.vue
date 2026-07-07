<template>
  <div :class="['metric-card card fade-up', `variant-${variant}`]"
       :style="{ animationDelay: `${delay}ms` }">

    <!-- Top row -->
    <div class="metric-top">
      <div :class="['metric-icon-wrap', `icon-${variant}`]">
        <span :class="['material-symbols-outlined icon-filled icon-md', `icon-color-${variant}`]">
          {{ icon }}
        </span>
      </div>
      <span :class="['badge', deltaBadgeClass]">
        <span class="material-symbols-outlined" style="font-size:10px">
          {{ deltaPositive ? 'arrow_upward' : 'arrow_downward' }}
        </span>
        {{ delta }}
      </span>
    </div>

    <!-- Value -->
    <div class="metric-body">
      <div class="t-label text-muted" style="margin-bottom:4px">{{ label }}</div>
      <div :class="['t-metric count-up', valueClass]">{{ value }}</div>
    </div>

    <!-- Bottom bar (accent stripe) -->
    <div :class="['metric-stripe', `stripe-${variant}`]"></div>

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label:   { type: String, required: true },
  value:   { type: String, required: true },
  icon:    { type: String, required: true },
  delta:   { type: String, default: '' },
  variant: { type: String, default: 'income' }, // income | expense | savings | negative
  delay:   { type: Number, default: 0 },
})

const deltaPositive = computed(() => !props.delta.startsWith('-') && props.variant !== 'expense')

const deltaBadgeClass = computed(() => {
  if (props.variant === 'negative') return 'badge badge-error'
  if (props.variant === 'expense')  return 'badge badge-error'
  return 'badge badge-success'
})

const valueClass = computed(() => {
  if (props.variant === 'negative') return 'text-error'
  return 'text-primary'
})
</script>

<style scoped>
.metric-card {
  position: relative; overflow: hidden;
  padding-bottom: var(--space-md);
  display: flex; flex-direction: column; gap: var(--space-md);
}

.metric-top {
  display: flex; justify-content: space-between; align-items: flex-start;
}

.metric-icon-wrap {
  width: 40px; height: 40px; border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center;
}
.icon-income    { background: var(--col-accent-light); }
.icon-expense   { background: var(--col-error-bg); }
.icon-savings   { background: var(--col-blue-light); }
.icon-negative  { background: var(--col-error-bg); }

.icon-color-income   { color: var(--col-accent); }
.icon-color-expense  { color: var(--col-error); }
.icon-color-savings  { color: var(--col-blue); }
.icon-color-negative { color: var(--col-error); }

/* Accent stripe at bottom left */
.metric-stripe {
  position: absolute; left: 0; bottom: 0;
  width: 3px; height: 40%;
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
}
.stripe-income   { background: var(--col-accent); }
.stripe-expense  { background: var(--col-error); }
.stripe-savings  { background: var(--col-blue); }
.stripe-negative { background: var(--col-error); }

/* Critical state */
.variant-negative {
  border-color: var(--col-error-border);
}
</style>
