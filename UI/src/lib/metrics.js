// Métricas a cualquier umbral, calculadas a partir de los histogramas de probabilidad
// del conjunto de test (200 bins por clase, exportados por src/export.py).
// Un bloque se marca como anómalo si su probabilidad >= umbral.
import { D, BINS, A_TEST, N_NORM, N_TEST } from '../store.js'

const cumCache = new Map()
const prCache = new Map()

function cumulative(cid) {
  if (cumCache.has(cid)) return cumCache.get(cid)
  const { a, n } = D.configs[cid].hist
  const cA = new Float64Array(BINS + 1), cN = new Float64Array(BINS + 1)
  for (let i = BINS - 1; i >= 0; i--) { cA[i] = cA[i + 1] + a[i]; cN[i] = cN[i + 1] + n[i] }
  const c = { cA, cN }
  cumCache.set(cid, c)
  return c
}

export function metricsAt(cid, t) {
  const { cA, cN } = cumulative(cid)
  const b = Math.max(0, Math.min(BINS, Math.round(t * BINS)))
  const TP = cA[b], FP = cN[b], FN = A_TEST - TP, TN = N_NORM - FP
  const P = TP + FP ? TP / (TP + FP) : 1
  const R = TP / A_TEST
  const F1 = P + R ? (2 * P * R) / (P + R) : 0
  return { TP, FP, FN, TN, P, R, F1, acc: (TP + TN) / N_TEST, flag: TP + FP }
}

export function prPoints(cid) {
  if (prCache.has(cid)) return prCache.get(cid)
  const pts = []
  for (let b = 1; b < BINS; b++) { const m = metricsAt(cid, b / BINS); pts.push({ t: b / BINS, R: m.R, P: m.P }) }
  prCache.set(cid, pts)
  return pts
}

// Atajos de umbral de la pestaña Umbral
export function suggestedThreshold(cid, kind) {
  if (kind === 'def') return 0.5
  let best = 0.5
  if (kind === 'f1') {
    let bv = -1
    for (let b = 1; b < BINS; b++) { const m = metricsAt(cid, b / BINS); if (m.F1 > bv) { bv = m.F1; best = b / BINS } }
  } else if (kind === 'r999') {
    best = 1 / BINS
    for (let b = 1; b < BINS; b++) if (metricsAt(cid, b / BINS).R >= 0.999) best = b / BINS
  } else if (kind === 'p99') {
    best = (BINS - 1) / BINS
    for (let b = BINS - 1; b >= 1; b--) if (metricsAt(cid, b / BINS).P >= 0.99) best = b / BINS
  }
  return best
}
