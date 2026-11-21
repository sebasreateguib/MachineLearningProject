<script setup>
import { computed, ref, watch } from 'vue'
import { S, D, EVENTS, cid, modelName } from '../store.js'
import { fmt } from '../lib/format.js'
import SegControl from '../components/SegControl.vue'
import ModelProbs from '../components/ModelProbs.vue'

const typical = D.sim.typical
const PAGE = 40
const limit = ref(PAGE)
watch(() => [S.tri, cid.value], () => (limit.value = PAGE))

const RES = {
  VP: ['ok', '✓ Atrapada'], VN: ['ok', '✓ Normal'],
  FP: ['bad', '✗ Falsa alarma'], FN: ['bad', '✗ No detectada'],
}

const rows = computed(() => {
  const k = D.config_ids.indexOf(cid.value)
  return D.triage
    .map(b => {
      const p = b.p[k], pred = p >= S.t, an = b.y === 1
      const dev = EVENTS.map((e, i) => [e, b.v[i], i]).filter(([, v, i]) => v !== typical[i])
      return { ...b, prob: p, res: pred ? (an ? 'VP' : 'FP') : (an ? 'FN' : 'VN'), dev }
    })
    .sort((a, b) => b.prob - a.prob)
    .map((r, i) => ({ ...r, rank: i + 1 }))
})
const counts = computed(() => ({
  alert: rows.value.filter(r => r.prob >= S.t).length,
  err: rows.value.filter(r => r.res === 'FP' || r.res === 'FN').length,
}))
const list = computed(() => {
  if (S.tri === 'alert') return rows.value.filter(r => r.prob >= S.t)
  if (S.tri === 'err') return rows.value.filter(r => r.res === 'FP' || r.res === 'FN')
  return rows.value
})
const shown = computed(() => list.value.slice(0, limit.value))
const dividerAt = computed(() => (S.tri === 'all' ? shown.value.findIndex(r => r.prob < S.t) : -1))

const selected = computed(() => rows.value.find(r => r.id === S.sel) || rows.value[0])
const probOf = c => selected.value.p[D.config_ids.indexOf(c)]
const eventRows = computed(() => {
  const b = selected.value
  const items = EVENTS.map((e, i) => ({ e, v: b.v[i], ty: typical[i], desc: D.events[i].desc }))
    .filter(r => r.v > 0 || r.ty > 0)
  const max = Math.max(6, ...items.map(r => Math.max(r.v, r.ty)))
  return items.map(r => ({ ...r, off: r.v !== r.ty, w: (r.v / max) * 100, tk: (r.ty / max) * 100 }))
})

function openInSimulator() {
  S.sim = [...selected.value.v]
  S.preset = null
  S.tab = 'simulador'
  scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="grid g75">
    <div class="card">
      <div class="cardhead">
        <div><h2>Bandeja de revisión</h2>
          <p class="sub">Bloques de test ordenados por probabilidad de anomalía según {{ modelName() }}, como los vería el equipo de operaciones.
            Muestra de {{ fmt(rows.length) }} bloques: todos los que algún modelo clasifica mal, más 600 elegidos al azar.</p></div>
        <SegControl v-model="S.tri"
          :options="[['all', 'Todos'], ['alert', `Alertas (${counts.alert})`], ['err', `Errores (${counts.err})`]]" />
      </div>
      <div class="tblwrap"><table class="tbl">
        <thead><tr><th>#</th><th>BlockId</th><th>Probabilidad</th><th>Fuera de lo típico</th><th>Resultado</th></tr></thead>
        <tbody>
          <template v-for="(r, i) in shown" :key="r.id">
            <tr v-if="i === dividerAt" class="divider"><td colspan="5">
              <div class="divline">umbral {{ S.t.toFixed(3) }} · debajo no se alerta</div></td></tr>
            <tr class="click" :class="{ sel: r.id === selected.id }" @click="S.sel = r.id">
              <td class="mono" style="color:var(--text-3)">{{ r.rank }}</td>
              <td class="mono" style="font-size:11.5px">{{ r.id }}</td>
              <td><div class="pbar" style="min-width:110px"><div class="tr"><div class="fl" :style="{ width: r.prob * 100 + '%' }"></div></div>
                <span class="vv">{{ r.prob.toFixed(2) }}</span></div></td>
              <td><div class="chips" style="flex-wrap:nowrap">
                <template v-if="r.dev.length">
                  <span v-for="[e, v] in r.dev.slice(0, 2)" :key="e" class="ev">{{ e }}={{ v }}</span>
                  <span v-if="r.dev.length > 2" class="ev" style="color:var(--text-3)">+{{ r.dev.length - 2 }}</span>
                </template>
                <span v-else style="color:var(--text-3);font-size:12px;white-space:nowrap">patrón típico</span>
              </div></td>
              <td><div class="res" :class="RES[r.res][0]">{{ RES[r.res][1] }}</div>
                <span class="badge" :class="r.y ? 'a' : 'n'" style="font-size:11px;color:var(--text-3)">real: {{ r.y ? 'Anomalía' : 'Normal' }}</span></td>
            </tr>
          </template>
          <tr v-if="!shown.length"><td colspan="5" style="color:var(--text-3)">Sin bloques en este filtro.</td></tr>
        </tbody>
      </table></div>
      <button v-if="limit < list.length" class="chip" style="margin-top:12px" @click="limit += PAGE">
        Mostrar {{ Math.min(PAGE, list.length - limit) }} más ({{ list.length - limit }} restantes)</button>
    </div>

    <div class="card" style="align-self:start;position:sticky;top:70px">
      <div class="eyebrow">Detalle del bloque</div>
      <div class="mono" style="font-size:13px;font-weight:600;word-break:break-all">{{ selected.id }}</div>
      <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px;flex-wrap:wrap">
        <span class="badge" :class="selected.y ? 'a' : 'n'">Etiqueta real: {{ selected.y ? 'Anomalía' : 'Normal' }}</span>
      </div>
      <div v-if="selected.amb" class="callout" style="margin:-4px 0 14px">
        <b>Vector ambiguo.</b> Otros bloques del dataset tienen exactamente estos mismos conteos con la etiqueta contraria. Ningún modelo basado solo en conteos puede acertar en todos ellos.</div>
      <h2 style="font-size:13px">Probabilidad por modelo</h2>
      <ModelProbs :prob-of="probOf" />
      <h2 style="font-size:13px;margin-top:18px">Conteo de eventos</h2>
      <p class="sub" style="margin-bottom:6px">Barra = este bloque · línea = bloque normal típico</p>
      <div v-for="r in eventRows" :key="r.e" class="mrow" :data-tip="`<b>${r.e}</b> · ${r.desc}<br>Este bloque: ${r.v} · típico: ${r.ty}`">
        <span><span class="mono" style="font-weight:600">{{ r.e }}</span></span>
        <div class="tr"><div class="fl" :style="{ width: r.w + '%', background: r.off ? 'var(--accent)' : 'var(--axis)' }"></div>
          <div class="tk" :style="{ left: `calc(${r.tk}% - 1px)` }"></div></div>
        <span class="vv">{{ r.v }}</span>
      </div>
      <button class="chip" style="margin-top:14px" @click="openInSimulator">Abrir en el simulador →</button>
    </div>
  </div>
</template>
