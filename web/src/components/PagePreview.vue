<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'
import { loadTemplate, useStore } from '../lib/store'
import { editor, fromTemplate, newDraft, open } from '../editor/state'
import type { Page } from '../render/page'
import type { LayerMode } from '../lib/types'

const store = useStore()
const { state } = store
const pages = ref<Page[]>([])
const error = ref('')
const rendering = ref(false)

const layerModes = [
  { label: 'Sur la même page', value: 'merge' },
  { label: 'Une page par calque', value: 'split' },
]

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
  () => [store.device.value, store.profile.value?.name, templateId.value, layerMode.value] as const,
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
      </div>
      <span
        v-if="unchecked"
        class="pill warn"
        v-tooltip.bottom="UNCHECKED_HINT"
      >numérotation non vérifiée</span>
      <div v-if="store.device.value" class="controls">
        <label class="ctl">
          <span class="eyebrow">Gabarit<template v-if="automatic && templateId !== NO_TEMPLATE"> (auto)</template></span>
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
          :label="templateId === NO_TEMPLATE ? 'Créer un gabarit' : 'Modifier le gabarit'"
          @click="editTemplate"
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
    </header>
    <div class="stage">
      <ProgressSpinner v-if="rendering && !pages.length" style="width: 40px; height: 40px" />
      <p v-if="error" class="stage-error">Page impossible à construire : {{ error }}</p>
      <figure v-for="(page, i) in pages" :key="i" class="sheet">
        <figcaption v-if="pages.length > 1">{{ page.title }}</figcaption>
        <div class="paper" v-html="page.svg" />
      </figure>
    </div>
  </section>
</template>

<style scoped>
.page-col { background: var(--panel); }
.pagehead { padding: 10px 14px; display: flex; align-items: flex-end; gap: 12px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.title { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1 1 260px; }
.title h2 { font-size: 22px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.controls { display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-end; }
.ctl { display: flex; flex-direction: column; gap: 4px; }
.tpl-select { width: 260px; max-width: 100%; }
.stage {
  flex: 1; overflow: auto; padding: 18px; display: flex; flex-direction: column; align-items: center; gap: 18px;
  background: repeating-linear-gradient(45deg, transparent 0 10px, color-mix(in srgb, var(--panel-3) 35%, transparent) 10px 11px);
}
.sheet { margin: 0; width: 100%; max-width: 720px; display: flex; flex-direction: column; gap: 6px; }
.sheet figcaption { font-size: 12px; color: var(--ink-3); }
.paper { background: #fff; border-radius: 3px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); overflow: hidden; }
.paper :deep(svg) { display: block; width: 100%; height: auto; }
.stage-error { color: var(--bad); }
</style>
