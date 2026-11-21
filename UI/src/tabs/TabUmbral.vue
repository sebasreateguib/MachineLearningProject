<script setup>
import { computed } from 'vue'
import { S, D, N_TEST, A_TEST, cid, configId, modelName, setThreshold } from '../store.js'
import { metricsAt, suggestedThreshold } from '../lib/metrics.js'
import { fmt, pct, f4 } from '../lib/format.js'
import ScoreHistogram from '../charts/ScoreHistogram.vue'
import PRCurve from '../charts/PRCurve.vue'

const m = computed(() => metricsAt(cid.value, S.t))
const kpis = computed(() => [
  ['Precisión', f4(m.value.P)], ['Recall', f4(m.value.R)], ['F1', f4(m.value.F1)],
  ['A revisar', fmt(m.value.flag)], ['Falsas alarmas', fmt(m.value.FP)], ['No detectadas', fmt(m.value.FN)],
])
const shortcuts = [['f1', 'Máximo F1'], ['r999', 'Recall ≥ 99.9%'], ['p99', 'Precisión ≥ 99%'], ['def', 'Por defecto (0.5)']]
const active = computed(() => Object.fromEntries(shortcuts.map(([k]) => [k, Math.abs(suggestedThreshold(cid.value, k) - S.t) < 1e-9])))
const others = computed(() => D.models.filter(x => x.id !== S.model).map(x => ({ cid: configId(x.id), name: x.name, id: x.id })))
const sliderFill = computed(() => ((S.t - 0.005) / 0.99) * 100 + '%')
// Frase que traduce las métricas a la operación diaria (HTML con <b> en las cifras)
const story = computed(() => {
  const x = m.value, b = s => `<b>${s}</b>`
  const missed = x.FN === 0 ? 'Ninguna pasará sin alerta'
    : `${b(fmt(x.FN))} ${x.FN === 1 ? 'pasará' : 'pasarán'} sin alerta`
  const ratio = x.flag ? x.FP / x.flag : 0
  const alarms = ratio < 0.005 ? 'casi ninguna revisión será una falsa alarma'
    : `${b(pct(ratio))} de sus revisiones serán falsas alarmas`
  return `Si el equipo de operaciones revisa los ${b(fmt(x.flag))} bloques marcados (${pct(x.flag / N_TEST, 2)} del total), ` +
    `encontrará ${b(fmt(x.TP))} de las ${fmt(A_TEST)} anomalías. ${missed}, y ${alarms}.`
})
</script>

<template>
  <div class="card">
    <div class="thr-top">
      <div><h2>Umbral de decisión</h2>
        <p class="sub" style="margin:0">Un bloque se marca como anómalo si su probabilidad es mayor o igual al umbral. Bajarlo atrapa más anomalías a costa de más falsas alarmas; subirlo hace lo contrario.</p></div>
      <div class="thr-ctl">
        <input type="range" min="0.005" max="0.995" step="0.005" :value="S.t" :style="{ '--p': sliderFill }"
               aria-label="Umbral" @input="e => setThreshold(+e.target.value)">
        <output>{{ S.t.toFixed(3) }}</output>
      </div>
      <div class="quick"><span style="font-size:12px;color:var(--text-3);align-self:center;margin-right:4px">Atajos:</span>
        <button v-for="[k, l] in shortcuts" :key="k" class="chip" :class="{ on: active[k] }"
                @click="setThreshold(suggestedThreshold(cid, k))">{{ l }}</button>
      </div>
    </div>
    <div class="grid g6 kpis">
      <div v-for="[k, v] in kpis" :key="k" class="kpi"><div class="k">{{ k }}</div><div class="v">{{ v }}</div></div>
    </div>
    <p class="story" v-html="story"></p>
  </div>
  <div class="grid g75">
    <div class="card"><h2>¿Dónde cae cada bloque?</h2>
      <p class="sub">Probabilidad que asigna {{ modelName() }} a cada bloque de test. Las barras opacas a la derecha del umbral son los bloques marcados.</p>
      <ScoreHistogram :cid="cid" :t="S.t" />
    </div>
    <div class="card"><h2>Curva precisión–recall</h2>
      <p class="sub">Cada punto de la curva es un umbral posible. Pasa el cursor para explorarlos; haz clic para fijar uno.</p>
      <PRCurve :cid="cid" :others="others" :t="S.t" @pick="setThreshold" @select="c => (S.model = c.split('_')[0])" />
      <div class="legend"><span><i class="ln" style="background:var(--accent)"></i>{{ modelName() }}</span>
        <span><i class="ln" style="background:var(--axis)"></i>Otros modelos</span>
        <span><i style="background:var(--accent);border-radius:50%"></i>Umbral actual</span></div>
      <div class="note">Ejes ampliados: recall desde 0.95 y precisión desde 0.85; lo que queda fuera se recorta.
        <template v-if="m.R < 0.95 || m.P < 0.85">El umbral actual queda fuera del área visible.</template></div>
    </div>
  </div>
</template>
