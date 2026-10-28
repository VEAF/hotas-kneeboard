<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, watchEffect } from 'vue'
import { onKeyStroke, useLocalStorage, useResizeObserver } from '@vueuse/core'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import ModuleList from './components/ModuleList.vue'
import DeviceList from './components/DeviceList.vue'
import PagePreview from './components/PagePreview.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import ShortcutsDialog from './components/ShortcutsDialog.vue'
import DcsConfigDialog from './components/DcsConfigDialog.vue'
import ExportProgressDialog from './components/ExportProgressDialog.vue'
import EditorView from './editor/EditorView.vue'
import { editor } from './editor/state'
import { api } from './lib/api'
import { docUrl } from './lib/docs'
import { clampColumn, type ColumnWidths } from './lib/columns'
import { exportableModules, failuresDetail, type ExportProgress, type ModuleFailure } from './lib/exportAll'
import type { Profile } from './lib/types'
import SplitButton from 'primevue/splitbutton'
import { useStore } from './lib/store'
import { kneeboardPngBase64, pagesPdf } from './render/export'
import { lang, t, tn } from './lib/i18n'
import { usePrimeVue } from 'primevue/config'

const store = useStore()
const { state, busy } = store
const toast = useToast()
const modules = ref<InstanceType<typeof ModuleList> | null>(null)
const settingsOpen = ref(false)
const helpOpen = ref(false)
const dcsConfigOpen = ref(false)
// PrimeVue's own words (an empty list, a filter without result) follow the interface's language
const primevue = usePrimeVue()
watchEffect(() => {
  Object.assign(primevue.config.locale ?? {}, {
    emptyMessage: t('primevue.empty'),
    emptyFilterMessage: t('primevue.empty_filter'),
    emptySearchMessage: t('primevue.empty_filter'),
    emptySelectionMessage: t('primevue.empty_selection'),
    searchMessage: t('primevue.search'),
    selectionMessage: t('primevue.selection'),
  })
})
const theme = useLocalStorage<'dark' | 'light'>('hotas-kneeboard-theme', 'dark')
// on <html>, not on the app: PrimeVue puts dialogs, menus and tooltips at the end of <body>
watchEffect(() => {
  document.documentElement.classList.toggle('app-dark', theme.value === 'dark')
  document.documentElement.classList.toggle('app-light', theme.value === 'light')
})

const exportedCount = computed(() => {
  const p = store.profile.value
  return p ? p.devices.filter((d) => store.isExported(p.name, d)).length : 0
})
const canKneeboard = computed(() => !!store.profile.value?.unit_type && exportedCount.value > 0 && !busy.value)
const kneeboardHint = computed(() => {
  const p = store.profile.value
  if (!p) return ''
  if (!p.unit_type) return t('app.kneeboard.not_aircraft')
  return t('app.kneeboard.writes_to', { unit: p.unit_type })
})

onMounted(() => store.load())

// --- column widths: the lines between the columns are dragged --------------------------------

const columns = useLocalStorage<ColumnWidths>('hotas-kneeboard-columns', { modules: null, devices: null }, { mergeDefaults: true })
const COLUMN_KEYS = ['modules', 'devices'] as const
const colsEl = ref<HTMLElement | null>(null)
/** x of the right edge of the module and device columns, in the column area */
const edges = ref<number[]>([])
const columnStyle = computed(() => ({
  ...(columns.value.modules ? { '--col-modules': `${columns.value.modules}px` } : {}),
  ...(columns.value.devices ? { '--col-devices': `${columns.value.devices}px` } : {}),
}))

function measureColumns() {
  const area = colsEl.value
  if (!area || area.children.length < 3) return
  const left = area.getBoundingClientRect().left
  edges.value = [0, 1].map((i) => area.children[i].getBoundingClientRect().right - left)
}
useResizeObserver(colsEl, measureColumns)
watch(columns, () => nextTick(measureColumns), { deep: true })

function startResize(event: PointerEvent, index: number) {
  const area = colsEl.value
  if (!area) return
  event.preventDefault()
  const handle = event.currentTarget as HTMLElement
  handle.setPointerCapture(event.pointerId)
  const startX = event.clientX
  const startWidth = area.children[index].getBoundingClientRect().width
  const move = (e: PointerEvent) => {
    columns.value = { ...columns.value, [COLUMN_KEYS[index]]: clampColumn(startWidth + e.clientX - startX, window.innerWidth) }
  }
  const stop = () => {
    handle.removeEventListener('pointermove', move)
    handle.removeEventListener('pointerup', stop)
    handle.removeEventListener('pointercancel', stop)
  }
  handle.addEventListener('pointermove', move)
  handle.addEventListener('pointerup', stop)
  handle.addEventListener('pointercancel', stop)
}

function resetColumn(index: number) {
  columns.value = { ...columns.value, [COLUMN_KEYS[index]]: null }
}

/** "All the modules": the aircraft with a device ticked, in the list order */
const allModules = computed(() => exportableModules(store.profiles.value, store.isExported))
/** An export of all the modules in progress, shown in a modal dialog */
const progress = ref<ExportProgress | null>(null)
function stopExport() {
  if (progress.value) progress.value.stopping = true
}

async function writeKneeboardOf(p: Profile) {
  const pages = await store.modulePages(p)
  const payload = []
  for (const page of pages) payload.push({ title: page.title, png: await kneeboardPngBase64(page, state.settings!.page_height) })
  return api.writeKneeboard(p.unit_type!, p.name, payload)
}

async function exportKneeboard() {
  const p = store.profile.value
  if (!p?.unit_type || !canKneeboard.value || !state.settings) return
  busy.value = 'kneeboard'
  try {
    const result = await writeKneeboardOf(p)
    toast.add({
      severity: 'success',
      summary: tn('app.kneeboard.written', result.written.length, { unit: p.unit_type }),
      detail: result.folder + (result.removed.length ? ` — ${tn('app.kneeboard.removed', result.removed.length)}` : ''),
      life: 6000,
    })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('app.kneeboard.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = ''
  }
}

/** Every module in turn; a module that fails does not stop the others, the summary names it */
async function exportKneeboardAll() {
  const list = allModules.value
  if (!list.length || busy.value || !state.settings) return
  busy.value = 'kneeboard'
  const failures: ModuleFailure[] = []
  let pages = 0
  let tried = 0
  progress.value = { title: t('app.kneeboard.all_title'), done: 0, total: list.length, module: '', stopping: false }
  try {
    for (const p of list) {
      if (progress.value.stopping) break
      progress.value.module = p.name
      try {
        pages += (await writeKneeboardOf(p)).written.length
      } catch (e) {
        failures.push({ module: p.name, error: (e as Error).message })
      }
      progress.value.done = ++tried
    }
  } finally {
    busy.value = ''
    progress.value = null
  }
  const done = tried - failures.length
  const stopped = tried < list.length ? ` ${t('app.kneeboard.stopped', { n: list.length - tried })}` : ''
  toast.add({
    severity: failures.length ? (done ? 'warn' : 'error') : stopped ? 'info' : 'success',
    summary: t('app.kneeboard.all_done', { pages, done, total: list.length }) + stopped,
    detail: failures.length ? `${t('app.export.failure')}\n${failuresDetail(failures)}` : t('app.kneeboard.all_folder'),
    life: failures.length ? 15000 : 6000,
  })
}

async function exportPdf() {
  const p = store.profile.value
  if (!p || exportedCount.value === 0 || busy.value) return
  busy.value = 'pdf'
  try {
    const pages = await store.modulePages(p)
    await pagesPdf(pages, `HOTAS - ${p.name}.pdf`)
    toast.add({ severity: 'success', summary: tn('app.pdf.written', pages.length, { module: p.name }), detail: t('app.pdf.where'), life: 5000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('app.pdf.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = ''
  }
}

/** One PDF, module after module: the browser stops a page downloading several files */
async function exportPdfAll() {
  const list = allModules.value
  if (!list.length || busy.value) return
  busy.value = 'pdf'
  progress.value = { title: t('app.pdf.all_title'), done: 0, total: list.length, module: '', stopping: false }
  try {
    const pages = []
    for (const p of list) {
      progress.value.module = p.name
      pages.push(...(await store.modulePages(p)))
      progress.value.done++
      // stopped: no PDF at all, a part of the modules would pass for all of them
      if (progress.value.stopping) {
        toast.add({ severity: 'info', summary: t('app.pdf.all_stopped'), detail: t('app.pdf.no_file'), life: 5000 })
        return
      }
    }
    progress.value.module = t('app.pdf.writing')
    await pagesPdf(pages, `HOTAS - ${t('app.pdf.all_file')}.pdf`)
    toast.add({
      severity: 'success',
      summary: t('app.pdf.all_written', { modules: list.length, pages: pages.length }),
      detail: t('app.pdf.where'),
      life: 5000,
    })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('app.pdf.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = ''
    progress.value = null
  }
}

const allHint = computed(() =>
  allModules.value.length
    ? t('app.export.all_hint', { n: allModules.value.length })
    : t('app.export.all_none'),
)
const pdfReady = computed(() => !!store.profile.value && exportedCount.value > 0 && !busy.value)
const kneeboardMenu = computed(() => [
  { label: t('app.kneeboard.this_module'), icon: 'pi pi-send', disabled: !canKneeboard.value, command: exportKneeboard },
  { label: `${t('app.kneeboard.all_modules')} — ${allHint.value}`, icon: 'pi pi-clone', disabled: !allModules.value.length || !!busy.value, command: exportKneeboardAll },
])
const pdfMenu = computed(() => [
  { label: t('app.pdf.this_module'), icon: 'pi pi-file-pdf', disabled: !pdfReady.value, command: exportPdf },
  { label: `${t('app.pdf.all_modules')} — ${allHint.value}`, icon: 'pi pi-clone', disabled: !allModules.value.length || !!busy.value, command: exportPdfAll },
])

async function refresh() {
  await store.load(true)
  if (!state.error) toast.add({ severity: 'info', summary: t('app.reloaded'), life: 2500 })
}

// --- keyboard ------------------------------------------------------------------------------

/** Focus in a field or a drop-down list: its keys are its own. A checkbox keeps only Space. */
function typing(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null
  if (!target?.closest) return false
  if (target.closest('input[type=checkbox]')) return event.key === ' '
  return !!target.closest('input, textarea, select, [contenteditable=""], [contenteditable=true], [role=combobox], .p-select-overlay, .p-listbox')
}
const dialogOpen = () => settingsOpen.value || helpOpen.value || dcsConfigOpen.value || !!progress.value

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

function openEditor() {
  editor.forDevice = null
  editor.draft = null
  state.view = 'editor'
}

onKeyStroke((event) => {
  // the editor has its own keys
  if (event.defaultPrevented || dialogOpen() || state.view !== 'pages') return
  const ctrl = event.ctrlKey || event.metaKey
  const key = event.key
  if (ctrl && !event.shiftKey && key.toLowerCase() === 'e') {
    event.preventDefault()
    exportKneeboard()
  } else if (ctrl && !event.shiftKey && key.toLowerCase() === 'p') {
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
  } else if (key.toLowerCase() === 'h' && !event.altKey) {
    if (store.device.value) store.setHidden(store.device.value.name, !store.isHidden(store.device.value.name))
  } else if (key.toLowerCase() === 'l' && !event.altKey) {
    store.changeSettings({ layer_mode: state.settings?.layer_mode === 'split' ? 'merge' : 'split' })
  } else if (event.shiftKey && !event.altKey && key.toLowerCase() === 'e') {
    // every module: Shift alone, Ctrl+Shift+E and Ctrl+Shift+P are the browser's (Firefox: network
    // monitor, private window)
    exportKneeboardAll()
  } else if (event.shiftKey && !event.altKey && key.toLowerCase() === 'p') {
    exportPdfAll()
  } else if (key === '/') {
    event.preventDefault()
    modules.value?.focusSearch()
  } else if (key === '?') {
    helpOpen.value = true
  }
})
</script>

<template>
  <div class="app">
    <header class="bar">
      <span class="brand"><i aria-hidden="true" />HOTAS Kneeboard</span>
      <span class="dcs" v-if="state.dcs">
        <template v-if="state.dcs.problems.length">
          <span class="pill warn">DCS</span>
          <span>{{ state.dcs.problems.join(' · ') }}</span>
        </template>
        <template v-else>
          <span class="pill ok" v-tooltip.bottom="`${state.dcs.install_dir} · ${state.dcs.saved_games_dir}`">DCS</span>
          <code>{{ state.dcs.install_dir }}</code>
          <span class="sep">·</span>
          <code>{{ state.dcs.saved_games_dir }}</code>
        </template>
      </span>
      <span class="spacer" />
      <Button v-if="state.view === 'pages'" icon="pi pi-pencil" text rounded :aria-label="t('app.bar.editor')" v-tooltip.bottom="t('app.bar.editor')" @click="openEditor" />
      <Button icon="pi pi-refresh" text rounded :aria-label="t('app.bar.reload')" v-tooltip.bottom="t('app.bar.reload')" :loading="state.loading" @click="refresh" />
      <Button icon="pi pi-sliders-h" text rounded :aria-label="t('app.bar.dcs_config')" v-tooltip.bottom="t('app.bar.dcs_config')" @click="dcsConfigOpen = true" />
      <Button icon="pi pi-cog" text rounded :aria-label="t('app.bar.settings')" v-tooltip.bottom="t('app.bar.settings')" @click="settingsOpen = true" />
      <Button :icon="theme === 'dark' ? 'pi pi-sun' : 'pi pi-moon'" text rounded :aria-label="t('app.bar.theme')" v-tooltip.bottom="t('app.bar.theme')" @click="theme = theme === 'dark' ? 'light' : 'dark'" />
      <Button icon="pi pi-question-circle" text rounded :aria-label="t('app.bar.shortcuts')" v-tooltip.bottom="t('app.bar.shortcuts')" @click="helpOpen = true" />
      <Button as="a" :href="docUrl(state.version, lang)" target="_blank" rel="noopener" icon="pi pi-book" text rounded :aria-label="t('app.bar.doc')" v-tooltip.bottom="t('app.bar.doc_tip')" />
      <div v-if="state.view === 'pages'" class="exports">
        <SplitButton
          label="PDF"
          :icon="busy === 'pdf' ? 'pi pi-spin pi-spinner' : 'pi pi-file-pdf'"
          severity="secondary"
          outlined
          :model="pdfMenu"
          :disabled="!!busy || (!pdfReady && !allModules.length)"
          :button-props="{ disabled: !pdfReady }"
          :menu-button-props="{ 'aria-label': t('app.pdf.more') }"
          v-tooltip.bottom="t('app.pdf.tip')"
          @click="exportPdf"
        />
        <SplitButton
          label="Kneeboard"
          :icon="busy === 'kneeboard' ? 'pi pi-spin pi-spinner' : 'pi pi-send'"
          :model="kneeboardMenu"
          :disabled="!!busy || (!canKneeboard && !allModules.length)"
          :button-props="{ disabled: !canKneeboard }"
          :menu-button-props="{ 'aria-label': t('app.kneeboard.more') }"
          v-tooltip.bottom="t('app.kneeboard.tip', { hint: kneeboardHint })"
          @click="exportKneeboard"
        />
      </div>
    </header>

    <div v-if="state.error" class="banner" role="alert">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ state.error }}</span>
      <Button :label="t('app.bar.settings')" size="small" text @click="settingsOpen = true" />
      <Button :label="t('app.retry')" size="small" text @click="refresh" />
    </div>
    <div v-else-if="state.bindings?.error" class="banner" role="alert">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ state.bindings.error }}</span>
      <Button :label="t('app.bar.settings')" size="small" text @click="settingsOpen = true" />
    </div>

    <EditorView v-if="state.view === 'editor'" />
    <main v-else ref="colsEl" class="cols" :style="columnStyle">
      <ModuleList ref="modules" />
      <DeviceList />
      <PagePreview />
      <div
        v-for="(edge, i) in edges"
        :key="i"
        class="col-resize"
        :style="{ left: `${edge}px` }"
        role="separator"
        aria-orientation="vertical"
        :aria-label="i === 0 ? t('app.columns.modules') : t('app.columns.devices')"
        :title="t('app.columns.tip')"
        @pointerdown="startResize($event, i)"
        @dblclick="resetColumn(i)"
      />
    </main>

    <footer v-if="state.view === 'pages'" class="status">
      <span><kbd>↑</kbd><kbd>↓</kbd> {{ t('app.status.device') }}</span>
      <span><kbd>PgUp</kbd><kbd>PgDn</kbd> {{ t('app.status.module') }}</span>
      <span><kbd>{{ t('keys.space') }}</kbd> {{ t('app.status.export') }}</span>
      <span><kbd>L</kbd> {{ t('app.status.layers') }}</span>
      <span><kbd>?</kbd> {{ t('app.status.shortcuts') }}</span>
      <span class="spacer" />
      <span v-if="state.loading">{{ t('app.status.reading') }}</span>
      <span v-else-if="store.profile.value?.unit_type">Kneeboard → Saved Games\DCS\Kneeboard\{{ store.profile.value.unit_type }}\</span>
      <span class="version">v{{ state.version }}</span>
    </footer>

    <SettingsDialog v-model:visible="settingsOpen" />
    <ShortcutsDialog v-model:visible="helpOpen" />
    <DcsConfigDialog v-model:visible="dcsConfigOpen" />
    <ExportProgressDialog :progress="progress" @stop="stopExport" />
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
.exports { display: flex; gap: 8px; margin-left: 6px; padding-left: 14px; border-left: 1px solid var(--line); }
.exports .p-button { font-weight: 600; }
.exports { align-items: center; }
.banner { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: color-mix(in srgb, var(--warn) 18%, var(--panel)); border-bottom: 1px solid var(--line); }
.cols { flex: 1; min-height: 0; display: grid; grid-template-columns: var(--col-modules, 230px) var(--col-devices, 300px) minmax(0, 1fr); position: relative; }
/* the line between two columns, dragged to resize them; wider than it looks, to be caught */
.col-resize { position: absolute; top: 0; bottom: 0; width: 9px; margin-left: -5px; cursor: col-resize; z-index: 2; touch-action: none; }
.col-resize:hover, .col-resize:active { background: linear-gradient(to right, transparent 3px, var(--amber) 3px, var(--amber) 6px, transparent 6px); }
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
/* the page keeps the full height down to small screens: narrower lists rather than stacked */
@media (max-width: 1280px) {
  .cols { grid-template-columns: var(--col-modules, 190px) var(--col-devices, 250px) minmax(0, 1fr); }
  .dcs code, .dcs .sep { display: none; }
}
@media (max-width: 860px) {
  .cols { grid-template-columns: 180px minmax(0, 1fr); grid-template-rows: minmax(0, 40%) minmax(0, 1fr); }
  .cols > .page-col { grid-column: 1 / -1; border-top: 1px solid var(--line); }
  .col-resize { display: none; }
}
</style>
