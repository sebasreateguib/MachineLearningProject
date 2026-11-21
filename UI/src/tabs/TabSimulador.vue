<script setup>
import { computed, ref } from 'vue'
import { S, D, EVENTS, cid, modelName } from '../store.js'
import { predictConfig, lookupVector } from '../lib/models.js'
import { fmt, pct } from '../lib/format.js'
import ModelProbs from '../components/ModelProbs.vue'

const typical = D.sim.typical
const TOP = 12
const showAll = ref(false)

// Eventos ordenados por importancia en el modelo por defecto (Random Forest)
const order = (() => {
  const imp = D.configs[D.meta.default_config].importance
  return EVENTS.map((e, i) => i).sort((a, b) => imp[b] - imp[a])
})()
const visible = computed(() => (showAll.value ? order : order.slice(0, TOP)))

const p = computed(() => predictConfig(cid.value, S.sim))
const flagged = computed(() => p.value >= S.t)
const probOf = c => predictConfig(c, S.sim)
const match = computed(() => lookupVector(S.sim))
const isTypical = computed(() => S.sim.every((v, i) => v === typical[i]))

// Explicación contrafactual: cuánto cambia la probabilidad si cada evento vuelve a su valor típico
const why = computed(() => {
  const items = []
  S.sim.forEach((v, i) => {
    if (v === typical[i]) return
    const alt = [...S.sim]; alt[i] = typical[i]
    items.push({ e: EVENTS[i], v, ty: typical[i], d: p.value - predictConfig(cid.value, alt) })
  })
  items.sort((a, b) => Math.abs(b.d) - Math.abs(a.d))
  const max = Math.max(0.05, ...items.map(x => Math.abs(x.d)))
  return items.map(x => ({ ...x, w: (Math.abs(x.d) / max) * 100 }))
})

function applyPreset(i) { S.sim = [...D.sim.presets[i].v]; S.preset = i }
function setEvent(i, v) { S.sim[i] = v; S.preset = null }
const sliderMax = i => Math.max(D.sim.slider_max[i], S.sim[i])
</script>

<template>
  <div class="grid g57">
    <div class="card">
      <h2>Construye un bloque</h2>
      <p class="sub">Ajusta cuántas veces aparece cada evento. El bloque normal más común tiene E5, E9, E11, E21, E23 y E26 = 3 (una por réplica) y E22 = 1.
        Los modelos son los entrenados, evaluados aquí mismo en el navegador.</p>
      <div class="presets">
        <button v-for="(pr, i) in D.sim.presets" :key="pr.name" class="chip" :class="{ on: S.preset === i }" @click="applyPreset(i)"
                :data-tip="`Aparece en ${fmt(pr.n)} bloques normales y ${fmt(pr.a)} anómalos del dataset`">{{ pr.name }}</button>
      </div>
      <div v-for="i in visible" :key="EVENTS[i]" class="sl">
        <div class="sl-h" :data-tip="`<b>${EVENTS[i]}</b> · ${D.events[i].desc}<br><span class='mono'>${D.events[i].template}</span>`">
          <span class="ev">{{ EVENTS[i] }}</span><span class="sl-l">{{ D.events[i].desc }}</span>
          <span class="ty">típico {{ typical[i] }}</span><output>{{ S.sim[i] }}</output>
        </div>
        <input type="range" min="0" :max="sliderMax(i)" step="1" :value="S.sim[i]" :aria-label="EVENTS[i]"
               :style="{ '--p': (S.sim[i] / sliderMax(i)) * 100 + '%' }" @input="e => setEvent(i, +e.target.value)">
      </div>
      <button class="chip" style="margin-top:12px" @click="showAll = !showAll">
        {{ showAll ? 'Mostrar solo los 12 eventos más importantes' : `Mostrar los ${EVENTS.length - TOP} eventos restantes` }}</button>
    </div>

    <div class="grid" style="align-content:start">
      <div class="card">
        <div class="eyebrow">Predicción · {{ modelName() }}</div>
        <div class="bigprob"><span class="v">{{ pct(p, p > 0.999 || p < 0.001 ? 2 : 1) }}</span>
          <span class="verdict" :class="flagged ? 'a' : 'n'">{{ flagged ? 'Se marca como anomalía' : 'Pasa como normal' }}</span></div>
        <div style="font-size:12.5px;color:var(--text-2);margin-bottom:16px">probabilidad de anomalía · umbral {{ S.t.toFixed(3) }}</div>
        <ModelProbs :prob-of="probOf" />
        <div class="callout" v-if="match && match.n > 0 && match.a > 0">
          <b>Vector ambiguo.</b> Este vector exacto aparece en {{ fmt(match.n) }} bloques normales y {{ fmt(match.a) }} anómalos del dataset.
          Cualquier modelo que solo vea conteos les da a todos la misma predicción, así que se equivoca en una parte. Para separarlos haría falta el orden de los eventos (DeepLog, LogRobust).</div>
        <p class="note" v-else-if="match">Este vector exacto aparece en <b>{{ fmt(match.n + match.a) }}</b> bloques del dataset:
          {{ fmt(match.n) }} normales y {{ fmt(match.a) }} anómalos.</p>
        <p class="note" v-else>Este vector no aparece en el dataset: el modelo está extrapolando a una combinación nunca vista.</p>
      </div>
      <div class="card">
        <h2>¿Qué lo hace sospechoso?</h2>
        <p class="sub">Cuánto cambia la probabilidad si cada evento vuelve a su valor típico.</p>
        <template v-if="why.length">
          <div v-for="x in why" :key="x.e" class="mrow"
               :data-tip="`Con ${x.e} = ${x.ty} (típico) la probabilidad sería ${pct(p - x.d)}`">
            <span><span class="mono" style="font-weight:600">{{ x.e }}</span>
              <span style="color:var(--text-3)"> {{ x.v > x.ty ? '↑' : '↓' }} {{ x.v }} vs {{ x.ty }}</span></span>
            <div class="tr"><div class="fl" :style="{ width: x.w + '%', background: x.d >= 0 ? 'var(--accent)' : 'var(--axis)' }"></div></div>
            <span class="vv">{{ x.d >= 0 ? '+' : '−' }}{{ Math.abs(x.d).toFixed(2) }}</span>
          </div>
        </template>
        <p v-else style="color:var(--text-2);font-size:13px;margin:0">Nada: el bloque coincide con el patrón normal más común.</p>
        <p v-if="isTypical" class="note">Prueba el preset «Anomalía frecuente 2»: es idéntico a este bloque salvo por un único evento E20.</p>
        <div class="note">Explicación aproximada: mide cada evento por separado, sin considerar cómo interactúan.</div>
      </div>
    </div>
  </div>
</template>
