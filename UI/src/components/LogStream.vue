<script setup>
// Flujo decorativo de logs: usa las plantillas reales que Drain extrajo del dataset.
// Las marcas de tiempo y los ids de bloque son ilustrativos (generados con una semilla fija).
import { D } from '../store.js'

const tpls = D.events.filter(e => e.lines > 1000)
let seed = 7
const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296
const hex = n => Array.from({ length: n }, () => '0123456789abcdef'[Math.floor(rnd() * 16)]).join('')

let ms = 11 * 3600e3 + 21 * 60e3
const lines = Array.from({ length: 36 }, () => {
  ms += Math.floor(rnd() * 900) + 20
  const e = tpls[Math.floor(rnd() * tpls.length)]
  const t = new Date(ms).toISOString().slice(11, 23)
  return { t, id: e.id, parts: e.template.split('*'), blk: 'blk_' + hex(8), flag: rnd() < 0.11 }
})
const loop = [...lines, ...lines]
</script>

<template>
  <div class="stream" aria-hidden="true">
    <div class="stream-h">
      <span class="live"></span><span>hdfs · stream</span>
      <span class="stream-n">plantillas reales · flujo ilustrativo</span>
    </div>
    <div class="stream-body">
      <div class="stream-roll">
        <div v-for="(l, i) in loop" :key="i" class="ln" :class="{ flag: l.flag }">
          <span class="t">{{ l.t }}</span>
          <span class="id">{{ l.id }}</span>
          <span class="m"><template v-for="(p, j) in l.parts" :key="j"><span v-if="j" class="w">◆</span>{{ p }}</template></span>
          <span class="b">{{ l.blk }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
