<script setup>
// Barras horizontales agrupadas: por cada evento, valor en bloques normales y anómalos.
import { computed } from 'vue'
import { useWidth } from '../lib/useWidth.js'

const props = defineProps({ rows: { type: Array, required: true } })  // [{ label, n, a }]
const { el, width } = useWidth()

const ML = 44, MR = 44, RH = 38, BH = 11
const g = computed(() => {
  const W = width.value, iw = W - ML - MR
  const max = Math.max(...props.rows.flatMap(r => [r.n, r.a])) * 1.05
  const x = v => (v / max) * iw
  const ticks = Array.from({ length: Math.floor(max) + 1 }, (_, i) => i)
  return { W, H: RH * props.rows.length + 22, iw, x, ticks }
})
</script>

<template>
  <div ref="el">
    <svg :width="g.W" :height="g.H" :viewBox="`0 0 ${g.W} ${g.H}`" role="img" aria-label="Frecuencia promedio por clase">
      <g v-for="v in g.ticks" :key="v">
        <line :x1="ML + g.x(v)" :x2="ML + g.x(v)" y1="0" :y2="RH * rows.length" stroke="var(--grid)" />
        <text :x="ML + g.x(v)" :y="RH * rows.length + 16" text-anchor="middle" class="mono muted">{{ v }}</text>
      </g>
      <g v-for="(r, i) in rows" :key="r.label">
        <text x="0" :y="i * RH + (RH - BH * 2 - 2) / 2 + BH + 5" class="mono ink" style="font-weight:600">{{ r.label }}</text>
        <g v-for="([v, color, name], j) in [[r.n, 'var(--normal)', 'Normal'], [r.a, 'var(--anom)', 'Anomalía']]" :key="j"
           :data-tip="`<b>${r.label}</b> · ${name}<br>promedio ${v.toFixed(3)} por bloque`">
          <rect :x="ML" :y="i * RH + (RH - BH * 2 - 2) / 2 + j * (BH + 2) - 1" :width="g.iw + MR" :height="BH + 2" fill="transparent" />
          <rect :x="ML" :y="i * RH + (RH - BH * 2 - 2) / 2 + j * (BH + 2)" :width="Math.max(v > 0 ? 3 : 0, g.x(v))" :height="BH" rx="3" :fill="color" />
          <text :x="ML + Math.max(v > 0 ? 3 : 0, g.x(v)) + 6" :y="i * RH + (RH - BH * 2 - 2) / 2 + j * (BH + 2) + BH - 1.5" class="mono" style="font-size:10.5px">{{ v.toFixed(2) }}</text>
        </g>
      </g>
    </svg>
  </div>
</template>
