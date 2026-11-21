<script setup>
// Distribución de la probabilidad de anomalía en test, una fila por clase (small multiples),
// eje y logarítmico compartido y línea del umbral.
import { computed } from 'vue'
import { D, BINS, N_NORM, A_TEST } from '../store.js'
import { useWidth } from '../lib/useWidth.js'
import { fmt } from '../lib/format.js'

const props = defineProps({ cid: { type: String, required: true }, t: { type: Number, required: true } })
const { el, width } = useWidth()

const SHOWN = 50, ML = 44, MR = 10, PH = 108, GAP = 40, MT = 22, MB = 34
const TICK = ['1', '10', '100', '1k', '10k', '100k', '1M']

const g = computed(() => {
  const W = width.value, iw = W - ML - MR, bw = iw / SHOWN, k = BINS / SHOWN
  const agg = h => Array.from({ length: SHOWN }, (_, i) => h.slice(i * k, (i + 1) * k).reduce((a, b) => a + b, 0))
  const h = D.configs[props.cid].hist
  const N = agg(h.n), A = agg(h.a)
  const lmin = Math.log10(0.6), lmax = Math.log10(Math.max(...N, ...A)) + 0.15
  const y = (c, top) => top + PH - (c > 0 ? ((Math.log10(c) - lmin) / (lmax - lmin)) * PH : 0)
  const step = Math.floor(lmax) > 4 ? 2 : 1
  const panels = [
    { name: 'Normales', n: N_NORM, data: N, top: MT, color: 'var(--normal)', on: 'marcados (falsas alarmas)', off: 'no marcados' },
    { name: 'Anomalías', n: A_TEST, data: A, top: MT + PH + GAP, color: 'var(--anom)', on: 'marcadas (atrapadas)', off: 'no detectadas' },
  ].map(p => ({
    ...p,
    ticks: Array.from({ length: Math.floor(lmax / step) + 1 }, (_, i) => i * step).map(e => ({ y: y(10 ** e, p.top), label: TICK[e] })),
    bars: p.data.map((c, i) => {
      const flagged = i / SHOWN >= props.t - 1e-9
      return {
        i, c, flagged, x: ML + i * bw,
        y: y(c, p.top), h: p.top + PH - y(c, p.top),
        tip: `<b>${p.name}</b> · prob. ${(i / SHOWN).toFixed(2)}–${((i + 1) / SHOWN).toFixed(2)}<br>${fmt(c)} bloques · ${flagged ? p.on : p.off}`,
      }
    }),
  }))
  return { W, H: MT + PH * 2 + GAP + MB, iw, bw, panels, bot: MT + PH * 2 + GAP, tx: ML + props.t * iw }
})
</script>

<template>
  <div ref="el">
    <svg :width="g.W" :height="g.H" :viewBox="`0 0 ${g.W} ${g.H}`" role="img" aria-label="Distribución de probabilidades por clase">
      <g v-for="p in g.panels" :key="p.name">
        <text :x="ML" :y="p.top - 9" class="ink" style="font-weight:600">{{ p.name }}
          <tspan class="mono muted" style="font-weight:400">{{ fmt(p.n) }} bloques</tspan></text>
        <g v-for="tk in p.ticks" :key="tk.label">
          <line :x1="ML" :x2="g.W - MR" :y1="tk.y" :y2="tk.y" stroke="var(--grid)" />
          <text :x="ML - 8" :y="tk.y + 4" text-anchor="end" class="mono muted">{{ tk.label }}</text>
        </g>
        <line :x1="ML" :x2="g.W - MR" :y1="p.top + PH" :y2="p.top + PH" stroke="var(--axis)" />
        <template v-for="b in p.bars" :key="b.i">
          <rect v-if="b.c > 0" :x="b.x + 1" :y="b.y" :width="Math.max(1, g.bw - 2)" :height="b.h"
                :rx="Math.min(2, g.bw / 4)" :fill="p.color" :opacity="b.flagged ? 1 : 0.32" />
          <rect :x="b.x" :y="p.top" :width="g.bw" :height="PH" fill="transparent" :data-tip="b.tip" />
        </template>
      </g>
      <text v-for="v in [0, 0.25, 0.5, 0.75, 1]" :key="v" :x="ML + v * g.iw" :y="g.bot + 16" text-anchor="middle" class="mono muted">{{ v }}</text>
      <text :x="ML + g.iw / 2" :y="g.bot + 31" text-anchor="middle" class="muted">probabilidad de anomalía según el modelo</text>
      <line :x1="g.tx" :x2="g.tx" :y1="MT - 4" :y2="g.bot" stroke="var(--accent)" stroke-width="2" stroke-dasharray="4 3" />
      <text :x="g.tx + (t < 0.7 ? 7 : -7)" :y="MT + PH + 15" :text-anchor="t < 0.7 ? 'start' : 'end'" class="mono"
            style="fill:var(--accent-ink);font-weight:600">umbral {{ t.toFixed(3) }}{{ t < 0.7 && g.W > 480 ? ' → marcados' : '' }}</text>
    </svg>
    <div class="note">Eje vertical en escala logarítmica: en test hay 33 veces más bloques normales que anómalos.</div>
  </div>
</template>
