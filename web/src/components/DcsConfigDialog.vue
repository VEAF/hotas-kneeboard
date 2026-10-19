<script setup lang="ts">
// Changes to DCS's own controls files (Saved Games\DCS\Config\Input): the backups made before each
// change, listed and restorable.

import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import { api } from '../lib/api'
import { useStore } from '../lib/store'
import type { DcsBackupsResponse } from '../lib/types'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const toast = useToast()

const data = ref<DcsBackupsResponse | null>(null)
const error = ref('')
const working = ref('') // '' | 'backup' | id of the backup being restored
const confirming = ref<string | null>(null)

async function load() {
  error.value = ''
  try {
    data.value = await api.dcsBackups()
  } catch (e) {
    error.value = (e as Error).message
  }
}

watch(visible, (open) => {
  confirming.value = null
  if (open) load()
})

const date = (iso: string) =>
  new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'medium' })
const size = (bytes: number) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} Ko` : `${(bytes / 1024 / 1024).toFixed(1)} Mo`)

async function backupNow() {
  working.value = 'backup'
  try {
    const backup = await api.createDcsBackup()
    toast.add({ severity: 'success', summary: 'Sauvegarde faite', detail: `${backup.files} fichiers, ${size(backup.size)}`, life: 4000 })
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Sauvegarde impossible', detail: (e as Error).message, life: 10000 })
  } finally {
    working.value = ''
  }
}

async function restore(id: string) {
  confirming.value = null
  working.value = id
  try {
    await api.restoreDcsBackup(id)
    toast.add({
      severity: 'success',
      summary: 'Commandes DCS restaurées',
      detail: "L'état d'avant est lui-même sauvegardé, en tête de liste.",
      life: 6000,
    })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Restauration impossible', detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Commandes DCS" :style="{ width: 'min(720px, 94vw)' }">
    <div class="body">
      <p class="intro">
        Avant chaque modification des commandes de DCS, l'application sauvegarde tout le dossier
        <code>Saved Games\DCS\Config\Input</code>. Les 20 dernières sauvegardes sont gardées.
      </p>

      <p v-if="data?.dcs_running" class="warn" role="alert">
        <i class="pi pi-exclamation-triangle" /> DCS est lancé : ferme-le pour restaurer ou modifier ses commandes, il réécrit ces fichiers en enregistrant.
      </p>
      <p v-else-if="data && data.dcs_running === null" class="warn" role="alert">
        <i class="pi pi-exclamation-triangle" /> Impossible de savoir si DCS est lancé : les modifications seront refusées.
      </p>
      <p v-if="error" class="warn" role="alert">{{ error }}</p>

      <section>
        <div class="head">
          <h3 class="eyebrow">Sauvegardes</h3>
          <Button size="small" severity="secondary" icon="pi pi-save" label="Sauvegarder maintenant" :loading="working === 'backup'" :disabled="!!working" @click="backupNow" />
        </div>
        <ul v-if="data?.backups.length" class="rows">
          <li v-for="b in data.backups" :key="b.id">
            <span class="when">{{ date(b.created) }}</span>
            <span class="reason">{{ b.reason }}</span>
            <span class="n">{{ b.files }} fichiers · {{ size(b.size) }}</span>
            <span class="act">
              <template v-if="confirming === b.id">
                <Button size="small" severity="danger" label="Restaurer" @click="restore(b.id)" />
                <Button size="small" text label="Annuler" @click="confirming = null" />
              </template>
              <Button
                v-else
                size="small"
                text
                icon="pi pi-history"
                label="Restaurer…"
                :loading="working === b.id"
                :disabled="!!working || data.dcs_running !== false"
                @click="confirming = b.id"
              />
            </span>
          </li>
        </ul>
        <p v-else-if="data" class="intro">Aucune sauvegarde pour l'instant.</p>
        <p v-if="confirming" class="intro">
          Les commandes de DCS reviendront exactement à cet état, pour tous les modules ; l'état actuel est sauvegardé d'abord.
        </p>
        <p v-if="data" class="intro folder">Dossier : <code>{{ data.folder }}</code></p>
      </section>
    </div>
  </Dialog>
</template>

<style scoped>
.body { display: flex; flex-direction: column; gap: 14px; }
.intro { color: var(--ink-3); font-size: 13px; margin: 0; }
.folder code { word-break: break-all; }
.warn { margin: 0; padding: 8px 10px; border-radius: 6px; background: color-mix(in srgb, var(--warn) 18%, var(--panel)); }
.head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
h3 { margin: 0; }
.rows { list-style: none; margin: 0 0 8px; padding: 0; border: 1px solid var(--line); border-radius: 6px; max-height: 50vh; overflow: auto; }
.rows li { display: grid; grid-template-columns: 150px minmax(0, 1fr) auto auto; gap: 10px; align-items: center; padding: 5px 10px; border-bottom: 1px solid var(--line); }
.rows li:last-child { border-bottom: 0; }
.when { font-variant-numeric: tabular-nums; }
.reason { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ink-2); }
.act { display: flex; gap: 4px; justify-content: flex-end; }
@media (max-width: 600px) { .rows li { grid-template-columns: 1fr auto; } .reason, .n { grid-column: 1; } }
</style>
