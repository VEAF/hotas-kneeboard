<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { StorageSerializers, useElementSize, useLocalStorage } from '@vueuse/core'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'
import { loadTemplate, useStore } from '../lib/store'
import { editor, fromTemplate, newDraft, open } from '../editor/state'
import type { Page } from '../render/page'
import type { LayerMode } from '../lib/types'
import OtherProgramsDialog from './OtherProgramsDialog.vue'

const programsOpen = ref(false)

const store = useStore()
const { state } = store
const pages = ref<Page[]>([])
const error = ref('')
const rendering = ref(false)

const layerModes = [
  { label: 'Même page', value: 'merge' },
  { label: 'Par calque', value: 'split' },
]

// --- zoom: the page fits the space it has, unless the user zooms -------------------------------
const stage = ref<HTMLElement | null>(null)
const { width: stageWidth, height: stageHeight } = useElementSize(stage)
type Zoom = 'fit' | 'width' | number
// JSON: a zoom factor must come back as a number, not as the text of one
const zoom = useLocalStorage<Zoom>('hotas-kneeboard-zoom', 'fit', { serializer: StorageSerializers.object })
const CAPTION = 22
const zoomModes = [
  { icon: 'pi pi-arrows-alt', value: 'fit', tip: 'Page entière' },
  { icon: 'pi pi-arrows-h', value: 'width', tip: 'Toute la largeur' },
]
const zoomMode = computed({
  get: () => (typeof zoom.value === 'number' ? null : zoom.value),
  set: (value) => value && (zoom.value = value),
})

const GAP = 18
// side by side only if the pages lose less than this of their size compared to one per row
const SIDE_BY_SIDE_KEEPS = 0.85
// "full width", two per row: from this width on
const MIN_HALF_WIDTH = 400

/** Room for the pages (useElementSize gives the stage's content box: padding already out) */
function space(): { width: number; height: number } {
  return {
    width: Math.max(120, stageWidth.value),
    height: Math.max(120, stageHeight.value - (pages.value.length > 1 ? CAPTION : 0)),
  }
}

/** Pages side by side, two per row (the two halves of a wide drawing), when there is room for it */
const columns = computed(() => {
  if (pages.value.length < 2 || typeof zoom.value === 'number') return 1
  const { width, height } = space()
  const half = (width - GAP) / 2
  if (zoom.value === 'width') return half >= MIN_HALF_WIDTH ? 2 : 1
  const fit = (w: number, p: Page) => Math.min(w, (height * p.width) / p.height)
  return pages.value.every((p) => fit(half, p) >= SIDE_BY_SIDE_KEEPS * fit(width, p)) ? 2 : 1
})

/** Width of a page on screen, in pixels */
function sheetWidth(page: Page): number {
  const { height } = space()
  const width = (space().width - GAP * (columns.value - 1)) / columns.value
  if (zoom.value === 'width') return width
  if (zoom.value === 'fit') return Math.min(width, (height * page.width) / page.height)
  return page.width * zoom.value
}

function zoomBy(factor: number) {
  const first = pages.value[0]
  if (!first) return
  const current = sheetWidth(first) / first.width
  zoom.value = Math.min(4, Math.max(0.2, current * factor))
}

function onWheel(event: WheelEvent) {
  if (!event.ctrlKey) return
  event.preventDefault()
  zoomBy(event.deltaY < 0 ? 1.1 : 1 / 1.1)
}
const zoomLabel = computed(() => {
  const first = pages.value[0]
  return first ? `${Math.round((sheetWidth(first) / first.width) * 100)} %` : ''
})

// PrimeVue's Select shows an empty string as "nothing selected": "no template" needs a value
const NO_TEMPLATE = '-'
const templateOptions = computed(() => [
  { label: 'Aucun : page liste', value: NO_TEMPLATE },
  ...[...state.templates].sort((a, b) => a.name.localeCompare(b.name)).map((t) => ({ label: t.name, value: t.id })),
])

const templateId = computed({
  get: () => (store.device.value ? (store.templateIdFor(store.device.value) ?? NO_TEMPLATE) : NO_TEMPLATE),
  set: (value: string) => store.device.value && store.setTemplate(store.device.value, value === NO_TEMPLATE ? null : value),
})

const layerMode = computed({
  get: () => state.settings?.layer_mode ?? 'merge',
  set: (value: LayerMode) => value && store.changeSettings({ layer_mode: value }),
})

const UNCHECKED_HINT =
  "La numérotation de ce gabarit n'a pas encore été vérifiée sur le vrai périphérique : une commande peut tomber sur la mauvaise case. Modifier le gabarit, puis « Vérifier » : appuie sur chaque bouton."
/** A library template whose numbering nobody checked on the real device yet */
const unchecked = computed(() => {
  const summary = state.templates.find((t) => t.id === templateId.value)
  // a user's version in front of a bundled template is still unchecked unless marked so
  return !!summary && (!summary.user || !!summary.replaces_bundled) && !summary.checked
})

const automatic = computed(() => {
  const d = store.device.value
  return !!d && state.settings?.device_templates[d.name] === undefined
})

/** The editor, on this device's template (or a new one for it) */
async function editTemplate() {
  const d = store.device.value
  const p = store.profile.value
  if (!d || !p) return
  editor.forDevice = { profile: p.name, deviceKey: d.full_name, name: d.name }
  const id = store.templateIdFor(d)
  if (id) {
    const loaded = await loadTemplate(id)
    const user = !!state.templates.find((t) => t.id === id)?.user
    open(fromTemplate(loaded.data, loaded.image, user, d.name))
  } else {
    open(newDraft({ name: d.name, devices: [d.name] }))
  }
  state.view = 'editor'
}

let generation = 0
watch(
  () =>
    [
      store.device.value,
      store.profile.value?.name,
      templateId.value,
      layerMode.value,
      state.settings?.split_wide,
      // other programs: what is read, and the user's choices about them
      state.programs,
      JSON.stringify([
        state.settings?.srs_profiles,
        state.settings?.program_bindings,
        state.settings?.hidden_programs,
        state.settings?.program_colors,
      ]),
    ] as const,
  async ([d, profileName]) => {
    const current = ++generation
    error.value = ''
    if (!d || !profileName) {
      pages.value = []
      return
    }
    rendering.value = true
    try {
      const result = await store.pagesOf(profileName, d)
      if (current === generation) pages.value = result
    } catch (e) {
      if (current === generation) error.value = (e as Error).message
    } finally {
      if (current === generation) rendering.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <section class="col page-col" aria-label="Page">
    <header class="pagehead">
      <div class="title">
        <h2>{{ store.device.value?.name ?? 'Aucun périphérique' }}</h2>
        <span v-if="store.device.value?.source === 'diff'" class="pill warn" v-tooltip.bottom="'Seules les modifications enregistrées dans Saved Games sont connues : défauts du module absents.'">
          {{ store.device.value.error === 'module not installed' ? 'module non installé' : 'pas de profil de base' }}
        </span>
        <span
          v-else-if="store.device.value?.error === 'path too long'"
          class="pill warn"
          v-tooltip.bottom="'Le chemin de son fichier de commandes dépasse 260 caractères : l\'interpréteur de DCS ne peut pas le lire, la page montre les défauts du module. Un dossier Saved Games plus court règle le problème.'"
        >chemin trop long</span>
        <span
          v-if="unchecked"
          class="pill warn"
          v-tooltip.bottom="UNCHECKED_HINT"
        >numérotation non vérifiée</span>
      </div>
      <div v-if="store.device.value" class="controls">
        <label class="ctl">
          <span class="eyebrow">Gabarit<template v-if="automatic && templateId !== NO_TEMPLATE"> auto</template></span>
          <Select
            v-model="templateId"
            :options="templateOptions"
            option-label="label"
            option-value="value"
            filter
            size="small"
            class="tpl-select"
            aria-label="Gabarit du périphérique"
          />
        </label>
        <Button
          size="small"
          severity="secondary"
          icon="pi pi-pencil"
          :label="templateId === NO_TEMPLATE ? 'Créer' : 'Modifier'"
          v-tooltip.bottom="templateId === NO_TEMPLATE ? 'Créer un gabarit pour ce périphérique' : 'Modifier le gabarit dans l\'éditeur'"
          @click="editTemplate"
        />
        <Button
          size="small"
          severity="secondary"
          icon="pi pi-th-large"
          label="Autres logiciels"
          v-tooltip.bottom="'Boutons utilisés par SRS, VectorXR ou un logiciel saisi à la main'"
          @click="programsOpen = true"
        />
        <label class="ctl">
          <span class="eyebrow">Calques</span>
          <SelectButton
            v-model="layerMode"
            :options="layerModes"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            size="small"
            aria-label="Affichage des calques"
          />
        </label>
      </div>
      <OtherProgramsDialog v-model:visible="programsOpen" />
    </header>
    <div class="stage-wrap">
      <div ref="stage" class="stage" :class="{ single: pages.length === 1, paired: columns === 2 }" @wheel="onWheel">
        <ProgressSpinner v-if="rendering && !pages.length" style="width: 40px; height: 40px" />
        <p v-if="error" class="stage-error">Page impossible à construire : {{ error }}</p>
        <figure v-for="(page, i) in pages" :key="i" class="sheet" :style="{ width: `${sheetWidth(page)}px` }">
          <figcaption v-if="pages.length > 1">{{ page.title }}</figcaption>
          <div class="paper" v-html="page.svg" />
        </figure>
      </div>
      <div v-if="pages.length" class="zoom" role="group" aria-label="Zoom">
        <SelectButton v-model="zoomMode" :options="zoomModes" option-value="value" data-key="value" size="small" :allow-empty="false" aria-label="Ajustement de la page">
          <template #option="{ option }">
            <i :class="option.icon" v-tooltip.top="option.tip" :aria-label="option.tip" />
          </template>
        </SelectButton>
        <Button size="small" text icon="pi pi-minus" aria-label="Zoom arrière" v-tooltip.top="'Zoom arrière (Ctrl+molette)'" @click="zoomBy(1 / 1.2)" />
        <span class="zoom-value">{{ zoomLabel }}</span>
        <Button size="small" text icon="pi pi-plus" aria-label="Zoom avant" v-tooltip.top="'Zoom avant (Ctrl+molette)'" @click="zoomBy(1.2)" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.page-col { background: var(--panel); }
.pagehead { padding: 8px 14px; display: flex; align-items: flex-end; gap: 8px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.title { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1 1 200px; align-self: center; }
.title h2 { font-size: 22px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.controls { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
.ctl { display: flex; flex-direction: column; gap: 3px; }
.tpl-select { width: 230px; max-width: 100%; }
.stage-wrap { flex: 1; min-height: 0; position: relative; display: flex; }
.stage-wrap > .stage { flex: 1; }
/* floating over the page, bottom right: takes no height from it */
.zoom {
  position: absolute; right: 14px; bottom: 12px; display: flex; align-items: center; gap: 2px; padding: 4px;
  background: color-mix(in srgb, var(--panel-2) 92%, transparent); border: 1px solid var(--line); border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
}
.zoom-value { font: 600 12px var(--f-mono); color: var(--ink-2); min-width: 44px; text-align: center; font-variant-numeric: tabular-nums; }
.stage {
  min-height: 0; overflow: auto; padding: 16px; display: flex; flex-direction: column; align-items: safe center; gap: 18px;
  background: repeating-linear-gradient(45deg, transparent 0 10px, color-mix(in srgb, var(--panel-3) 35%, transparent) 10px 11px);
}
/* one page: centred both ways when it is smaller than the space */
.stage.single { justify-content: safe center; }
/* two pages per row: the halves of a wide drawing next to each other, as on paper */
.stage.paired { flex-direction: row; flex-wrap: wrap; justify-content: center; align-content: safe center; align-items: flex-start; }
.sheet { margin: 0; flex: none; display: flex; flex-direction: column; gap: 6px; }
.sheet figcaption { font-size: 12px; color: var(--ink-3); }
.paper { background: #fff; border-radius: 3px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); overflow: hidden; }
.paper :deep(svg) { display: block; width: 100%; height: auto; }
.stage-error { color: var(--bad); }
</style>
