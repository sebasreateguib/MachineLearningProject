<script setup>
defineProps({ options: { type: Array, required: true }, modelValue: { type: String, required: true } })
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="seg">
    <button v-for="[value, label] in options" :key="value" :aria-pressed="modelValue === value"
            @click="$emit('update:modelValue', value)">{{ label }}</button>
  </div>
</template>
