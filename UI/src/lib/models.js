// Evalúa en el navegador los modelos exportados por src/export.py.
// Reproduce scikit-learn exactamente (verificado en export.py con predict_exported).
import { D } from '../store.js'

export function predict(m, vector) {
  let x = vector.map(Number)
  if (m.tfidf) x = x.map((v, i) => v * m.tfidf.idf[i] - m.tfidf.mean[i])

  if (m.type === 'forest') {
    // los árboles de sklearn comparan la entrada convertida a float32
    x = x.map(Math.fround)
    let s = 0
    for (const tr of m.trees) {
      let n = 0
      while (tr.f[n] !== -1) n = x[tr.f[n]] <= tr.t[n] ? tr.l[n] : tr.r[n]
      s += tr.p[n]
    }
    return s / m.trees.length
  }
  if (m.type === 'logistic') {
    let z = m.intercept
    for (let i = 0; i < x.length; i++) z += x[i] * m.coef[i]
    return 1 / (1 + Math.exp(-z))
  }
  if (m.type === 'gaussian_nb') {
    const jll = [0, 1].map(c => {
      let s = Math.log(m.prior[c])
      for (let i = 0; i < x.length; i++) {
        const v = m.var[c][i], d = x[i] - m.theta[c][i]
        s -= 0.5 * Math.log(2 * Math.PI * v) + (0.5 * d * d) / v
      }
      return s
    })
    const mx = Math.max(...jll)
    const e = jll.map(j => Math.exp(j - mx))
    return e[1] / (e[0] + e[1])
  }
  throw new Error('Modelo no soportado: ' + m.type)
}

export const predictConfig = (cid, vector) => predict(D.sim.models[cid], vector)

// ¿Cuántos bloques del dataset tienen exactamente este vector?
const vectorIndex = new Map(D.vectors.map(v => [v.v.join(','), v]))
export const lookupVector = vector => vectorIndex.get(vector.join(',')) || null
