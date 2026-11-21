export const fmt = n => Math.round(n).toLocaleString('en-US')
export const pct = (x, d = 1) => (x * 100).toFixed(d) + '%'
export const f3 = x => x.toFixed(3)
export const f4 = x => x.toFixed(4)
