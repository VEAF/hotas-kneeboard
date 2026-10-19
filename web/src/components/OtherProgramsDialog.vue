<script setup lang="ts">
// Buttons of this device that other programs use: SRS's profile for the module, what SRS and
// VectorXR read, and the entries made by hand (VoiceAttack, OpenKneeboard…), which are edited here.

import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { loadTemplate, useStore } from '../lib/store'
import { compareInputs, inputName } from '../render/inputs'
import { normalizeGuid } from '../render/programs'
import { detectInput, gamepadSupported } from '../editor/gamepad'
import type { ManualProgramBinding } from '../lib/types'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const { state } = store

const device = computed(() => store.device.value)
const profileName = computed(() => store.profile.value?.name ?? '')
const guid = computed(() => (device.value ? normalizeGuid(device.value.guid) : ''))

// --- SRS profile of the module ------------------------------------------------------------------
const AUTO = '__auto__'
const NONE = '__none__'
const srsOptions = computed(() => {
  const matched = state.programs?.srs.matched[profileName.value]
  return [
    { label: `Selon le nom du module${matched ? ` (${matched})` : ' (aucun)'}`, value: AUTO },
    { label: 'Aucun : pas de SRS sur ces pages', value: NONE },
    ...(state.programs?.srs.profiles ?? []).map((p) => ({ label: p, value: p })),
  ]
})
const srsChoice = computed({
  get: () => {
    const chosen = state.settings?.srs_profiles[profileName.value]
    return chosen === undefined ? AUTO : chosen === '' ? NONE : chosen
  },
  set: (value: string) => store.setSrsProfile(profileName.value, value === AUTO ? undefined : value === NONE ? null : value),
})

// --- what lands on this device ------------------------------------------------------------------
const manual = computed(() => state.settings?.program_bindings ?? [])
const read = computed(() =>
  store
    .readProgramBindings(profileName.value)
    .filter((b) => normalizeGuid(b.device_guid) === guid.value)
    .sort((a, b) => compareInputs(a.input, b.input)),
)
const mine = computed(() =>
  manual.value
    .map((b, index) => ({ ...b, index }))
    .filter((b) => normalizeGuid(b.device_guid) === guid.value)
    .sort((a, b) => compareInputs(a.input, b.input)),
)

// --- entry by hand -----------------------------------------------------------------------------
const editing = ref<number | null>(null) // index in program_bindings; null: a new entry
const form = ref({ program: '', input: '', action: '' })
const error = ref('')
const templateInputs = ref<string[]>([])

watch(
  () => [visible.value, device.value] as const,
  async ([open, d]) => {
    if (!open || !d) return
    reset()
    const id = store.templateIdFor(d)
    templateInputs.value = id ? Object.keys((await loadTemplate(id)).data.inputs) : []
  },
  { immediate: true },
)

const inputOptions = computed(() => {
  const keys = new Set([...templateInputs.value, ...Object.keys(device.value?.inputs ?? {})])
  return [...keys].sort(compareInputs).map((key) => ({ label: `${inputName(key)} (${key})`, value: key }))
})

function reset() {
  editing.value = null
  form.value = { program: '', input: '', action: '' }
  error.value = ''
  stopListening()
}

function edit(index: number) {
  const entry = manual.value[index]
  editing.value = index
  form.value = { program: entry.program, input: entry.input, action: entry.action }
  error.value = ''
}

function remove(index: number) {
  store.setManualBindings(manual.value.filter((_, i) => i !== index))
  // the entry being edited moves up when one before it goes
  if (editing.value === index) reset()
  else if (editing.value !== null && editing.value > index) editing.value -= 1
}

function save() {
  const d = device.value
  if (!d) return
  const entry: ManualProgramBinding = {
    program: form.value.program.trim(),
    device_guid: guid.value,
    device_name: d.name,
    input: form.value.input.trim(),
    action: form.value.action.trim(),
  }
  if (!entry.program || !entry.action) {
    error.value = 'Indique le logiciel et ce que fait le bouton.'
    return
  }
  if (!/^JOY_[A-Z0-9_]+$/.test(entry.input)) {
    error.value = 'Choisis le bouton dans la liste, ou appuie dessus avec « Identifier ».'
    return
  }
  const list = [...manual.value]
  if (editing.value === null) list.push(entry)
  else list[editing.value] = entry
  store.setManualBindings(list)
  reset()
}

// --- "press the button" ------------------------------------------------------------------------
const listening = ref<AbortController | null>(null)
const heard = ref('')

async function identify() {
  stopListening()
  const controller = new AbortController()
  listening.value = controller
  heard.value = 'Appuie sur le bouton…'
  try {
    const found = await detectInput(controller.signal, (name) => (heard.value = `${name} vient d'apparaître : appuie à nouveau.`))
    form.value.input = found.key
    heard.value = `${inputName(found.key)} sur ${found.device}`
  } catch (e) {
    if ((e as Error).name !== 'AbortError') heard.value = (e as Error).message
  } finally {
    if (listening.value === controller) listening.value = null
  }
}

function stopListening() {
  listening.value?.abort()
  listening.value = null
  heard.value = ''
}
onBeforeUnmount(stopListening)
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Autres logiciels sur ce périphérique" :style="{ width: 'min(700px, 94vw)' }" @hide="reset">
    <div class="form">
      <p class="intro">
        Les boutons que d'autres logiciels utilisent s'affichent sur les pages à côté des commandes DCS, chacun dans sa couleur.
        SRS et VectorXR sont lus directement ; les autres se saisissent ici.
      </p>

      <label class="field" for="srs-profile">
        <span class="eyebrow">Profil SRS pour {{ store.profile.value?.display_name ?? profileName }}</span>
        <Select v-if="state.programs?.srs.profiles.length" input-id="srs-profile" v-model="srsChoice" :options="srsOptions" option-label="label" option-value="value" />
        <small v-else>SRS introuvable : indique son dossier dans les réglages, onglet « Autres logiciels ».</small>
      </label>

      <section>
        <h3 class="eyebrow">Lus dans SRS et VectorXR</h3>
        <ul v-if="read.length" class="rows">
          <li v-for="(b, i) in read" :key="i">
            <span class="tag" :style="{ background: store.programStyles.value.get(b.program)?.color }">{{ store.programStyles.value.get(b.program)?.tag }}</span>
            <span class="input">{{ inputName(b.input) }}</span>
            <span class="action">{{ b.action }}</span>
          </li>
        </ul>
        <p v-else class="intro">Rien sur ce périphérique.</p>
      </section>

      <section>
        <h3 class="eyebrow">Saisis à la main</h3>
        <ul v-if="mine.length" class="rows">
          <li v-for="b in mine" :key="b.index" :class="{ current: editing === b.index }">
            <span class="tag" :style="{ background: store.programStyles.value.get(b.program)?.color }">{{ store.programStyles.value.get(b.program)?.tag }}</span>
            <span class="input">{{ inputName(b.input) }}</span>
            <span class="action">{{ b.program }} · {{ b.action }}</span>
            <Button size="small" text icon="pi pi-pencil" aria-label="Modifier" @click="edit(b.index)" />
            <Button size="small" text severity="danger" icon="pi pi-trash" aria-label="Supprimer" @click="remove(b.index)" />
          </li>
        </ul>

        <form class="entry" @submit.prevent="save">
          <label class="field">
            <span class="eyebrow">Logiciel</span>
            <InputText v-model="form.program" list="known-programs" placeholder="VoiceAttack" size="small" />
            <datalist id="known-programs">
              <option v-for="p in store.programNames.value" :key="p" :value="p" />
            </datalist>
          </label>
          <label class="field">
            <span class="eyebrow">Bouton</span>
            <div class="with-button">
              <Select v-model="form.input" :options="inputOptions" option-label="label" option-value="value" editable size="small" class="input-select" placeholder="JOY_BTN…" />
              <Button
                v-if="gamepadSupported()"
                size="small"
                severity="secondary"
                :icon="listening ? 'pi pi-stop' : 'pi pi-bullseye'"
                :label="listening ? 'Arrêter' : 'Identifier'"
                @click="listening ? stopListening() : identify()"
              />
            </div>
            <small v-if="heard">{{ heard }}</small>
          </label>
          <label class="field">
            <span class="eyebrow">Action</span>
            <InputText v-model="form.action" placeholder="Écoute micro" size="small" />
          </label>
          <p v-if="error" class="error">{{ error }}</p>
          <div class="actions">
            <Button v-if="editing !== null" type="button" size="small" text label="Annuler" @click="reset" />
            <Button type="submit" size="small" :icon="editing === null ? 'pi pi-plus' : 'pi pi-check'" :label="editing === null ? 'Ajouter' : 'Enregistrer'" />
          </div>
        </form>
      </section>
    </div>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field small, .intro { color: var(--ink-3); font-size: 13px; margin: 0; }
h3 { margin: 0 0 6px; }
.rows { list-style: none; margin: 0; padding: 0; border: 1px solid var(--line); border-radius: 6px; }
.rows li { display: grid; grid-template-columns: 44px 90px minmax(0, 1fr) auto auto; gap: 10px; align-items: center; padding: 5px 10px; border-bottom: 1px solid var(--line); }
.rows li:last-child { border-bottom: 0; }
.rows li.current { background: var(--panel-3); }
.tag { color: #fff; font: 700 11px var(--f-mono); text-align: center; border-radius: 3px; padding: 1px 4px; }
.input { color: var(--ink-2); font-size: 13px; }
.action { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.entry { display: grid; grid-template-columns: 1fr 1.4fr 1.4fr; gap: 10px; align-items: start; margin-top: 10px; }
.entry .error, .entry .actions { grid-column: 1 / -1; }
.with-button { display: flex; gap: 6px; }
.input-select { flex: 1; min-width: 0; }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.error { color: var(--bad); margin: 0; }
@media (max-width: 560px) { .entry { grid-template-columns: 1fr; } }
</style>
