<script setup>
// Importancia de variables (una sola serie, en %).
import { computed } from 'vue'
import { useWidth } from '../lib/useWidth.js'

const props = defineProps({ rows: { type: Array, required: true } })  // [{ label, v (0..1), tip }]
const { el, width } = useWidth()

const ML = 74, MR = 56, RH = 34
const g = computed(() => {
  const W = width.value, iw = W - ML - MR
  const max = Math.max(...props.rows.map(r => r.v), 1e-9)
  return { W, H: RH * props.rows.length, iw, w: v => Math.max(v > 0 ? 4 : 0, (v / max) * iw) }
})
</script>

<template>
  <div ref="el">
    <svg :width="g.W" :height="g.H" :viewBox="`0 0 ${g.W} ${g.H}`" role="img" aria-label="Importancia de variables">
      <g v-for="(r, i) in rows" :key="r.label" :data-tip="r.tip || `<b>${r.label}</b><br>${(r.v * 100).toFixed(1)}% de la importancia`">
        <rect x="0" :y="i * RH" :width="g.W" :height="RH" fill="transparent" />
        <text x="0" :y="i * RH + 21" class="mono ink" style="font-weight:600">{{ r.label }}</text>
        <rect :x="ML" :y="i * RH + 9" :width="g.iw" height="16" rx="4" fill="var(--surface-2)" />
        <rect :x="ML" :y="i * RH + 9" :width="g.w(r.v)" height="16" rx="4" fill="var(--accent)" />
        <text :x="ML + g.iw + 8" :y="i * RH + 21" class="mono ink">{{ (r.v * 100).toFixed(1) }}%</text>
      </g>
    </svg>
  </div>
</template>
