<script setup>
// Gráfico de puntos: una fila por modelo, una métrica en el eje x (que no empieza en 0).
import { computed } from 'vue'
import { useWidth } from '../lib/useWidth.js'
import { f4 } from '../lib/format.js'

const props = defineProps({
  rows: { type: Array, required: true },   // [{ id, name, short, v, sel }]
  label: { type: String, required: true },
})
defineEmits(['select'])
const { el, width } = useWidth()

const RH = 40, MT = 4
const g = computed(() => {
  const W = width.value
  const vals = props.rows.map(r => r.v)
  const lo = Math.min(0.9, Math.floor((Math.min(...vals) - 0.01) * 20) / 20)
  const ml = Math.min(160, W * 0.36), mr = 58, iw = W - ml - mr
  const x = v => ml + ((v - lo) / (1 - lo)) * iw
  const ticks = []
  for (let t = lo; t <= 1 + 1e-9; t += lo < 0.85 ? 0.05 : 0.025) ticks.push(+t.toFixed(3))
  return { W, H: MT + RH * props.rows.length + 26, ml, mr, x, lo, ticks, narrow: W < 420 }
})
</script>

<template>
  <div ref="el">
    <svg :width="g.W" :height="g.H" :viewBox="`0 0 ${g.W} ${g.H}`" role="img" :aria-label="`${label} por modelo`">
      <g v-for="t in g.ticks" :key="t">
        <line :x1="g.x(t)" :x2="g.x(t)" :y1="MT" :y2="MT + RH * rows.length" stroke="var(--grid)" />
        <text :x="g.x(t)" :y="MT + RH * rows.length + 18" text-anchor="middle" class="mono muted">{{ t.toFixed(t * 100 % 5 ? 3 : 2) }}</text>
      </g>
      <g v-for="(r, i) in rows" :key="r.id" style="cursor:pointer" @click="$emit('select', r.id)"
         :data-tip="`<b>${r.name}</b><br>${label}: ${f4(r.v)}`">
        <rect x="0" :y="MT + RH * i + 2" :width="g.W" :height="RH - 4" rx="7"
              :fill="r.sel ? 'var(--accent-soft)' : 'transparent'" />
        <text x="10" :y="MT + RH * i + RH / 2 + 4" class="ink" :style="{ fontSize: '12.5px', fontWeight: r.sel ? 600 : 400 }">
          {{ g.narrow ? r.short : r.name }}</text>
        <circle :cx="g.x(r.v)" :cy="MT + RH * i + RH / 2" :r="r.sel ? 7 : 6" fill="var(--accent)" stroke="var(--surface)" stroke-width="2" />
        <text :x="g.W - g.mr + 12" :y="MT + RH * i + RH / 2 + 4" class="mono ink" :style="{ fontWeight: r.sel ? 600 : 400 }">{{ f4(r.v) }}</text>
      </g>
    </svg>
    <div class="note">Eje desde {{ g.lo.toFixed(2) }} para distinguir diferencias pequeñas.</div>
  </div>
</template>
