<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { onKeyStroke, useEventListener } from '@vueuse/core'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'
import EditorCanvas from './EditorCanvas.vue'
import { catalog as catalogGroups, nextFree, sortedKeys } from './catalog'
import { detectInput, gamepadSupported } from './gamepad'
import {
  addExtraBox,
  canRedo,
  canUndo,
  draftTemplate,
  duplicateSelected,
  editor,
  fromTemplate,
  newDraft,
  nudgeSelected,
  open,
  redo,
  remember,
  removeSelected,
  renameSelected,
  toggleAnchor,
  toggleSplit,
  undo,
} from './state'
import { api } from '../lib/api'
import { loadTemplate, useStore } from '../lib/store'
import { inputName } from '../render/inputs'
import { diagramPage } from '../render/page'
import { FONT_CSS } from '../render/export'
import { canvasMeasurer } from '../render/text'
import { pageLanguage, t, tn } from '../lib/i18n'

const store = useStore()
const toast = useToast()
const canvasBox = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const placing = ref<string | null>(null) // null: not placing; '': the next free input
const listening = ref<AbortController | null>(null)
const detected = ref('')
const mode = ref<'edit' | 'preview'>('edit')
const saving = ref(false)
const deviceName = ref('')
const draggingFile = ref(false)
// one undo step per editing of the name, taken before its first change
let nameRemembered = false
function rememberName() {
  if (nameRemembered) return
  remember()
  nameRemembered = true
}

const draft = computed(() => editor.draft)
const keys = computed(() => (draft.value ? sortedKeys(Object.keys(draft.value.inputs)) : []))
const selectedKey = computed({
  get: () => editor.selection?.key ?? null,
  set: (key: string | null) => key && renameSelected(key),
})
const catalog = computed(() =>
  catalogGroups().map((g) => ({
    ...g,
    items: g.items.map((i) => ({ ...i, label: draft.value && i.value in draft.value.inputs && i.value !== selectedKey.value ? t('editor.placed', { input: i.label }) : i.label })),
  })),
)
const templateOptions = computed(() => [...store.state.templates].sort((a, b) => a.name.localeCompare(b.name)))
const modes = computed(() => [
  { label: t('editor.mode.edit'), value: 'edit' },
  { label: t('editor.mode.preview'), value: 'preview' },
])

// --- opening -------------------------------------------------------------------------------

if (!editor.draft) open(newDraft({ devices: editor.forDevice ? [editor.forDevice.name] : [] }))

async function startFrom(id: string) {
  if (!(await confirmDiscard())) return
  try {
    const loaded = await loadTemplate(id)
    const summary = store.state.templates.find((x) => x.id === id)
    open(fromTemplate(loaded.data, loaded.image, !!summary?.user, editor.forDevice?.name))
    fit()
  } catch (e) {
    toast.add({ severity: 'error', summary: t('editor.open_failed'), detail: (e as Error).message, life: 8000 })
  }
}

async function confirmDiscard(): Promise<boolean> {
  return !editor.dirty || window.confirm(t('editor.discard'))
}

async function startNew() {
  if (!(await confirmDiscard())) return
  open(newDraft({ devices: editor.forDevice ? [editor.forDevice.name] : [] }))
}

// --- picture -------------------------------------------------------------------------------

const MAX_SIDE = 1200
const MIN_SIDE = 700

function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

function pictureSize(dataUrl: string): Promise<[number, number]> {
  return new Promise((resolve) => {
    const image = new Image()
    image.onload = () => resolve([image.naturalWidth || 1000, image.naturalHeight || 1000])
    image.onerror = () => resolve([1000, 1000])
    image.src = dataUrl
  })
}

async function usePicture(file: File) {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!['png', 'jpg', 'jpeg', 'svg'].includes(extension)) {
    toast.add({ severity: 'warn', summary: t('editor.picture_expected'), life: 5000 })
    return
  }
  const dataUrl = await readFile(file)
  let [w, h] = await pictureSize(dataUrl)
  // a coordinate system of usual size, whatever the photo's resolution: label sizes stay readable
  const scale = Math.max(w, h) > MAX_SIDE ? MAX_SIDE / Math.max(w, h) : Math.max(w, h) < MIN_SIDE ? MIN_SIDE / Math.max(w, h) : 1
  ;[w, h] = [Math.round(w * scale), Math.round(h * scale)]
  const d = editor.draft!
  remember()
  // inputs already placed follow the new picture
  const [sx, sy] = [w / d.size[0], h / d.size[1]]
  if (d.image) {
    for (const input of Object.values(d.inputs)) {
      input.box = [input.box[0] * sx, input.box[1] * sy, input.box[2] * sx, input.box[3] * sy]
      if (input.anchor) input.anchor = [input.anchor[0] * sx, input.anchor[1] * sy]
      input.more_boxes = input.more_boxes?.map((b) => [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy])
    }
    d.split_at = d.split_at.map((x) => Math.round(x * sx * 10) / 10)
  }
  d.size = [w, h]
  d.image = { dataUrl, name: `background.${extension === 'jpeg' ? 'jpg' : extension}` }
  if (!d.name) d.name = file.name.replace(/\.[^.]+$/, '')
  fit()
}

function onPicked(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) usePicture(file)
  ;(event.target as HTMLInputElement).value = ''
}

useEventListener(window, 'dragover', (event: DragEvent) => {
  if (event.dataTransfer?.types.includes('Files')) {
    event.preventDefault()
    draggingFile.value = true
  }
})
useEventListener(window, 'dragleave', (event: DragEvent) => {
  if (!event.relatedTarget) draggingFile.value = false
})
useEventListener(window, 'drop', (event: DragEvent) => {
  draggingFile.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  event.preventDefault()
  if (file.name.endsWith('.zip')) importFile(file)
  else usePicture(file)
})

// --- zoom ----------------------------------------------------------------------------------

function fit() {
  const d = editor.draft
  const box = canvasBox.value
  if (!d || !box) return
  const scale = Math.min((box.clientWidth - 48) / d.size[0], (box.clientHeight - 48) / d.size[1])
  editor.zoom = Math.max(0.2, Math.min(3, scale))
}
const zoomBy = (factor: number) => (editor.zoom = Math.max(0.2, Math.min(4, editor.zoom * factor)))
watch(canvasBox, (box) => box && fit())

// --- identify a button ---------------------------------------------------------------------

async function identify() {
  if (listening.value) {
    listening.value.abort()
    return
  }
  checking.value?.abort() // one listener at a time
  const controller = new AbortController()
  listening.value = controller
  detected.value = ''
  try {
    const found = await detectInput(controller.signal, (device) => {
      detected.value = t('editor.identify.appeared', { device })
    })
    detected.value = t('editor.identify.found', { input: inputName(found.key), device: found.device })
    if (editor.selection) renameSelected(found.key)
    else placing.value = found.key
  } catch (e) {
    if ((e as Error).name !== 'AbortError') toast.add({ severity: 'warn', summary: (e as Error).message, life: 6000 })
  } finally {
    if (listening.value === controller) listening.value = null
  }
}
onBeforeUnmount(() => listening.value?.abort())

// --- check the numbering on the device ------------------------------------------------------

/** Inputs pressed on the device during the check, and what was found for each */
const checkLog = ref<{ key: string; boxed: boolean }[]>([])
const checking = ref<AbortController | null>(null)
const checkedBy = ref(readCheckedBy())

function readCheckedBy(): string {
  try {
    return localStorage.getItem('hotas-kneeboard-checked-by') ?? ''
  } catch {
    return ''
  }
}

/** Press every button of the device in turn: its box is selected, or it gets placed */
async function check() {
  if (checking.value) {
    checking.value.abort()
    return
  }
  const controller = new AbortController()
  checking.value = controller
  checkLog.value = []
  detected.value = ''
  try {
    while (!controller.signal.aborted) {
      const found = await detectInput(controller.signal, (device) => {
        detected.value = t('editor.check.appeared', { device })
      })
      const boxed = !!editor.draft && found.key in editor.draft.inputs
      checkLog.value = [{ key: found.key, boxed }, ...checkLog.value.filter((e) => e.key !== found.key)]
      listening.value?.abort() // one listener at a time
      if (boxed) {
        placing.value = null
        editor.selection = { key: found.key, part: 'box', index: 0 }
        detected.value = t('editor.check.boxed', { input: inputName(found.key) })
      } else {
        editor.selection = null
        placing.value = found.key
        detected.value = t('editor.check.unboxed', { input: inputName(found.key) })
      }
    }
  } catch (e) {
    if ((e as Error).name !== 'AbortError') toast.add({ severity: 'warn', summary: (e as Error).message, life: 6000 })
  } finally {
    if (checking.value === controller) checking.value = null
  }
}
onBeforeUnmount(() => checking.value?.abort())
// another draft: what was listened to belongs to the previous one
watch(
  () => editor.session,
  () => {
    checking.value?.abort()
    listening.value?.abort()
    checkLog.value = []
    detected.value = ''
  },
)

const checkedCount = computed(() => new Set(checkLog.value.map((e) => e.key)).size)

function markChecked() {
  const d = editor.draft
  const by = checkedBy.value.trim()
  if (!d) return
  if (!by) {
    toast.add({ severity: 'warn', summary: t('editor.check.who'), life: 4000 })
    return
  }
  try {
    localStorage.setItem('hotas-kneeboard-checked-by', by)
  } catch {
    // a convenience only
  }
  remember()
  d.checked = { by, date: new Date().toISOString().slice(0, 10) }
}

// --- devices -------------------------------------------------------------------------------

function addDevice() {
  const name = deviceName.value.trim()
  if (!name || !editor.draft || editor.draft.devices.includes(name)) return
  remember()
  editor.draft.devices.push(name)
  deviceName.value = ''
}
function removeDevice(name: string) {
  remember()
  editor.draft!.devices = editor.draft!.devices.filter((d) => d !== name)
}

// --- preview -------------------------------------------------------------------------------

const previewDevices = computed(() =>
  store.profiles.value.flatMap((p) => p.devices.map((d) => ({ label: `${p.name} · ${d.name}`, value: `${p.name}|${d.full_name}` }))),
)
const previewOf = ref('')
watch(
  () => editor.forDevice,
  (f) => {
    if (f) previewOf.value = `${f.profile}|${f.deviceKey}`
  },
  { immediate: true },
)
const previewSvg = computed(() => {
  const d = editor.draft
  if (mode.value !== 'preview' || !d?.image) return ''
  const [profileName, key] = previewOf.value.split('|')
  const device = store.profiles.value.find((p) => p.name === profileName)?.devices.find((x) => x.full_name === key)
  if (!device) return ''
  return diagramPage({
    profile: profileName,
    device,
    template: { data: draftTemplate(d), image: d.image.dataUrl },
    layer: null,
    measurer: canvasMeasurer(),
    fontCss: FONT_CSS,
    lang: pageLanguage(store.state.dcs?.language),
  }).svg
})

// --- save, share ---------------------------------------------------------------------------

async function save(asNew = false) {
  const d = editor.draft
  if (!d || saving.value) return
  const session = editor.session
  if (!d.image) return toast.add({ severity: 'warn', summary: t('editor.save.no_picture'), life: 5000 })
  if (!d.name.trim()) return toast.add({ severity: 'warn', summary: t('editor.save.no_name'), life: 5000 })
  saving.value = true
  try {
    const { id: _, image: __, user: ___, ...template } = draftTemplate(d)
    const summary = await api.saveTemplate({
      template: { ...template, name: d.name.trim() },
      image_name: d.image.name,
      image: d.image.dataUrl.split(',')[1],
      id: asNew ? null : d.id,
    })
    // the draft now in the editor (an undo during the request replaced the object), unless
    // another one was opened meanwhile
    if (editor.draft && editor.session === session) {
      editor.draft.id = summary.id
      editor.draft.overrides = false
    }
    editor.dirty = false
    const target = editor.forDevice
    await store.load(true)
    if (target) {
      const device = store.profiles.value.find((p) => p.name === target.profile)?.devices.find((x) => x.full_name === target.deviceKey)
      if (device && store.templateIdFor(device) !== summary.id) store.setTemplate(device, summary.id)
    }
    toast.add({ severity: 'success', summary: t('editor.save.done', { name: summary.name }), detail: target ? t('editor.save.used_for', { device: target.name }) : undefined, life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('editor.save.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    saving.value = false
  }
}

/** The draft as a new template, whatever it was started from */
function saveAsNew() {
  save(true)
}

async function importFile(file: File) {
  if (!(await confirmDiscard())) return
  try {
    const dataUrl = await readFile(file)
    const summary = await api.importTemplate(dataUrl.split(',')[1])
    await store.load(true)
    editor.dirty = false
    await startFrom(summary.id)
    toast.add({ severity: 'success', summary: t('editor.import.done', { name: summary.name }), life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('editor.import.failed'), detail: (e as Error).message, life: 10000 })
  }
}

function onImportPicked(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) importFile(file)
  ;(event.target as HTMLInputElement).value = ''
}

const savedUserTemplate = computed(() => {
  const id = editor.draft?.id
  return !!id && !editor.draft?.overrides && !!store.state.templates.find((x) => x.id === id && x.user)
})

const replacesBundled = computed(() => !!store.state.templates.find((x) => x.id === editor.draft?.id)?.replaces_bundled)

async function deleteTemplate() {
  const d = editor.draft
  const question = replacesBundled.value
    ? t('editor.delete.own_version', { name: d?.name })
    : t('editor.delete.template', { name: d?.name })
  if (!d?.id || !window.confirm(question)) return
  try {
    await api.deleteTemplate(d.id)
    open(newDraft({ devices: editor.forDevice ? [editor.forDevice.name] : [] }))
    await store.load(true)
    toast.add({ severity: 'info', summary: t('editor.delete.done'), life: 3000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('editor.delete.failed'), detail: (e as Error).message, life: 8000 })
  }
}

async function close() {
  if (!(await confirmDiscard())) return
  listening.value?.abort()
  editor.draft = null
  store.state.view = 'pages'
}

// --- keyboard ------------------------------------------------------------------------------

function inField(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null
  return !!target?.closest?.('input, textarea, select, [contenteditable=""], [contenteditable=true], [role=combobox], .p-select-overlay, .p-listbox, .p-dialog')
}

onKeyStroke((event) => {
  if (event.defaultPrevented) return
  const ctrl = event.ctrlKey || event.metaKey
  const key = event.key.toLowerCase()
  if (ctrl && key === 's') {
    event.preventDefault()
    save()
    return
  }
  if (inField(event)) return
  const step = event.shiftKey ? 10 : 1
  if (ctrl && key === 'z' && !event.shiftKey) undo()
  else if (ctrl && (key === 'y' || (key === 'z' && event.shiftKey))) redo()
  else if (ctrl && key === 'd') duplicateSelected()
  else if (ctrl) return
  else if (key === 'delete' || key === 'backspace') removeSelected()
  else if (key === 'arrowleft') nudgeSelected(-step, 0)
  else if (key === 'arrowright') nudgeSelected(step, 0)
  else if (key === 'arrowup') nudgeSelected(0, -step)
  else if (key === 'arrowdown') nudgeSelected(0, step)
  else if (key === '+' || key === '=') zoomBy(1.2)
  else if (key === '-') zoomBy(1 / 1.2)
  else if (key === '0') fit()
  else if (key === 'n') placing.value = ''
  else if (key === 'i') identify()
  else if (key === 'v') check()
  else if (key === 'p') mode.value = mode.value === 'edit' ? 'preview' : 'edit'
  else if (key === 'escape') {
    if (placing.value !== null) placing.value = null
    else editor.selection = null
  } else return
  event.preventDefault()
})

useEventListener(window, 'beforeunload', (event: BeforeUnloadEvent) => {
  if (editor.dirty) event.preventDefault()
})

function onPaletteDrag(event: DragEvent) {
  event.dataTransfer?.setData('application/x-hotas-input', '')
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy'
}

// [keys, label]: catalog keys, apart from the keys that are the same in every language
const SHORTCUTS = [
  ['N', 'editor.keys.place'],
  ['I', 'editor.keys.identify'],
  ['V', 'editor.keys.check'],
  ['keys.delete', 'editor.keys.delete'],
  ['Ctrl D', 'editor.keys.duplicate'],
  ['← ↑ → ↓', 'editor.keys.move'],
  ['Ctrl Z / Ctrl Y', 'editor.keys.undo'],
  ['+ − 0', 'editor.keys.zoom'],
  ['P', 'editor.keys.preview'],
  ['Ctrl S', 'editor.keys.save'],
]
const nextKey = computed(() => (draft.value ? inputName(nextFree(Object.keys(draft.value.inputs), editor.selection?.key)) : ''))
</script>

<template>
  <div v-if="draft" class="editor">
    <header class="ebar">
      <Button icon="pi pi-arrow-left" text :label="t('editor.back')" @click="close" />
      <InputText
        v-model="draft.name"
        :placeholder="t('editor.name')"
        size="small"
        class="name"
        :aria-label="t('editor.name')"
        @focus="nameRemembered = false"
        @beforeinput="rememberName"
      />
      <span v-if="draft.overrides" class="pill warn" v-tooltip.bottom="t('editor.overrides_tip')">{{ t('editor.overrides') }}</span>
      <span v-if="editor.dirty" class="pill">{{ t('editor.unsaved') }}</span>
      <span class="spacer" />
      <Button icon="pi pi-undo" text rounded :disabled="!canUndo" :aria-label="t('editor.undo')" v-tooltip.bottom="t('editor.undo')" @click="undo" />
      <Button icon="pi pi-refresh" text rounded :disabled="!canRedo" :aria-label="t('editor.redo')" v-tooltip.bottom="t('editor.redo')" @click="redo" />
      <Button icon="pi pi-search-minus" text rounded :aria-label="t('editor.zoom_out')" @click="zoomBy(1 / 1.2)" />
      <Button icon="pi pi-expand" text rounded :aria-label="t('editor.fit')" v-tooltip.bottom="t('editor.fit')" @click="fit" />
      <Button icon="pi pi-search-plus" text rounded :aria-label="t('editor.zoom_in')" @click="zoomBy(1.2)" />
      <SelectButton v-model="mode" :options="modes" option-label="label" option-value="value" :allow-empty="false" size="small" :aria-label="t('editor.mode.aria')" />
      <Button v-if="draft.id" size="small" severity="secondary" text :label="t('editor.save_as_new')" :disabled="saving" @click="saveAsNew" />
      <Button icon="pi pi-save" :label="t('common.save')" :loading="saving" v-tooltip.bottom="t('editor.save_tip')" @click="save()" />
    </header>

    <div class="ebody">
      <aside class="side">
        <section class="block">
          <span class="eyebrow">{{ t('editor.start') }}</span>
          <div class="row-buttons">
            <Button size="small" severity="secondary" icon="pi pi-image" :label="t('editor.picture')" @click="fileInput?.click()" />
            <Button size="small" severity="secondary" icon="pi pi-file" :label="t('editor.new')" @click="startNew" />
          </div>
          <Select
            :options="templateOptions"
            option-label="name"
            option-value="id"
            filter
            size="small"
            :placeholder="t('editor.from_template')"
            :aria-label="t('editor.from_template')"
            @update:model-value="startFrom"
          />
          <input ref="fileInput" type="file" accept=".png,.jpg,.jpeg,.svg" hidden @change="onPicked" />
        </section>

        <section class="block">
          <span class="eyebrow">{{ t('editor.split.title') }}</span>
          <div class="row-buttons">
            <Button
              size="small"
              severity="secondary"
              :icon="draft.split_at.length ? 'pi pi-times' : 'pi pi-arrows-h'"
              :label="draft.split_at.length ? t('editor.split.off') : t('editor.split.on')"
              @click="toggleSplit"
            />
          </div>
          <p class="hint">
            <template v-if="draft.split_at.length">{{ t('editor.split.hint_on') }}</template>
            <template v-else>{{ t('editor.split.hint_off') }}</template>
          </p>
        </section>

        <section class="block">
          <span class="eyebrow">{{ t('editor.devices') }}</span>
          <div class="chips">
            <span v-for="name in draft.devices" :key="name" class="chip">{{ name }}<button type="button" :aria-label="t('editor.remove_device', { name })" @click="removeDevice(name)">×</button></span>
          </div>
          <InputText v-model="deviceName" size="small" :placeholder="t('editor.device_placeholder')" :aria-label="t('editor.add_device')" @keydown.enter.prevent="addDevice" />
        </section>

        <section class="block">
          <span class="eyebrow">{{ t('editor.inputs', { n: keys.length }) }}</span>
          <div class="row-buttons">
            <span class="palette" draggable="true" :title="t('editor.palette_tip')" @dragstart="onPaletteDrag">＋ {{ t('editor.palette') }}</span>
            <Button size="small" :severity="placing !== null ? 'warn' : 'secondary'" :label="t('editor.place')" @click="placing = placing === null ? '' : null" />
            <Button
              v-if="gamepadSupported()"
              size="small"
              :severity="listening ? 'warn' : 'secondary'"
              :icon="listening ? 'pi pi-spin pi-spinner' : 'pi pi-bolt'"
              :label="listening ? t('editor.press') : t('editor.identify.label')"
              v-tooltip.bottom="t('editor.identify.tip')"
              @click="identify"
            />
          </div>
          <p v-if="placing !== null" class="hint">{{ t('editor.placing', { input: placing ? inputName(placing) : nextKey }) }}</p>
          <p v-else-if="detected" class="hint">{{ t('editor.detected', { detected }) }}</p>
          <div class="inputs" role="listbox" :aria-label="t('editor.placed_inputs')">
            <button
              v-for="key in keys"
              :key="key"
              type="button"
              class="input-row"
              :class="{ on: editor.selection?.key === key }"
              @click="editor.selection = { key, part: 'box', index: 0 }"
            >
              {{ inputName(key) }}<span class="code">{{ key }}</span>
            </button>
            <p v-if="!keys.length" class="hint">{{ t('editor.no_input') }}</p>
          </div>
        </section>

        <section v-if="editor.selection" class="block">
          <span class="eyebrow">{{ t('editor.selected') }}</span>
          <Select
            v-model="selectedKey"
            :options="catalog"
            option-label="label"
            option-value="value"
            option-group-label="label"
            option-group-children="items"
            filter
            size="small"
            :aria-label="t('editor.dcs_input')"
          />
          <div class="row-buttons">
            <Button size="small" severity="secondary" :label="draft.inputs[editor.selection.key]?.anchor ? t('editor.anchor.off') : t('editor.anchor.on')" @click="toggleAnchor" />
            <Button size="small" severity="secondary" :label="t('editor.extra_box')" v-tooltip.bottom="t('editor.extra_box_tip')" @click="addExtraBox" />
            <Button size="small" severity="secondary" :label="t('editor.duplicate')" @click="duplicateSelected" />
            <Button size="small" severity="danger" text :label="t('editor.remove')" @click="removeSelected" />
          </div>
        </section>

        <section v-if="gamepadSupported()" class="block">
          <span class="eyebrow">{{ t('editor.check.title') }}</span>
          <p class="hint">{{ t('editor.check.hint') }}</p>
          <div class="row-buttons">
            <Button
              size="small"
              :severity="checking ? 'warn' : 'secondary'"
              :icon="checking ? 'pi pi-spin pi-spinner' : 'pi pi-check-square'"
              :label="checking ? tn('editor.check.stop', checkedCount) : t('editor.check.label')"
              @click="check"
            />
          </div>
          <div v-if="checkLog.length" class="check-log">
            <span v-for="entry in checkLog" :key="entry.key" class="pill" :class="entry.key in draft.inputs ? 'ok' : 'warn'">{{ inputName(entry.key) }}</span>
          </div>
          <p v-if="draft.checked" class="hint">{{ t('editor.check.by', { by: draft.checked.by, date: draft.checked.date }) }}</p>
          <div class="row-buttons">
            <InputText v-model="checkedBy" size="small" :placeholder="t('editor.check.nickname')" :aria-label="t('editor.check.checked_by')" class="checked-by" />
            <Button size="small" severity="secondary" :label="t('editor.check.mark')" v-tooltip.bottom="t('editor.check.mark_tip')" @click="markChecked" />
          </div>
        </section>

        <section class="block">
          <span class="eyebrow">{{ t('editor.share') }}</span>
          <div class="row-buttons">
            <Button size="small" severity="secondary" icon="pi pi-download" :label="t('editor.import.label')" @click="importInput?.click()" />
            <a v-if="draft.id && !editor.dirty && !draft.overrides" class="p-button p-button-sm p-button-secondary link-button" :href="api.templateFileUrl(draft.id)" download>{{ t('editor.export') }}</a>
            <Button v-if="savedUserTemplate" size="small" severity="danger" text :label="t('editor.delete.label')" @click="deleteTemplate" />
          </div>
          <input ref="importInput" type="file" accept=".zip" hidden @change="onImportPicked" />
        </section>

        <section class="block keys-help">
          <span class="eyebrow">{{ t('editor.shortcuts') }}</span>
          <div v-for="[k, label] in SHORTCUTS" :key="k"><kbd>{{ k.startsWith('keys.') ? t(k) : k }}</kbd> {{ t(label) }}</div>
        </section>
      </aside>

      <main ref="canvasBox" class="stage" :class="{ dropping: draggingFile }">
        <div v-if="!draft.image" class="dropzone" @click="fileInput?.click()">
          <i class="pi pi-image" />
          <p>{{ t('editor.drop') }}</p>
          <p class="hint">{{ t('editor.drop_hint') }}</p>
        </div>
        <template v-else-if="mode === 'edit'">
          <EditorCanvas :placing="placing" @placed="placing = null" />
        </template>
        <div v-else class="preview">
          <Select v-model="previewOf" :options="previewDevices" option-label="label" option-value="value" filter size="small" :placeholder="t('editor.preview.of')" class="preview-select" :aria-label="t('editor.preview.aria')" />
          <div v-if="previewSvg" class="paper" v-html="previewSvg" />
          <p v-else class="hint">{{ t('editor.preview.choose') }}</p>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.editor { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.ebar { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-bottom: 1px solid var(--line); background: var(--panel-2); flex-wrap: wrap; }
.ebar .name { width: 280px; max-width: 40vw; }
.ebody { flex: 1; min-height: 0; display: grid; grid-template-columns: 300px minmax(0, 1fr); }
.side { border-right: 1px solid var(--line); overflow: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 16px; }
.block { display: flex; flex-direction: column; gap: 8px; }
.row-buttons { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 4px; background: var(--panel-3); border: 1px solid var(--line); border-radius: 999px; padding: 2px 4px 2px 10px; font-size: 12px; }
.chip button { all: unset; cursor: pointer; padding: 0 6px; color: var(--ink-3); }
.palette { cursor: grab; border: 1px dashed var(--amber); color: var(--amber); padding: 5px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }
.hint { font-size: 12px; color: var(--ink-3); margin: 0; }
.inputs { display: flex; flex-direction: column; gap: 2px; max-height: 260px; overflow: auto; }
.input-row { all: unset; cursor: pointer; display: flex; justify-content: space-between; gap: 8px; padding: 4px 8px; border-radius: 4px; font-size: 13px; }
.input-row:hover { background: var(--panel-3); }
.input-row.on { background: var(--sel); }
.input-row .code { font-family: var(--f-mono); font-size: 11px; color: var(--ink-3); }
.input-row:focus-visible { outline: 2px solid var(--amber); }
.link-button { text-decoration: none; }
.check-log { display: flex; flex-wrap: wrap; gap: 4px; }
.checked-by { width: 130px; }
.keys-help { font-size: 12px; color: var(--ink-2); gap: 4px; }
.keys-help kbd { margin-right: 6px; }
.stage { overflow: auto; padding: 24px; display: flex; align-items: flex-start; justify-content: center; background: repeating-linear-gradient(45deg, transparent 0 10px, color-mix(in srgb, var(--panel-3) 35%, transparent) 10px 11px); }
.stage.dropping { outline: 3px dashed var(--amber); outline-offset: -8px; }
.dropzone { margin: auto; max-width: 460px; text-align: center; border: 2px dashed var(--line); border-radius: 12px; padding: 40px 28px; cursor: pointer; color: var(--ink-2); }
.dropzone .pi { font-size: 40px; color: var(--amber); }
.preview { display: flex; flex-direction: column; gap: 12px; align-items: center; width: 100%; max-width: 760px; }
.preview-select { width: 100%; }
.preview .paper { width: 100%; background: #fff; border-radius: 3px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); overflow: hidden; }
.preview .paper :deep(svg) { display: block; width: 100%; height: auto; }
</style>
