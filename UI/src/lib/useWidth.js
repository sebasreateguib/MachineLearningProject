// Ancho reactivo de un elemento, para que los gráficos SVG se adapten al contenedor.
import { ref, onMounted, onBeforeUnmount } from 'vue'

export function useWidth(fallback = 600) {
  const el = ref(null)
  const width = ref(fallback)
  let ro
  onMounted(() => {
    ro = new ResizeObserver(([entry]) => { width.value = Math.max(240, Math.floor(entry.contentRect.width)) })
    ro.observe(el.value)
  })
  onBeforeUnmount(() => ro && ro.disconnect())
  return { el, width }
}
