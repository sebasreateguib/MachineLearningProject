<script setup>
import { S, D } from '../store.js'
import SegControl from './SegControl.vue'

const models = D.models.map(m => [m.id, m.short])
const reps = D.reps.map(r => [r.id, r.name])
const bals = D.bals.map(b => [b.id, b.name])
</script>

<template>
  <div class="config">
    <div class="side-label">Configuración</div>
    <div class="ctl"><label>Modelo</label><SegControl v-model="S.model" :options="models" /></div>
    <div class="ctl"><label>Representación</label><SegControl v-model="S.rep" :options="reps" /></div>
    <div class="ctl"><label>Desbalance</label><SegControl v-model="S.bal" :options="bals" /></div>
    <button class="thrchip" data-tip="Ajústalo en la pestaña <b>Umbral</b>" @click="S.tab = 'umbral'">
      <label>Umbral</label><span class="mono">{{ S.t.toFixed(3) }}</span>
    </button>
  </div>
</template>
