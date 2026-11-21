<script setup>
import { computed } from 'vue'
import { S, D, N_TEST, TABS, cid, configId, modelName, modelShort, repName, balName } from '../store.js'
import { metricsAt } from '../lib/metrics.js'
import { fmt, pct, f4 } from '../lib/format.js'
import LogStream from '../components/LogStream.vue'

const m = computed(() => metricsAt(cid.value, S.t))
const at05 = computed(() => metricsAt(cid.value, 0.5))
const rank = computed(() => D.models
  .map(x => ({ x, m: metricsAt(configId(x.id), S.t) }))
  .sort((a, b) => b.m.F1 - a.m.F1))
const amb = D.meta.ambiguity
const ds = D.meta.dataset

const questions = [
  ['modelos', '¿Qué modelo funciona mejor y con qué variante?'],
  ['umbral', '¿Cuántas alertas acepto a cambio de cuántas anomalías atrapadas?'],
  ['triage', '¿Qué bloques revisaría primero el equipo de operaciones?'],
  ['simulador', '¿Cómo reacciona el modelo si cambio los eventos de un bloque?'],
  ['datos', '¿Cómo son los datos y qué eventos importan?'],
]
const tabName = id => TABS.find(t => t[0] === id)[1]
</script>

<template>
  <section class="card hero">
    <div class="hero-main">
      <div class="eyebrow">Configuración actual · {{ modelName() }} · {{ repName() }} · {{ balName() }}</div>
      <p class="lede">De <b>{{ fmt(N_TEST) }}</b> bloques del conjunto de prueba, {{ modelName() }} marca
        <b class="hl">{{ fmt(m.flag) }}</b> para revisión, solo el {{ pct(m.flag / N_TEST) }} del total, y atrapa el
        <b class="hl">{{ pct(m.R, 2) }}</b> de las anomalías reales.</p>
      <div class="grid g2 stats">
        <div class="stat"><div class="k">Bloques en el dataset</div><div class="v">{{ fmt(ds.blocks) }}</div>
          <div class="n">{{ (ds.lines / 1e6).toFixed(1) }} M líneas de log · HDFS_v1</div></div>
        <div class="stat"><div class="k">Tasa de anomalías</div><div class="v">{{ pct(ds.anomalies / ds.blocks, 2) }}</div>
          <div class="n">{{ fmt(ds.anomalies) }} bloques etiquetados</div></div>
        <div class="stat"><div class="k">F1 de {{ modelShort() }}</div><div class="v">{{ f4(m.F1) }}</div>
          <div class="n">P {{ f4(m.P) }} · R {{ f4(m.R) }}</div></div>
        <div class="stat"><div class="k">Revisión manual evitada</div><div class="v">{{ pct(1 - m.flag / N_TEST) }}</div>
          <div class="n">frente a revisar todos los bloques</div></div>
      </div>
    </div>
    <LogStream />
  </section>

  <section class="card">
    <h2>Del Avance 1 al proyecto final</h2>
    <p class="sub">Los mismos tipos de modelo, primero sobre la muestra truncada de 7,940 bloques y ahora sobre el dataset completo.</p>
    <div class="tblwrap"><table class="tbl">
      <thead><tr><th></th><th class="num">Avance 1 (muestra)</th><th class="num">Final ({{ modelShort() }}, umbral 0.5)</th></tr></thead>
      <tbody>
        <tr><td>Bloques</td><td class="num">{{ fmt(amb.sample.blocks) }}</td><td class="num">{{ fmt(amb.full.blocks) }}</td></tr>
        <tr><td>Recall de la clase anómala</td><td class="num">0.492</td><td class="num"><b>{{ f4(at05.R) }}</b></td></tr>
        <tr><td>F1 de la clase anómala</td><td class="num">0.660</td><td class="num"><b>{{ f4(at05.F1) }}</b></td></tr>
        <tr data-tip="Anomalías con exactamente el mismo vector de conteos que algún bloque normal">
          <td>Anomalías indistinguibles por conteo</td>
          <td class="num">{{ pct(amb.sample.ambiguous_anomalies / amb.sample.anomalies) }}</td>
          <td class="num">{{ pct(amb.full.ambiguous_anomalies / amb.full.anomalies) }}</td></tr>
      </tbody>
    </table></div>
    <p class="note">El recall bajo del Avance 1 se debía al truncamiento de la muestra: sin el final del log, muchas anomalías se veían igual que bloques normales.</p>
  </section>

  <section class="card">
    <h2>Pipeline</h2><p class="sub">De texto sin estructura a una lista priorizada de bloques sospechosos.</p>
    <ol class="pipe">
      <li><div class="s">01</div><div class="t">Logs en bruto</div><div class="d">{{ fmt(ds.lines) }} líneas</div></li>
      <li><div class="s">02</div><div class="t">Parsing con Drain</div><div class="d">{{ ds.drain_clusters }} clusters → {{ ds.events }} eventos</div></li>
      <li><div class="s">03</div><div class="t">Matriz de conteo</div><div class="d">{{ fmt(ds.blocks) }} × {{ ds.events }}</div></li>
      <li><div class="s">04</div><div class="t">Entrenamiento</div><div class="d">16 configs · CV 5-fold</div></li>
      <li class="last"><div class="s">05</div><div class="t">Triage</div><div class="d">{{ fmt(m.flag) }} alertas</div></li>
    </ol>
  </section>

  <section class="grid g2">
    <div class="card">
      <h2>Ranking por F1</h2>
      <p class="sub">{{ repName() }} · {{ balName() }} · umbral {{ S.t.toFixed(3) }}. Haz clic para seleccionar un modelo.</p>
      <div class="tblwrap"><table class="tbl">
        <thead><tr><th>#</th><th>Modelo</th><th class="num">Precisión</th><th class="num">Recall</th><th class="num">F1</th></tr></thead>
        <tbody>
          <tr v-for="(r, i) in rank" :key="r.x.id" class="click" :class="{ sel: r.x.id === S.model }" @click="S.model = r.x.id">
            <td class="mono">{{ i + 1 }}</td><td>{{ r.x.name }}</td>
            <td class="num">{{ f4(r.m.P) }}</td><td class="num">{{ f4(r.m.R) }}</td><td class="num"><b>{{ f4(r.m.F1) }}</b></td>
          </tr>
        </tbody>
      </table></div>
    </div>
    <div class="card">
      <h2>Qué puedes explorar</h2><p class="sub">Cada pestaña responde una pregunta distinta sobre el modelo.</p>
      <div class="tblwrap"><table class="tbl"><tbody>
        <tr v-for="[t, q] in questions" :key="t" class="click" @click="S.tab = t">
          <td style="width:96px"><span class="ev">{{ tabName(t) }}</span></td><td>{{ q }}</td>
          <td style="color:var(--text-3)">→</td>
        </tr>
      </tbody></table></div>
    </div>
  </section>
</template>
