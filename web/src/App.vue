<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { onKeyStroke, useLocalStorage } from '@vueuse/core'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import ModuleList from './components/ModuleList.vue'
import DeviceList from './components/DeviceList.vue'
import PagePreview from './components/PagePreview.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import ShortcutsDialog from './components/ShortcutsDialog.vue'
import { api } from './lib/api'
import { useStore } from './lib/store'
import { pagePngBase64, pagesPdf } from './render/export'

const store = useStore()
const { state, busy } = store
const toast = useToast()
const modules = ref<InstanceType<typeof ModuleList> | null>(null)
const settingsOpen = ref(false)
const helpOpen = ref(false)
const theme = useLocalStorage<'dark' | 'light'>('hotas-kneeboard-theme', 'dark')

const exportedCount = computed(() => {
  const p = store.profile.value
  return p ? p.devices.filter((d) => store.isExported(p.name, d)).length : 0
})
const canKneeboard = computed(() => !!store.profile.value?.unit_type && exportedCount.value > 0 && !busy.value)
const kneeboardHint = computed(() => {
  const p = store.profile.value
  if (!p) return ''
  if (!p.unit_type) return "Ce profil n'est pas un avion : pas de kneeboard"
  return `Écrit les pages dans Saved Games\\DCS\\Kneeboard\\${p.unit_type}\\`
})

onMounted(() => store.load())

async function exportKneeboard() {
  const p = store.profile.value
  if (!p?.unit_type || !canKneeboard.value || !state.settings) return
  busy.value = 'kneeboard'
  try {
    const pages = await store.modulePages(p)
    const payload = []
    for (const page of pages) payload.push({ title: page.title, png: await pagePngBase64(page, state.settings.page_height) })
    const result = await api.writeKneeboard(p.unit_type, p.name, payload)
    toast.add({
      severity: 'success',
      summary: `${result.written.length} pages dans le kneeboard ${p.unit_type}`,
      detail: result.folder + (result.removed.length ? ` — ${result.removed.length} anciennes pages retirées` : ''),
      life: 6000,
    })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Export kneeboard impossible', detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = ''
  }
}

async function exportPdf() {
  const p = store.profile.value
  if (!p || exportedCount.value === 0 || busy.value) return
  busy.value = 'pdf'
  try {
    const pages = await store.modulePages(p)
    await pagesPdf(pages, `HOTAS - ${p.name}.pdf`)
    toast.add({ severity: 'success', summary: `PDF de ${p.name} : ${pages.length} pages`, detail: 'Dans le dossier des téléchargements du navigateur.', life: 5000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'PDF impossible', detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = ''
  }
}

async function refresh() {
  await store.load(true)
  if (!state.error) toast.add({ severity: 'info', summary: 'Fichiers de DCS relus', life: 2500 })
}

// --- keyboard ------------------------------------------------------------------------------

/** Focus in a field or a drop-down list: its keys are its own. A checkbox keeps only Space. */
function typing(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null
  if (!target?.closest) return false
  if (target.closest('input[type=checkbox]')) return event.key === ' '
  return !!target.closest('input, textarea, select, [contenteditable=""], [contenteditable=true], [role=combobox], [role=listbox], .p-select-overlay')
}
const dialogOpen = () => settingsOpen.value || helpOpen.value

function stepDevice(delta: number, move: boolean) {
  const list = store.devices.value
  const index = list.findIndex((d) => d.full_name === state.deviceKey)
  const target = Math.min(list.length - 1, Math.max(0, index + delta))
  if (index === -1 || target === index) return
  if (move && store.profile.value) store.moveDevice(store.profile.value.name, index, target)
  else state.deviceKey = list[target].full_name
}

function stepModule(delta: number) {
  const list = modules.value?.shown ?? store.profiles.value
  if (!list.length) return
  const index = list.findIndex((p) => p.name === state.profileName)
  const next = list[(index + delta + list.length) % list.length]
  state.profileName = next.name
  state.deviceKey = store.orderedDevices(next)[0]?.full_name ?? ''
}

onKeyStroke((event) => {
  if (event.defaultPrevented || dialogOpen()) return
  const ctrl = event.ctrlKey || event.metaKey
  const key = event.key
  if (ctrl && key.toLowerCase() === 'e') {
    event.preventDefault()
    exportKneeboard()
  } else if (ctrl && key.toLowerCase() === 'p') {
    event.preventDefault()
    exportPdf()
  } else if (key === 'F5') {
    event.preventDefault()
    refresh()
  } else if (typing(event) || ctrl || event.target instanceof HTMLElement && event.target.closest('.p-dialog')) {
    return
  } else if (key === 'ArrowDown' || key === 'ArrowUp') {
    event.preventDefault()
    stepDevice(key === 'ArrowDown' ? 1 : -1, event.altKey)
  } else if (key === 'PageDown' || key === 'PageUp') {
    event.preventDefault()
    stepModule(key === 'PageDown' ? 1 : -1)
  } else if (key === ' ') {
    event.preventDefault()
    if (store.device.value && store.profile.value) store.toggleExported(store.profile.value.name, store.device.value)
  } else if (key.toLowerCase() === 'l' && !event.altKey) {
    store.changeSettings({ layer_mode: state.settings?.layer_mode === 'split' ? 'merge' : 'split' })
  } else if (key === '/') {
    event.preventDefault()
    modules.value?.focusSearch()
  } else if (key === '?') {
    helpOpen.value = true
  }
})
</script>

<template>
  <div class="app" :class="theme === 'dark' ? 'app-dark' : 'app-light'">
    <header class="bar">
      <span class="brand"><i aria-hidden="true" />HOTAS Kneeboard</span>
      <span class="dcs" v-if="state.dcs">
        <template v-if="state.dcs.problems.length">
          <span class="pill warn">DCS</span>
          <span>{{ state.dcs.problems.join(' · ') }}</span>
        </template>
        <template v-else>
          <span class="pill ok">DCS</span>
          <code>{{ state.dcs.install_dir }}</code>
          <span class="sep">·</span>
          <code>{{ state.dcs.saved_games_dir }}</code>
        </template>
      </span>
      <span class="spacer" />
      <Button icon="pi pi-refresh" text rounded aria-label="Relire les fichiers de DCS (F5)" v-tooltip.bottom="'Relire les fichiers de DCS (F5)'" :loading="state.loading" @click="refresh" />
      <Button icon="pi pi-cog" text rounded aria-label="Réglages" v-tooltip.bottom="'Réglages'" @click="settingsOpen = true" />
      <Button :icon="theme === 'dark' ? 'pi pi-sun' : 'pi pi-moon'" text rounded aria-label="Thème clair ou sombre" v-tooltip.bottom="'Thème clair / sombre'" @click="theme = theme === 'dark' ? 'light' : 'dark'" />
      <Button icon="pi pi-question-circle" text rounded aria-label="Raccourcis clavier (?)" v-tooltip.bottom="'Raccourcis clavier (?)'" @click="helpOpen = true" />
      <Button
        severity="secondary"
        :disabled="!store.profile.value || exportedCount === 0 || !!busy"
        :loading="busy === 'pdf'"
        icon="pi pi-file-pdf"
        @click="exportPdf"
      >
        <span class="btn-label">PDF du module</span><kbd>Ctrl P</kbd>
      </Button>
      <Button
        :disabled="!canKneeboard"
        :loading="busy === 'kneeboard'"
        icon="pi pi-upload"
        v-tooltip.bottom="kneeboardHint"
        @click="exportKneeboard"
      >
        <span class="btn-label">Exporter vers le kneeboard</span><kbd>Ctrl E</kbd>
      </Button>
    </header>

    <div v-if="state.error" class="banner" role="alert">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ state.error }}</span>
      <Button label="Réglages" size="small" text @click="settingsOpen = true" />
      <Button label="Réessayer" size="small" text @click="refresh" />
    </div>
    <div v-else-if="state.bindings?.error" class="banner" role="alert">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ state.bindings.error }}</span>
      <Button label="Réglages" size="small" text @click="settingsOpen = true" />
    </div>

    <main class="cols">
      <ModuleList ref="modules" />
      <DeviceList />
      <PagePreview />
    </main>

    <footer class="status">
      <span><kbd>↑</kbd><kbd>↓</kbd> périphérique</span>
      <span><kbd>PgUp</kbd><kbd>PgDn</kbd> module</span>
      <span><kbd>Espace</kbd> inclure dans l'export</span>
      <span><kbd>L</kbd> calques</span>
      <span><kbd>?</kbd> tous les raccourcis</span>
      <span class="spacer" />
      <span v-if="state.loading">Lecture des fichiers de DCS…</span>
      <span v-else-if="store.profile.value?.unit_type">Kneeboard → Saved Games\DCS\Kneeboard\{{ store.profile.value.unit_type }}\</span>
      <span class="version">v{{ state.version }}</span>
    </footer>

    <SettingsDialog v-model:visible="settingsOpen" />
    <ShortcutsDialog v-model:visible="helpOpen" />
    <Toast position="bottom-center" />
  </div>
</template>

<style>
.app { height: 100%; display: flex; flex-direction: column; background: var(--panel); color: var(--ink); }
.bar { display: flex; align-items: center; gap: 8px 12px; padding: 8px 14px; background: var(--panel-2); border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.brand { font-family: var(--f-display); font-weight: 700; font-size: 19px; letter-spacing: 0.06em; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
.brand i { width: 12px; height: 12px; border-radius: 2px; background: var(--amber); display: inline-block; transform: rotate(45deg); }
.dcs { font-size: 12px; color: var(--ink-2); display: flex; align-items: center; gap: 6px; min-width: 0; overflow: hidden; }
.dcs code { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dcs .sep { color: var(--ink-3); }
.spacer { flex: 1; }
.bar kbd { background: transparent; border-color: currentColor; color: inherit; opacity: 0.7; margin-left: 8px; }
.banner { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: color-mix(in srgb, var(--warn) 18%, var(--panel)); border-bottom: 1px solid var(--line); }
.cols { flex: 1; min-height: 0; display: grid; grid-template-columns: 240px 320px minmax(0, 1fr); }
.col { border-right: 1px solid var(--line); display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.col:last-child { border-right: 0; }
.colhead { padding: 10px 12px 8px; display: flex; flex-direction: column; gap: 8px; border-bottom: 1px solid var(--line); }
.list { overflow: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px; flex: 1; }
.row { display: grid; gap: 8px; align-items: center; padding: 7px 8px; border-radius: 6px; cursor: pointer; border: 1px solid transparent; user-select: none; }
.row:hover { background: var(--panel-3); }
.row.on { background: var(--sel); border-color: var(--line); }
.row .meta { display: flex; flex-direction: column; min-width: 0; }
.row .t { font-weight: 600; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row .s { font-size: 12px; color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.n { font: 600 12px var(--f-mono); color: var(--ink-2); font-variant-numeric: tabular-nums; }
.empty { color: var(--ink-3); padding: 8px; margin: 0; }
.status { display: flex; gap: 16px; flex-wrap: wrap; padding: 6px 14px; border-top: 1px solid var(--line); background: var(--panel-2); font-size: 12px; color: var(--ink-3); }
.status kbd + kbd { margin-left: 2px; }
.version { font-family: var(--f-mono); }
@media (max-width: 1100px) {
  .cols { grid-template-columns: 200px minmax(0, 1fr); grid-template-rows: minmax(0, 40%) minmax(0, 1fr); }
  .cols > .page-col { grid-column: 1 / -1; border-top: 1px solid var(--line); }
  .btn-label { display: none; }
}
</style>
