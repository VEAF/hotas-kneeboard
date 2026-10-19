<script setup lang="ts">
import Dialog from 'primevue/dialog'
import { SHORTCUTS } from '../lib/shortcuts'

const visible = defineModel<boolean>('visible', { required: true })
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Raccourcis clavier" :style="{ width: 'min(520px, 94vw)' }">
    <table class="keys">
      <tbody>
        <tr v-for="s in SHORTCUTS" :key="s.label">
          <td><kbd v-for="k in s.keys" :key="k">{{ k }}</kbd></td>
          <td>{{ s.label }}</td>
        </tr>
      </tbody>
    </table>
  </Dialog>
</template>

<style scoped>
.keys { width: 100%; border-collapse: collapse; }
.keys td { padding: 6px 4px; border-bottom: 1px solid var(--line); }
.keys td:first-child { white-space: nowrap; width: 1%; padding-right: 16px; }
.keys kbd + kbd { margin-left: 4px; }
</style>
