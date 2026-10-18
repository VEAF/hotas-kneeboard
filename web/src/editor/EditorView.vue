<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { onKeyStroke, useEventListener } from '@vueuse/core'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'
import EditorCanvas from './EditorCanvas.vue'
import { CATALOG, nextFree, sortedKeys } from './catalog'
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
  undo,
} from './state'
import { api } from '../lib/api'
import { loadTemplate, useStore } from '../lib/store'
import { inputName } from '../render/inputs'
import { diagramPage } from '../render/page'
import { FONT_CSS } from '../render/export'
import { canvasMeasurer } from '../render/text'

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
  CATALOG.map((g) => ({
    ...g,
    items: g.items.map((i) => ({ ...i, label: draft.value && i.value in draft.value.inputs && i.value !== selectedKey.value ? `${i.label} (placé)` : i.label })),
  })),
)
const templateOptions = computed(() => [...store.state.templates].sort((a, b) => a.name.localeCompare(b.name)))
const modes = [
  { label: 'Édition', value: 'edit' },
  { label: 'Aperçu', value: 'preview' },
]

// --- opening -------------------------------------------------------------------------------

if (!editor.draft) open(newDraft({ devices: editor.forDevice ? [editor.forDevice.name] : [] }))

async function startFrom(id: string) {
  if (!(await confirmDiscard())) return
  try {
    const loaded = await loadTemplate(id)
    const summary = store.state.templates.find((t) => t.id === id)
    open(fromTemplate(loaded.data, loaded.image, !!summary?.user, editor.forDevice?.name))
    fit()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Gabarit impossible à ouvrir', detail: (e as Error).message, life: 8000 })
  }
}

async function confirmDiscard(): Promise<boolean> {
  return !editor.dirty || window.confirm('Les modifications non enregistrées seront perdues. Continuer ?')
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
    toast.add({ severity: 'warn', summary: 'Image PNG, JPG ou SVG attendue', life: 5000 })
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
  const controller = new AbortController()
  listening.value = controller
  detected.value = ''
  try {
    const found = await detectInput(controller.signal, (device) => {
      detected.value = `${device} vient d'apparaître : appuie encore une fois sur le bouton`
    })
    detected.value = `${inputName(found.key)} sur ${found.device}`
    if (editor.selection) renameSelected(found.key)
    else placing.value = found.key
  } catch (e) {
    if ((e as Error).name !== 'AbortError') toast.add({ severity: 'warn', summary: (e as Error).message, life: 6000 })
  } finally {
    if (listening.value === controller) listening.value = null
  }
}
onBeforeUnmount(() => listening.value?.abort())

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
  }).svg
})

// --- save, share ---------------------------------------------------------------------------

async function save() {
  const d = editor.draft
  if (!d || saving.value) return
  if (!d.image) return toast.add({ severity: 'warn', summary: "Ajoute d'abord l'image du périphérique", life: 5000 })
  if (!d.name.trim()) return toast.add({ severity: 'warn', summary: 'Donne un nom au gabarit', life: 5000 })
  saving.value = true
  try {
    const { id: _, image: __, user: ___, ...template } = draftTemplate(d)
    const summary = await api.saveTemplate({
      template: { ...template, name: d.name.trim() },
      image_name: d.image.name,
      image: d.image.dataUrl.split(',')[1],
      id: d.id,
    })
    // the draft now in the editor (an undo during the request replaced the object)
    if (editor.draft) {
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
    toast.add({ severity: 'success', summary: `Gabarit « ${summary.name} » enregistré`, detail: target ? `Utilisé pour ${target.name}` : undefined, life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Enregistrement impossible', detail: (e as Error).message, life: 10000 })
  } finally {
    saving.value = false
  }
}

/** The draft as a new template, whatever it was started from */
function saveAsNew() {
  if (!editor.draft) return
  editor.draft.id = null
  editor.draft.overrides = false
  save()
}

async function importFile(file: File) {
  if (!(await confirmDiscard())) return
  try {
    const dataUrl = await readFile(file)
    const summary = await api.importTemplate(dataUrl.split(',')[1])
    await store.load(true)
    editor.dirty = false
    await startFrom(summary.id)
    toast.add({ severity: 'success', summary: `Gabarit « ${summary.name} » importé`, life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Import impossible', detail: (e as Error).message, life: 10000 })
  }
}

function onImportPicked(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) importFile(file)
  ;(event.target as HTMLInputElement).value = ''
}

const savedUserTemplate = computed(() => {
  const id = editor.draft?.id
  return !!id && !editor.draft?.overrides && !!store.state.templates.find((t) => t.id === id && t.user)
})

const replacesBundled = computed(() => !!store.state.templates.find((t) => t.id === editor.draft?.id)?.replaces_bundled)

async function deleteTemplate() {
  const d = editor.draft
  const question = replacesBundled.value
    ? `Supprimer ta version de « ${d?.name} » ? Celle de la bibliothèque reviendra.`
    : `Supprimer le gabarit « ${d?.name} » ? Il disparaît de ta bibliothèque.`
  if (!d?.id || !window.confirm(question)) return
  try {
    await api.deleteTemplate(d.id)
    open(newDraft({ devices: editor.forDevice ? [editor.forDevice.name] : [] }))
    await store.load(true)
    toast.add({ severity: 'info', summary: 'Gabarit supprimé', life: 3000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Suppression impossible', detail: (e as Error).message, life: 8000 })
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
  return !!target?.closest?.('input, textarea, select, [contenteditable=""], [contenteditable=true], [role=combobox], [role=listbox], .p-select-overlay, .p-dialog')
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

const SHORTCUTS = [
  ['N', 'placer une entrée (puis clic sur l\'image)'],
  ['I', 'identifier en appuyant sur le bouton'],
  ['Suppr', 'supprimer la sélection'],
  ['Ctrl D', 'dupliquer sur le bouton suivant'],
  ['← ↑ → ↓', 'déplacer (Maj : de 10)'],
  ['Ctrl Z / Ctrl Y', 'annuler / rétablir'],
  ['+ − 0', 'zoom, ajuster'],
  ['P', 'aperçu avec de vraies liaisons'],
  ['Ctrl S', 'enregistrer'],
]
const nextKey = computed(() => (draft.value ? inputName(nextFree(Object.keys(draft.value.inputs), editor.selection?.key)) : ''))
</script>

<template>
  <div v-if="draft" class="editor">
    <header class="ebar">
      <Button icon="pi pi-arrow-left" text label="Pages" @click="close" />
      <InputText
        v-model="draft.name"
        placeholder="Nom du gabarit"
        size="small"
        class="name"
        aria-label="Nom du gabarit"
        @focus="nameRemembered = false"
        @beforeinput="rememberName"
      />
      <span v-if="draft.overrides" class="pill warn" v-tooltip.bottom="'Enregistré, ton gabarit passera devant celui de la bibliothèque'">remplace la bibliothèque</span>
      <span v-if="editor.dirty" class="pill">non enregistré</span>
      <span class="spacer" />
      <Button icon="pi pi-undo" text rounded :disabled="!canUndo" aria-label="Annuler (Ctrl Z)" v-tooltip.bottom="'Annuler (Ctrl Z)'" @click="undo" />
      <Button icon="pi pi-refresh" text rounded :disabled="!canRedo" aria-label="Rétablir (Ctrl Y)" v-tooltip.bottom="'Rétablir (Ctrl Y)'" @click="redo" />
      <Button icon="pi pi-search-minus" text rounded aria-label="Zoom arrière (-)" @click="zoomBy(1 / 1.2)" />
      <Button icon="pi pi-expand" text rounded aria-label="Ajuster (0)" v-tooltip.bottom="'Ajuster (0)'" @click="fit" />
      <Button icon="pi pi-search-plus" text rounded aria-label="Zoom avant (+)" @click="zoomBy(1.2)" />
      <SelectButton v-model="mode" :options="modes" option-label="label" option-value="value" :allow-empty="false" size="small" aria-label="Édition ou aperçu" />
      <Button v-if="draft.id" size="small" severity="secondary" text label="Enregistrer comme nouveau" :disabled="saving" @click="saveAsNew" />
      <Button icon="pi pi-save" :loading="saving" @click="save"><span class="btn-label">Enregistrer</span><kbd>Ctrl S</kbd></Button>
    </header>

    <div class="ebody">
      <aside class="side">
        <section class="block">
          <span class="eyebrow">Départ</span>
          <div class="row-buttons">
            <Button size="small" severity="secondary" icon="pi pi-image" label="Image…" @click="fileInput?.click()" />
            <Button size="small" severity="secondary" icon="pi pi-file" label="Nouveau" @click="startNew" />
          </div>
          <Select
            :options="templateOptions"
            option-label="name"
            option-value="id"
            filter
            size="small"
            placeholder="Partir d'un gabarit…"
            aria-label="Partir d'un gabarit"
            @update:model-value="startFrom"
          />
          <input ref="fileInput" type="file" accept=".png,.jpg,.jpeg,.svg" hidden @change="onPicked" />
        </section>

        <section class="block">
          <span class="eyebrow">Périphériques DCS</span>
          <div class="chips">
            <span v-for="name in draft.devices" :key="name" class="chip">{{ name }}<button type="button" :aria-label="`Retirer ${name}`" @click="removeDevice(name)">×</button></span>
          </div>
          <InputText v-model="deviceName" size="small" placeholder="Nom DCS, sans GUID, puis Entrée" aria-label="Ajouter un nom de périphérique" @keydown.enter.prevent="addDevice" />
        </section>

        <section class="block">
          <span class="eyebrow">Entrées · {{ keys.length }}</span>
          <div class="row-buttons">
            <span class="palette" draggable="true" title="Glisse sur l'image" @dragstart="onPaletteDrag">＋ Entrée</span>
            <Button size="small" :severity="placing !== null ? 'warn' : 'secondary'" label="Placer (N)" @click="placing = placing === null ? '' : null" />
            <Button
              v-if="gamepadSupported()"
              size="small"
              :severity="listening ? 'warn' : 'secondary'"
              :icon="listening ? 'pi pi-spin pi-spinner' : 'pi pi-bolt'"
              :label="listening ? 'Appuie…' : 'Identifier (I)'"
              v-tooltip.bottom="'Appuie sur le bouton du périphérique : l\'entrée est reconnue'"
              @click="identify"
            />
          </div>
          <p v-if="placing !== null" class="hint">Clique sur l'image à l'endroit du bouton : {{ placing ? inputName(placing) : nextKey }}. Échap pour annuler.</p>
          <p v-else-if="detected" class="hint">Reconnu : {{ detected }}</p>
          <div class="inputs" role="listbox" aria-label="Entrées placées">
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
            <p v-if="!keys.length" class="hint">Aucune entrée : glisse « ＋ Entrée » sur l'image, ou N puis clic.</p>
          </div>
        </section>

        <section v-if="editor.selection" class="block">
          <span class="eyebrow">Entrée sélectionnée</span>
          <Select
            v-model="selectedKey"
            :options="catalog"
            option-label="label"
            option-value="value"
            option-group-label="label"
            option-group-children="items"
            filter
            size="small"
            aria-label="Entrée DCS"
          />
          <div class="row-buttons">
            <Button size="small" severity="secondary" :label="draft.inputs[editor.selection.key]?.anchor ? 'Sans repère' : 'Avec repère'" @click="toggleAnchor" />
            <Button size="small" severity="secondary" label="2e case" v-tooltip.bottom="'La même entrée dessinée à un autre endroit'" @click="addExtraBox" />
            <Button size="small" severity="secondary" label="Dupliquer" @click="duplicateSelected" />
            <Button size="small" severity="danger" text label="Supprimer" @click="removeSelected" />
          </div>
        </section>

        <section class="block">
          <span class="eyebrow">Partage</span>
          <div class="row-buttons">
            <Button size="small" severity="secondary" icon="pi pi-download" label="Importer…" @click="importInput?.click()" />
            <a v-if="draft.id && !editor.dirty && !draft.overrides" class="p-button p-button-sm p-button-secondary link-button" :href="api.templateFileUrl(draft.id)" download>Exporter</a>
            <Button v-if="savedUserTemplate" size="small" severity="danger" text label="Supprimer le gabarit" @click="deleteTemplate" />
          </div>
          <input ref="importInput" type="file" accept=".zip" hidden @change="onImportPicked" />
        </section>

        <section class="block keys-help">
          <span class="eyebrow">Raccourcis</span>
          <div v-for="[k, label] in SHORTCUTS" :key="k"><kbd>{{ k }}</kbd> {{ label }}</div>
        </section>
      </aside>

      <main ref="canvasBox" class="stage" :class="{ dropping: draggingFile }">
        <div v-if="!draft.image" class="dropzone" @click="fileInput?.click()">
          <i class="pi pi-image" />
          <p>Glisse ici une photo ou un dessin du périphérique (PNG, JPG, SVG), ou clique pour en choisir un.</p>
          <p class="hint">Ou pars d'un gabarit existant, à gauche, pour le corriger.</p>
        </div>
        <template v-else-if="mode === 'edit'">
          <EditorCanvas :placing="placing" @placed="placing = null" />
        </template>
        <div v-else class="preview">
          <Select v-model="previewOf" :options="previewDevices" option-label="label" option-value="value" filter size="small" placeholder="Liaisons de…" class="preview-select" aria-label="Liaisons à montrer" />
          <div v-if="previewSvg" class="paper" v-html="previewSvg" />
          <p v-else class="hint">Choisis un module et un périphérique pour voir le gabarit avec ses liaisons.</p>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.editor { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.ebar { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-bottom: 1px solid var(--line); background: var(--panel-2); flex-wrap: wrap; }
.ebar .name { width: 280px; max-width: 40vw; }
.ebar kbd { background: transparent; border-color: currentColor; color: inherit; opacity: 0.7; margin-left: 8px; }
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
