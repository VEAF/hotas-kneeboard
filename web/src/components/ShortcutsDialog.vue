<script setup lang="ts">
import Dialog from 'primevue/dialog'
import { SHORTCUTS } from '../lib/shortcuts'
import { docUrl } from '../lib/docs'
import { useStore } from '../lib/store'
import { lang, t } from '../lib/i18n'
import Tr from './Tr'

const visible = defineModel<boolean>('visible', { required: true })
const { state } = useStore()
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('shortcuts.title')" :style="{ width: 'min(520px, 94vw)' }">
    <table class="keys">
      <tbody>
        <tr v-for="s in SHORTCUTS" :key="s.label">
          <td><kbd v-for="k in s.keys" :key="k">{{ k.startsWith('keys.') ? t(k) : k }}</kbd></td>
          <td>{{ t(s.label) }}</td>
        </tr>
      </tbody>
    </table>
    <p class="doc">
      <i class="pi pi-book" />
      <span><Tr k="shortcuts.doc"><template #doc><a :href="docUrl(state.version, lang)" target="_blank" rel="noopener">{{ t('shortcuts.doc_link') }}</a></template></Tr></span>
    </p>
  </Dialog>
</template>

<style scoped>
.keys { width: 100%; border-collapse: collapse; }
.keys td { padding: 6px 4px; border-bottom: 1px solid var(--line); }
.keys td:first-child { white-space: nowrap; width: 1%; padding-right: 16px; }
.keys kbd + kbd { margin-left: 4px; }
.doc { margin: 14px 4px 0; display: flex; align-items: center; gap: 8px; }
</style>
