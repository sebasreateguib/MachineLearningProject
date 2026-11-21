<script setup>
import { computed } from 'vue'
import { D, cfg, modelName } from '../store.js'
import { fmt, pct } from '../lib/format.js'
import GroupedBars from '../charts/GroupedBars.vue'
import ImportanceBars from '../charts/ImportanceBars.vue'

const ds = D.meta.dataset
const amb = D.meta.ambiguity
const normal = ds.blocks - ds.anomalies

const meanRows = [...D.events]
  .sort((a, b) => Math.abs(b.mean[0] - b.mean[1]) - Math.abs(a.mean[0] - a.mean[1]))
  .slice(0, 8)
  .map(e => ({ label: e.id, n: e.mean[0], a: e.mean[1] }))

const imp = computed(() => {
  const own = cfg.value.importance
  const values = own || D.configs[D.meta.default_config].importance
  const sorted = D.events.map((e, i) => ({ label: e.id, v: values[i] })).sort((a, b) => b.v - a.v)
  const top = sorted.slice(0, 8)
  const rest = sorted.slice(8)
  const restSum = rest.reduce((s, r) => s + r.v, 0)
  return {
    own: !!own,
    rows: [...top, { label: `Otros ${rest.length}`, v: restSum, tip: `<b>${rest.length} eventos restantes</b><br>${(restSum * 100).toFixed(1)}% en total` }],
  }
})
</script>

<template>
  <div class="card">
    <h2>Distribución de clases · HDFS_v1 completo</h2>
    <p class="sub">{{ fmt(ds.blocks) }} bloques etiquetados por expertos del dominio.</p>
    <div class="prop">
      <div :style="{ flex: normal, background: 'var(--normal)' }" :data-tip="`<b>Normal</b><br>${fmt(normal)} bloques · ${pct(normal / ds.blocks, 2)}`"></div>
      <div :style="{ flex: ds.anomalies, minWidth: '8px', background: 'var(--anom)' }" :data-tip="`<b>Anomalía</b><br>${fmt(ds.anomalies)} bloques · ${pct(ds.anomalies / ds.blocks, 2)}`"></div>
    </div>
    <div class="legend" style="justify-content:space-between">
      <span><i style="background:var(--normal)"></i>Normal · <b class="mono">{{ fmt(normal) }}</b> ({{ pct(normal / ds.blocks, 2) }})</span>
      <span><i style="background:var(--anom)"></i>Anomalía · <b class="mono">{{ fmt(ds.anomalies) }}</b> ({{ pct(ds.anomalies / ds.blocks, 2) }})</span>
    </div>
    <p class="note">Un clasificador que siempre diga «Normal» tendría {{ pct(normal / ds.blocks) }} de accuracy sin detectar nada. Por eso se evalúa con precisión, recall y F1.</p>
  </div>

  <div class="grid g2">
    <div class="card"><h2>Frecuencia promedio por clase</h2>
      <p class="sub">Los 8 eventos con mayor diferencia entre bloques normales y anómalos (dataset completo).</p>
      <div class="legend" style="margin:0 0 10px"><span><i style="background:var(--normal)"></i>Normal</span><span><i style="background:var(--anom)"></i>Anomalía</span></div>
      <GroupedBars :rows="meanRows" />
    </div>
    <div class="card"><h2>Importancia de variables</h2>
      <p class="sub">{{ imp.own ? modelName() + ' (configuración actual)' : 'Random Forest (este modelo no tiene importancia de variables)' }}.</p>
      <ImportanceBars :rows="imp.rows" />
      <p class="note">En la muestra del Avance 1, E5 concentraba el 93.4 %. Con el dataset completo la señal se reparte entre más eventos. Es importancia relativa dentro del modelo, no causalidad.</p>
    </div>
  </div>

  <div class="card">
    <h2>El límite del enfoque por conteo</h2>
    <p class="sub">Bloques con exactamente el mismo vector de conteos pero distinta etiqueta: ningún modelo que solo vea conteos puede separarlos.</p>
    <div class="tblwrap"><table class="tbl">
      <thead><tr><th></th><th class="num">Muestra (Avance 1)</th><th class="num">Dataset completo</th></tr></thead>
      <tbody>
        <tr><td>Bloques</td><td class="num">{{ fmt(amb.sample.blocks) }}</td><td class="num">{{ fmt(amb.full.blocks) }}</td></tr>
        <tr><td>Vectores de conteo distintos</td><td class="num">{{ fmt(amb.sample.distinct_vectors) }}</td><td class="num">{{ fmt(amb.full.distinct_vectors) }}</td></tr>
        <tr><td>Anomalías con el mismo vector que un bloque normal</td>
          <td class="num">{{ fmt(amb.sample.ambiguous_anomalies) }} de {{ fmt(amb.sample.anomalies) }} (<b>{{ pct(amb.sample.ambiguous_anomalies / amb.sample.anomalies) }}</b>)</td>
          <td class="num">{{ fmt(amb.full.ambiguous_anomalies) }} de {{ fmt(amb.full.anomalies) }} (<b>{{ pct(amb.full.ambiguous_anomalies / amb.full.anomalies) }}</b>)</td></tr>
        <tr data-tip="Para cada vector distinto, los bloques de la clase minoritaria entre los que lo comparten. Es una cota inferior de errores para cualquier clasificador basado solo en conteos.">
          <td>Errores mínimos posibles</td><td class="num">{{ fmt(amb.sample.min_errors) }}</td><td class="num"><b>{{ fmt(amb.full.min_errors) }}</b></td></tr>
      </tbody>
    </table></div>
  </div>

  <div class="card"><h2>Diccionario de eventos</h2>
    <p class="sub">Las {{ ds.events }} plantillas de Loghub. Drain las encontró como {{ ds.drain_clusters }} clusters (similitud {{ ds.drain_sim_th }}); el parsing coincide al 100 % con la matriz oficial.</p>
    <div class="tblwrap"><table class="tbl dict">
      <thead><tr><th>Evento</th><th>Plantilla</th><th>Qué significa</th><th class="num">Líneas</th>
        <th class="num" data-tip="% de bloques normales / anómalos donde aparece">Presencia N / A</th></tr></thead>
      <tbody>
        <tr v-for="e in D.events" :key="e.id">
          <td>{{ e.id }}</td><td class="tpl">{{ e.template }}</td><td>{{ e.desc }}</td>
          <td class="num">{{ fmt(e.lines) }}</td>
          <td class="num" style="white-space:nowrap">{{ pct(e.presence[0]) }} / {{ pct(e.presence[1]) }}</td>
        </tr>
      </tbody>
    </table></div>
  </div>
</template>
