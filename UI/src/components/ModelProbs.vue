<script setup>
// Probabilidad de anomalía de cada modelo (misma representación y desbalance), con el umbral marcado.
import { S, D, configId } from '../store.js'

const props = defineProps({ probOf: { type: Function, required: true } })  // (cid) => prob
</script>

<template>
  <div>
    <div v-for="m in D.models" :key="m.id" class="mrow" :class="{ sel: m.id === S.model }">
      <span>{{ m.name }}</span>
      <div class="tr">
        <div class="fl" :style="{ width: probOf(configId(m.id)) * 100 + '%' }"></div>
        <div class="tk" :style="{ left: `calc(${S.t * 100}% - 1px)` }" :data-tip="`Umbral ${S.t.toFixed(3)}`"></div>
      </div>
      <span class="vv">{{ probOf(configId(m.id)).toFixed(3) }}</span>
    </div>
  </div>
</template>
