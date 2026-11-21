// Tooltip global. Cualquier elemento con atributo data-tip (HTML) lo muestra al pasar
// el cursor; los gráficos con hover propio (curva PR) usan show/hide directamente y
// marcan su zona con data-tip-manual para que el listener global no la oculte.
let tip

function place(e) {
  const r = tip.getBoundingClientRect()
  let x = e.clientX + 14, y = e.clientY + 14
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14
  if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14
  tip.style.left = Math.max(8, x) + 'px'
  tip.style.top = Math.max(8, y) + 'px'
}

export function show(html, e) {
  tip.innerHTML = html
  tip.hidden = false
  place(e)
}

export function hide() {
  if (tip) tip.hidden = true
}

export function installTooltip(el) {
  tip = el
  document.addEventListener('pointermove', e => {
    if (e.target.closest('[data-tip-manual]')) return
    const t = e.target.closest('[data-tip]')
    if (!t) return hide()
    show(t.dataset.tip, e)
  })
  document.addEventListener('pointerleave', hide)
  document.addEventListener('click', hide)
}
