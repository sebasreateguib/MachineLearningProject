<script setup>
// Curva precisión–recall: el modelo seleccionado resaltado, los demás como contexto.
// Pasar el cursor muestra el umbral de cada punto; clic lo fija.
import { computed, ref } from 'vue'
import { prPoints, metricsAt } from '../lib/metrics.js'
import { useWidth } from '../lib/useWidth.js'
import { show, hide } from '../lib/tooltip.js'
import { f3 } from '../lib/format.js'

const props = defineProps({
  cid: { type: String, required: true },
  others: { type: Array, default: () => [] },   // [{ cid, name }]
  t: { type: Number, required: true },
})
const emit = defineEmits(['pick', 'select'])
const { el, width } = useWidth()

// Ejes ampliados: todos los modelos tienen recall y precisión altos, con ejes desde 0
// las curvas quedarían aplastadas en la esquina. Lo que sale del rango se recorta.
const XLO = 0.95, YLO = 0.85, ML = 46, MR = 14, MT = 10, MB = 42
const XTICKS = [0.95, 0.96, 0.97, 0.98, 0.99, 1], YTICKS = [0.85, 0.9, 0.95, 1]
const hover = ref(null)

const g = computed(() => {
  const W = width.value, H = Math.round(Math.min(330, Math.max(240, W * 0.8)))
  const iw = W - ML - MR, ih = H - MT - MB
  const x = v => ML + ((v - XLO) / (1 - XLO)) * iw
  const y = v => MT + ih - ((v - YLO) / (1 - YLO)) * ih
  const path = pts => 'M' + pts.map(p => `${x(p.R).toFixed(1)},${y(p.P).toFixed(1)}`).join('L')
  const cur = metricsAt(props.cid, props.t)
  return {
    W, H, iw, ih, x, y,
    others: props.others.map(o => ({ ...o, d: path(prPoints(o.cid)) })),
    sel: path(prPoints(props.cid)),
    cur: { x: x(cur.R), y: y(cur.P), inside: cur.R >= XLO && cur.P >= YLO },
  }
})

function onMove(e) {
  const svg = e.currentTarget.ownerSVGElement, r = svg.getBoundingClientRect()
  const mx = ((e.clientX - r.left) * g.value.W) / r.width
  const rec = XLO + ((mx - ML) / g.value.iw) * (1 - XLO)
  const pts = prPoints(props.cid).filter(p => p.R >= XLO && p.P >= YLO)
  if (!pts.length) return
  let best = pts[0]
  for (const p of pts) if (Math.abs(p.R - rec) < Math.abs(best.R - rec)) best = p
  hover.value = { x: g.value.x(best.R), y: g.value.y(best.P), t: best.t }
  show(`<b>Umbral ${best.t.toFixed(3)}</b><br>Recall ${f3(best.R)} · Precisión ${f3(best.P)}<br><span style="opacity:.75">clic para usar este umbral</span>`, e)
}
function onLeave() { hover.value = null; hide() }
</script>

<template>
  <div ref="el">
    <svg :width="g.W" :height="g.H" :viewBox="`0 0 ${g.W} ${g.H}`" role="img" aria-label="Curva precisión-recall">
      <defs><clipPath id="pr-plot"><rect :x="ML" :y="MT - 2" :width="g.iw + 2" :height="g.ih + 2" /></clipPath></defs>
      <g v-for="v in YTICKS" :key="'y' + v">
        <line :x1="ML" :x2="g.W - MR" :y1="g.y(v)" :y2="g.y(v)" stroke="var(--grid)" />
        <text :x="ML - 8" :y="g.y(v) + 4" text-anchor="end" class="mono muted">{{ v.toFixed(2) }}</text>
      </g>
      <text v-for="v in XTICKS" :key="'x' + v" :x="g.x(v)" :y="MT + g.ih + 16" text-anchor="middle" class="mono muted">{{ v.toFixed(2) }}</text>
      <line :x1="ML" :x2="g.W - MR" :y1="MT + g.ih" :y2="MT + g.ih" stroke="var(--axis)" />
      <text :x="ML + g.iw / 2" :y="g.H - 6" text-anchor="middle" class="muted">Recall →</text>
      <text :transform="`translate(12 ${MT + g.ih / 2}) rotate(-90)`" text-anchor="middle" class="muted">Precisión →</text>
      <g clip-path="url(#pr-plot)">
        <g v-for="o in g.others" :key="o.cid">
          <path :d="o.d" fill="none" stroke="var(--axis)" stroke-width="1.5" />
          <path :d="o.d" fill="none" stroke="transparent" stroke-width="12" :data-tip="o.name" style="cursor:pointer"
                @click="$emit('select', o.cid)" />
        </g>
        <path :d="g.sel" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" />
      </g>
      <circle v-if="g.cur.inside" :cx="g.cur.x" :cy="g.cur.y" r="6" fill="var(--accent)" stroke="var(--surface)" stroke-width="2" />
      <rect :x="ML" :y="MT" :width="g.iw" :height="g.ih" fill="transparent" data-tip-manual
            @pointermove="onMove" @pointerleave="onLeave" @click="hover && emit('pick', hover.t)" />
      <g v-if="hover" style="pointer-events:none">
        <line :x1="hover.x" :x2="hover.x" :y1="MT" :y2="MT + g.ih" stroke="var(--text-3)" stroke-dasharray="2 3" />
        <circle :cx="hover.x" :cy="hover.y" r="5" fill="var(--surface)" stroke="var(--accent)" stroke-width="2" />
      </g>
    </svg>
  </div>
</template>
