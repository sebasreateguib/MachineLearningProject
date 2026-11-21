<script setup>
import { onMounted, ref } from 'vue'
import { S, D, TABS, N_TEST } from './store.js'
import { installTooltip } from './lib/tooltip.js'
import { fmt } from './lib/format.js'
import ControlBar from './components/ControlBar.vue'
import TabResumen from './tabs/TabResumen.vue'
import TabModelos from './tabs/TabModelos.vue'
import TabUmbral from './tabs/TabUmbral.vue'
import TabTriage from './tabs/TabTriage.vue'
import TabSimulador from './tabs/TabSimulador.vue'
import TabDatos from './tabs/TabDatos.vue'

const VIEWS = {
  resumen: TabResumen, modelos: TabModelos, umbral: TabUmbral,
  triage: TabTriage, simulador: TabSimulador, datos: TabDatos,
}
const tipEl = ref(null)
onMounted(() => {
  installTooltip(tipEl.value)
  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return
    const t = TABS[+e.key - 1]
    if (t) goTab(t[0])
  })
})

function goTab(id) {
  S.tab = id
  scrollTo({ top: 0, behavior: 'smooth' })
}

function toggleTheme() {
  const root = document.documentElement
  const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches
  root.dataset.theme = dark ? 'light' : 'dark'
  try { localStorage.setItem('logwatch-theme', root.dataset.theme) } catch (_) { /* almacenamiento no disponible */ }
}
</script>

<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="logo" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 20 20">
            <g stroke="var(--text-3)" stroke-width="2" stroke-linecap="round">
              <line x1="3" y1="4" x2="13" y2="4" /><line x1="3" y1="8" x2="10" y2="8" /><line x1="3" y1="16" x2="12" y2="16" />
            </g>
            <line x1="3" y1="12" x2="9" y2="12" stroke="var(--anom)" stroke-width="2" stroke-linecap="round" />
            <circle cx="15" cy="12" r="2.6" fill="var(--anom)" />
          </svg>
        </div>
        <div><h1>LogWatch</h1><p>HDFS · anomalías</p></div>
      </div>

      <nav class="tabs" role="tablist" aria-label="Secciones">
        <div class="side-label">Explorar</div>
        <button v-for="([id, label], i) in TABS" :key="id" role="tab" :aria-selected="S.tab === id" @click="goTab(id)">
          <span class="num">0{{ i + 1 }}</span><span class="lbl">{{ label }}</span><kbd>{{ i + 1 }}</kbd></button>
      </nav>

      <ControlBar />

      <p class="side-foot">Proyecto final de Machine Learning<br>UTEC · 2026</p>
    </aside>

    <div class="stage">
      <div class="topbar">
        <div class="crumb mono"><span>logwatch</span><i>/</i><b>{{ S.tab }}</b></div>
        <div class="hright">
          <span class="pill" :data-tip="`Resultados sobre el conjunto de test (${fmt(N_TEST)} bloques), generados el ${D.meta.generated}`">Datos reales · test {{ fmt(N_TEST) }}</span>
          <button class="iconbtn" aria-label="Cambiar tema claro/oscuro" data-tip="Tema claro / oscuro" @click="toggleTheme">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
              <circle cx="8" cy="8" r="5.5" /><path d="M8 2.5v11a5.5 5.5 0 0 0 0-11z" fill="currentColor" stroke="none" />
            </svg>
          </button>
        </div>
      </div>

      <main>
        <div class="view" :key="S.tab">
          <component :is="VIEWS[S.tab]" />
        </div>
      </main>

      <footer><p>
        Métricas sobre el conjunto de test de HDFS_v1 ({{ fmt(D.meta.split.test) }} bloques, nunca usados para entrenar).
        Los modelos del simulador se evalúan en el navegador y reproducen exactamente a los entrenados en scikit-learn.
      </p></footer>
    </div>
  </div>
  <div id="tip" ref="tipEl" hidden></div>
</template>
