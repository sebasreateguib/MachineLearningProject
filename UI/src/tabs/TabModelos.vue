<script setup>
import { computed } from 'vue'
import { S, D, N_NORM, N_TEST, cid, cfg, configId, modelName, repName, balName } from '../store.js'
import { metricsAt } from '../lib/metrics.js'
import { fmt, f3, f4 } from '../lib/format.js'
import SegControl from '../components/SegControl.vue'
import DotPlot from '../charts/DotPlot.vue'

const METRICS = [['f1', 'F1'], ['P', 'Precisión'], ['R', 'Recall'], ['acc', 'Accuracy']]
const metricLabel = computed(() => METRICS.find(x => x[0] === S.metric)[1])

const all = computed(() => D.models.map(x => {
  const c = configId(x.id)
  return { x, c, m: metricsAt(c, S.t), cv: D.configs[c].cv }
}))
const dotRows = computed(() => all.value.map(r => ({
  id: r.x.id, name: r.x.name, short: r.x.short, sel: r.x.id === S.model,
  v: S.metric === 'f1' ? r.m.F1 : r.m[S.metric],
})))
const m = computed(() => metricsAt(cid.value, S.t))

const variants = computed(() => {
  const vals = D.reps.flatMap(r => D.bals.map(b => ({ r: r.id, b: b.id, f: D.configs[configId(S.model, r.id, b.id)].cv.f1 })))
  const best = Math.max(...vals.map(v => v.f))
  return { vals, best }
})
const cell = (r, b) => variants.value.vals.find(v => v.r === r && v.b === b)
const params = computed(() => Object.entries(cfg.value.params).map(([k, v]) => `${k} = ${v ?? 'sin límite'}`).join(' · '))
</script>

<template>
  <div class="grid g75">
    <div class="card">
      <div class="cardhead">
        <div><h2>Comparación de modelos</h2>
          <p class="sub">Clase anómala en el conjunto de prueba · {{ repName() }} · {{ balName() }} · umbral {{ S.t.toFixed(3) }}. Clic en un modelo para seleccionarlo.</p></div>
        <SegControl v-model="S.metric" :options="METRICS" />
      </div>
      <DotPlot :rows="dotRows" :label="metricLabel" @select="id => (S.model = id)" />
      <div class="tblwrap" style="margin-top:14px"><table class="tbl">
        <thead><tr><th>Modelo</th><th class="num" data-tip="Media ± desviación estándar en validación cruzada (5 folds, umbral 0.5)">F1 en CV</th>
          <th class="num">Accuracy</th><th class="num">Precisión</th><th class="num">Recall</th><th class="num">F1 test</th></tr></thead>
        <tbody>
          <tr v-for="r in all" :key="r.x.id" class="click" :class="{ sel: r.x.id === S.model }" @click="S.model = r.x.id">
            <td>{{ r.x.name }}<span v-if="r.c === D.meta.best_config" class="ev" style="margin-left:6px"
                data-tip="Mejor de las 16 configuraciones según F1 en validación cruzada">★ mejor CV</span></td>
            <td class="num">{{ f4(r.cv.f1) }} <span style="color:var(--text-3)">± {{ f4(r.cv.f1_std) }}</span></td>
            <td class="num">{{ f4(r.m.acc) }}</td><td class="num">{{ f4(r.m.P) }}</td><td class="num">{{ f4(r.m.R) }}</td>
            <td class="num"><b>{{ f4(r.m.F1) }}</b></td>
          </tr>
          <tr class="muted" data-tip="Línea base: predecir siempre <b>Normal</b>. Alto accuracy, cero anomalías detectadas.">
            <td>Siempre «Normal»</td><td class="num">—</td><td class="num">{{ f4(N_NORM / N_TEST) }}</td>
            <td class="num">—</td><td class="num">0.0000</td><td class="num">0.0000</td>
          </tr>
        </tbody>
      </table></div>
      <div class="note">La última fila muestra por qué el accuracy engaña: {{ f3(N_NORM / N_TEST) }} sin detectar una sola anomalía.</div>
    </div>

    <div class="grid" style="align-content:start">
      <div class="card">
        <h2>Matriz de confusión</h2><p class="sub">{{ modelName() }} · {{ repName() }} · {{ balName() }} · umbral {{ S.t.toFixed(3) }}</p>
        <div class="cm">
          <div></div><div class="h">Predice Normal</div><div class="h">Predice Anomalía</div>
          <div class="rh">Real<br>Normal</div>
          <div class="c"><div class="v">{{ fmt(m.TN) }}</div><div class="l">Verdaderos negativos</div></div>
          <div class="c err"><div class="v">{{ fmt(m.FP) }}</div><div class="l">Falsas alarmas</div></div>
          <div class="rh">Real<br>Anomalía</div>
          <div class="c err"><div class="v">{{ fmt(m.FN) }}</div><div class="l">No detectadas</div></div>
          <div class="c"><div class="v">{{ fmt(m.TP) }}</div><div class="l">Anomalías atrapadas</div></div>
        </div>
      </div>
      <div class="card">
        <h2>F1 en CV por variante</h2>
        <p class="sub">{{ modelName() }}: las cuatro combinaciones del experimento. Clic para aplicar.</p>
        <table class="tbl">
          <thead><tr><th></th><th v-for="b in D.bals" :key="b.id" class="num">{{ b.name }}</th></tr></thead>
          <tbody>
            <tr v-for="r in D.reps" :key="r.id"><td>{{ r.name }}</td>
              <td v-for="b in D.bals" :key="b.id" class="num" style="cursor:pointer"
                  :style="S.rep === r.id && S.bal === b.id ? 'background:var(--accent-soft)' : ''"
                  @click="S.rep = r.id; S.bal = b.id">
                <b v-if="cell(r.id, b.id).f === variants.best">{{ f4(cell(r.id, b.id).f) }} ★</b>
                <template v-else>{{ f4(cell(r.id, b.id).f) }}</template>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="note">Hiperparámetros elegidos por GridSearchCV: <span class="mono">{{ params }}</span></p>
      </div>
    </div>
  </div>
</template>
