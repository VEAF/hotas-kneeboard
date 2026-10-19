<script setup lang="ts">
// Changes to DCS's own controls files (Saved Games\DCS\Config\Input): devices disabled in DCS,
// and the backups made before each change, listed and restorable.

import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { api } from '../lib/api'
import { useStore } from '../lib/store'
import type { DcsBackupsResponse, DcsDevicesResponse } from '../lib/types'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const toast = useToast()

const data = ref<DcsBackupsResponse | null>(null)
const error = ref('')
const working = ref('') // '' | 'backup' | id of the backup being restored
const confirming = ref<string | null>(null)

const devices = ref<DcsDevicesResponse | null>(null)

const devicesError = ref('')

async function load() {
  error.value = ''
  devicesError.value = ''
  // apart: an unreadable disabled.lua must not hide the backups that can repair it
  await Promise.all([
    api.dcsBackups().then((r) => (data.value = r)).catch((e) => (error.value = (e as Error).message)),
    api.dcsDevices().then((r) => (devices.value = r)).catch((e) => (devicesError.value = (e as Error).message)),
  ])
}

const key = (fullName: string) => fullName.toLowerCase()
/** Every device the app knows: configured in a module, disabled in DCS, or seen at DCS's last start */
const knownDevices = computed(() => {
  const byKey = new Map<string, { fullName: string; name: string; disabled: boolean; seen: boolean }>()
  const add = (fullName: string) => {
    if (!byKey.has(key(fullName))) byKey.set(key(fullName), { fullName, name: fullName.replace(/\s*\{[^}]*\}$/, ''), disabled: false, seen: false })
    return byKey.get(key(fullName))!
  }
  for (const p of store.profiles.value) for (const d of p.devices) add(d.full_name)
  for (const d of devices.value?.seen ?? []) add(d).seen = true
  for (const d of devices.value?.disabled ?? []) add(d).disabled = true
  return [...byKey.values()].sort((a, b) => a.name.localeCompare(b.name) || a.fullName.localeCompare(b.fullName))
})
const guid = (fullName: string) => fullName.match(/\{([^}]*)\}$/)?.[1] ?? ''

async function setDisabled(fullName: string, disabled: boolean) {
  working.value = `device:${fullName}`
  try {
    await api.setDeviceDisabled(fullName, disabled)
    toast.add({ severity: 'success', summary: disabled ? 'Périphérique désactivé dans DCS' : 'Périphérique réactivé dans DCS', detail: fullName, life: 4000 })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Modification impossible', detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

// --- devices DCS did not see lately: their diffs can be deleted --------------------------------------
const forgetting = ref<string | null>(null) // device awaiting confirmation

async function forget(device: string) {
  forgetting.value = null
  working.value = `forget:${device}`
  try {
    const result = await api.forgetDevice(device)
    toast.add({ severity: 'success', summary: 'Périphérique oublié', detail: `${device} : commandes supprimées dans ${result.profiles.join(', ')}`, life: 6000 })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Suppression impossible', detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

watch(visible, (open) => {
  confirming.value = null
  forgetting.value = null
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

      <p v-if="devicesError" class="warn" role="alert">Périphériques désactivés illisibles : {{ devicesError }}</p>
      <section v-if="devices">
        <h3 class="eyebrow">Périphériques désactivés dans DCS</h3>
        <p class="intro">
          Un périphérique désactivé est ignoré par DCS, dans tous les modules ; ses commandes sont gardées et reviennent à la réactivation.
          C'est le réglage « Désactiver » de l'écran des commandes du jeu.
        </p>
        <ul class="rows devices">
          <li v-for="d in knownDevices" :key="d.fullName">
            <span class="dev">
              <span class="t">{{ d.name }}</span>
              <span class="s">{{ guid(d.fullName) }}{{ d.seen ? ' · vu par DCS récemment' : '' }}</span>
            </span>
            <ToggleSwitch
              :model-value="d.disabled"
              :disabled="!!working || data?.dcs_running !== false"
              :aria-label="`Désactiver ${d.name} dans DCS`"
              @update:model-value="setDisabled(d.fullName, $event)"
            />
          </li>
        </ul>
      </section>

      <section v-if="devices">
        <h3 class="eyebrow">Périphériques absents</h3>
        <p v-if="!devices.seen.length" class="intro">
          Le journal de DCS ne nomme aucun périphérique : impossible de dire lesquels sont absents. Lance DCS une fois, périphériques branchés.
        </p>
        <template v-else>
          <p class="intro">
            Ces périphériques ont des commandes enregistrées, mais DCS ne les a pas vus lors de ses deux derniers lancements<template v-if="devices.log_date"> (journal écrit le {{ date(devices.log_date) }})</template>.
            Débranchés ce jour-là, ou partis pour de bon : à toi de voir.
            « Oublier » supprime leurs commandes dans tous les modules, après une sauvegarde.
          </p>
          <ul v-if="devices.absent.length" class="rows devices">
            <li v-for="d in devices.absent" :key="d.device">
              <span class="dev">
                <span class="t">{{ d.device.replace(/\s*\{[^}]*\}$/, '') }}</span>
                <span class="s">{{ guid(d.device) }} · {{ d.profiles.length }} module{{ d.profiles.length > 1 ? 's' : '' }} : {{ d.profiles.join(', ') }}</span>
              </span>
              <span class="act">
                <template v-if="forgetting === d.device">
                  <Button size="small" severity="danger" label="Oublier" @click="forget(d.device)" />
                  <Button size="small" text label="Annuler" @click="forgetting = null" />
                </template>
                <Button
                  v-else
                  size="small"
                  text
                  icon="pi pi-trash"
                  label="Oublier…"
                  :loading="working === `forget:${d.device}`"
                  :disabled="!!working || data?.dcs_running !== false"
                  @click="forgetting = d.device"
                />
              </span>
            </li>
          </ul>
          <p v-else class="intro">Aucun : DCS a vu tous les périphériques qui ont des commandes.</p>
        </template>
      </section>

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
.devices li { grid-template-columns: minmax(0, 1fr) auto; }
.dev { display: flex; flex-direction: column; min-width: 0; }
.dev .t { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dev .s { font: 12px var(--f-mono); color: var(--ink-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.act { display: flex; gap: 4px; justify-content: flex-end; }
@media (max-width: 600px) { .rows li { grid-template-columns: 1fr auto; } .reason, .n { grid-column: 1; } }
</style>
