// Estado global de LogWatch y acceso a los datos exportados por src/export.py.
import { reactive, computed, watch } from 'vue'
import data from './data/resultados.json'

export const D = data
export const BINS = D.meta.bins
export const N_TEST = D.meta.split.test
export const A_TEST = D.meta.split.test_anomalies
export const N_NORM = N_TEST - A_TEST
export const EVENTS = D.events.map(e => e.id)

export const TABS = [
  ['resumen', 'Resumen'], ['modelos', 'Modelos'], ['umbral', 'Umbral'],
  ['triage', 'Triage'], ['simulador', 'Simulador'], ['datos', 'Datos'],
]

const def = D.configs[D.meta.default_config]
const hashTab = location.hash.slice(1)

export const S = reactive({
  tab: TABS.some(t => t[0] === hashTab) ? hashTab : 'resumen',
  model: def.model, rep: def.rep, bal: def.bal,
  t: 0.5,              // umbral de decisión
  metric: 'f1',        // métrica del gráfico de la pestaña Modelos
  tri: 'all',          // filtro de la bandeja de triage
  sel: null,           // bloque seleccionado en triage
  sim: [...D.sim.typical],  // vector del simulador
  preset: 0,
})

watch(() => S.tab, tab => history.replaceState(null, '', '#' + tab))

export const configId = (m = S.model, r = S.rep, b = S.bal) => `${m}_${r}_${b}`
export const cid = computed(() => configId())
export const cfg = computed(() => D.configs[cid.value])

export const modelName = (id = S.model) => D.models.find(m => m.id === id).name
export const modelShort = (id = S.model) => D.models.find(m => m.id === id).short
export const repName = (id = S.rep) => D.reps.find(r => r.id === id).name
export const balName = (id = S.bal) => D.bals.find(b => b.id === id).name

export function setThreshold(t) {
  S.t = Math.min(0.995, Math.max(0.005, Math.round(t * BINS) / BINS))
}
