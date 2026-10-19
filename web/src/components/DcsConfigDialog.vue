<script setup lang="ts">
// Changes to DCS's own controls files (Saved Games\DCS\Config\Input): devices disabled in DCS,
// devices DCS no longer sees, modifiers on a renamed device, the generic hat views and the buttons of a
// device without any removed in bulk, and the backups made before
// each change, listed and restorable.

import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { api } from '../lib/api'
import { useStore } from '../lib/store'
import type {
  DcsBackupsResponse,
  DcsDevicesResponse,
  GenericButtonsDevice,
  GenericButtonsPreview,
  HatViewsDevice,
  HatViewsPreview,
  HatViewsResult,
  ModifiersResponse,
} from '../lib/types'
import { lang, t, tn } from '../lib/i18n'
import Tr from './Tr'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const toast = useToast()

const data = ref<DcsBackupsResponse | null>(null)
const error = ref('')
const working = ref('') // '' | 'backup' | id of the backup being restored
const confirming = ref<string | null>(null)

const devices = ref<DcsDevicesResponse | null>(null)

const devicesError = ref('')
const modifiers = ref<ModifiersResponse | null>(null)
const modifiersError = ref('')

async function load() {
  error.value = ''
  devicesError.value = ''
  modifiersError.value = ''
  // apart: an unreadable disabled.lua must not hide the backups that can repair it
  await Promise.all([
    api.dcsBackups().then((r) => (data.value = r)).catch((e) => (error.value = (e as Error).message)),
    api.dcsDevices().then((r) => (devices.value = r)).catch((e) => (devicesError.value = (e as Error).message)),
    api.modifiers().then((r) => (modifiers.value = r)).catch((e) => (modifiersError.value = (e as Error).message)),
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
    forgetHatPreview()
    toast.add({ severity: 'success', summary: disabled ? t('dcs.devices.disabled_done') : t('dcs.devices.enabled_done'), detail: fullName, life: 4000 })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.change_failed'), detail: (e as Error).message, life: 10000 })
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
    forgetHatPreview()
    toast.add({ severity: 'success', summary: t('dcs.forget.done'), detail: t('dcs.forget.detail', { device, modules: result.profiles.join(', ') }), life: 6000 })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: t('editor.delete.failed'), detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

// --- modifiers DCS drops because their device was renamed by its driver ---------------------------
const fixable = computed(() => (modifiers.value?.issues ?? []).filter((i) => i.new_device))
const deviceName = (fullName: string) => fullName.replace(/\s*\{[^}]*\}$/, '')

async function changeModifiers(what: string, call: () => Promise<{ fixed: unknown[] }>, done: string) {
  working.value = what
  try {
    const result = await call()
    toast.add({ severity: 'success', summary: done, detail: tn('dcs.modifiers.renamed', result.fixed.length), life: 6000 })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.change_failed'), detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

const fixModifiers = () => changeModifiers('modifiers', api.fixModifiers, t('dcs.modifiers.fixed'))
const restoreModifiers = (profile: string, backup: string) =>
  changeModifiers(`modifiers:${profile}`, () => api.restoreModifiers(profile, backup), t('dcs.modifiers.restored', { profile }))

// --- the 8 generic hat views, removed in bulk ------------------------------------------------------
// computed on demand: reading every module takes a few seconds
const hat = ref<HatViewsPreview | null>(null)
const hatError = ref('')
const hatLoading = ref(false)
const everyDevice = ref(false)
const allModules = ref(false)
const hatChosen = ref<Set<string>>(new Set())
const hatConfirming = ref(false)
const hatResult = ref<HatViewsResult | null>(null)

const hatSelectable = (d: HatViewsDevice) => everyDevice.value || d.hat_only_views
const hatOk = (d: HatViewsDevice) => d.modules.filter((m) => !m.error)

async function loadHat() {
  hatLoading.value = true
  hatError.value = ''
  hatConfirming.value = false
  try {
    hat.value = await api.hatViews(allModules.value)
    resetHatChoice()
  } catch (e) {
    hat.value = null
    hatError.value = (e as Error).message
  } finally {
    hatLoading.value = false
  }
}

function resetHatChoice() {
  hatChosen.value = new Set((hat.value?.devices ?? []).filter(hatSelectable).map((d) => d.device))
}

function toggleHat(device: string, on: boolean) {
  const next = new Set(hatChosen.value)
  if (on) next.add(device)
  else next.delete(device)
  hatChosen.value = next
}

watch(allModules, () => {
  if (hat.value) loadHat()
})
// the option adds or removes the devices it concerns, the user's other choices stay
watch(everyDevice, (every) => {
  const next = new Set(hatChosen.value)
  for (const d of hat.value?.devices ?? []) {
    if (d.hat_only_views) continue
    if (every) next.add(d.device)
    else next.delete(d.device)
  }
  hatChosen.value = next
})

const hatTodo = computed(() => (hat.value?.devices ?? []).filter((d) => hatSelectable(d) && hatChosen.value.has(d.device)))
const hatTotals = computed(() => {
  const modules = hatTodo.value.flatMap(hatOk)
  return {
    views: modules.reduce((n, m) => n + m.views.length, 0),
    files: modules.length,
    created: modules.filter((m) => m.new_file).length,
  }
})
const hatSummary = (d: HatViewsDevice) => {
  const ok = hatOk(d)
  const created = ok.filter((m) => m.new_file).length
  return (
    t('dcs.in', { what: tn('dcs.views', ok.reduce((n, m) => n + m.views.length, 0)), where: tn('settings.devices.modules', ok.length) }) +
    (created ? ` (${tn('dcs.new_files', created)})` : '')
  )
}

/** What the server did, against the preview the user confirmed: a module of the preview not
 * written, or written with another count, is a difference too */
function comparedWithPreview(result: HatViewsResult, shown: HatViewsDevice[]): HatViewsResult {
  const differences = [...result.differences]
  const written = new Map(result.written.map((w) => [`${w.profile}\t${w.device.toLowerCase()}`, w]))
  for (const d of shown) {
    for (const m of hatOk(d)) {
      const w = written.get(`${m.profile}\t${m.file.toLowerCase()}`)
      if (!w) differences.push(t('dcs.hat.not_written', { file: m.file, profile: m.profile }))
      else if (w.removed !== m.views.length && w.removed === w.expected)
        differences.push(t('dcs.hat.other_count', { file: m.file, profile: m.profile, removed: w.removed, preview: m.views.length }))
    }
  }
  return { ...result, differences }
}

/** The preview no longer says what the files hold: it must be computed again */
function forgetHatPreview() {
  hat.value = null
  hatConfirming.value = false
}

async function removeHat() {
  hatConfirming.value = false
  working.value = 'hat'
  const shown = hatTodo.value
  try {
    const result = comparedWithPreview(
      await api.removeHatViews(shown.map((d) => d.device), everyDevice.value, allModules.value),
      shown,
    )
    hatResult.value = result
    const removed = result.written.reduce((n, w) => n + w.removed, 0)
    const files = result.written.filter((w) => w.removed > 0).length
    const differ = result.differences.length > 0
    toast.add({
      severity: differ ? 'warn' : 'success',
      summary: differ ? t('dcs.hat.done_differ') : t('dcs.hat.done'),
      detail: t('dcs.in', { what: tn('dcs.views_removed', removed), where: tn('dcs.files', files) }) + (differ ? t('dcs.see_window') : t('dcs.as_previewed')),
      life: 8000,
    })
    await Promise.all([load(), store.load(true), loadHat()])
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.remove_failed'), detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

// --- devices without any button (pedals): the buttons DCS gives them, removed in bulk -----------
// the user marks them (DCS writes nowhere how many buttons a device has); the preview is on demand
const deviceNames = computed(() => [...new Set(knownDevices.value.map((d) => d.name))].sort((a, b) => a.localeCompare(b)))
const isButtonless = (name: string) => !!store.state.settings?.buttonless_devices.some((d) => d.toLowerCase() === name.toLowerCase())
const generic = ref<GenericButtonsPreview | null>(null)
const genericError = ref('')
const genericLoading = ref(false)
const genericAllModules = ref(false)
const genericConfirming = ref(false)
const genericResult = ref<HatViewsResult | null>(null)

function setButtonless(name: string, on: boolean) {
  const others = (store.state.settings?.buttonless_devices ?? []).filter((d) => d.toLowerCase() !== name.toLowerCase())
  store.changeSettings({ buttonless_devices: on ? [...others, name] : others })
  generic.value = null
  genericConfirming.value = false
}

async function loadGeneric() {
  genericLoading.value = true
  genericError.value = ''
  genericConfirming.value = false
  try {
    await store.flushSettings()
    generic.value = await api.genericButtons(genericAllModules.value)
  } catch (e) {
    generic.value = null
    genericError.value = (e as Error).message
  } finally {
    genericLoading.value = false
  }
}
watch(genericAllModules, () => {
  if (generic.value) loadGeneric()
})

const genericOk = (d: GenericButtonsDevice) => d.modules.filter((m) => !m.error)
const genericTotals = computed(() => {
  const modules = (generic.value?.devices ?? []).flatMap(genericOk)
  return {
    buttons: modules.reduce((n, m) => n + m.bindings.length, 0),
    files: modules.length,
    created: modules.filter((m) => m.new_file).length,
  }
})

async function removeGeneric() {
  genericConfirming.value = false
  working.value = 'generic'
  try {
    await store.flushSettings()
    const result = await api.removeGenericButtons(genericAllModules.value)
    genericResult.value = result
    const removed = result.written.reduce((n, w) => n + w.removed, 0)
    const differ = result.differences.length > 0
    toast.add({
      severity: differ ? 'warn' : 'success',
      summary: differ ? t('dcs.generic.done_differ') : t('dcs.generic.done'),
      detail: tn('dcs.bindings_removed', removed) + (differ ? t('dcs.see_window') : t('dcs.as_previewed')),
      life: 8000,
    })
    forgetHatPreview()
    await Promise.all([load(), store.load(true), loadGeneric()])
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.remove_failed'), detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

async function undoGeneric() {
  if (!genericResult.value) return
  const id = genericResult.value.backup.id
  working.value = id
  try {
    await api.restoreDcsBackup(id)
    genericResult.value = null
    toast.add({ severity: 'success', summary: t('dcs.undo.done'), detail: t('dcs.undo.detail'), life: 5000 })
    forgetHatPreview()
    await Promise.all([load(), store.load(true), loadGeneric()])
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.undo.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    working.value = ''
  }
}

watch(visible, (open) => {
  confirming.value = null
  forgetting.value = null
  hatResult.value = null
  genericResult.value = null
  generic.value = null
  forgetHatPreview()
  if (open) load()
})

const date = (iso: string) =>
  new Date(iso).toLocaleString(lang.value === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'short', timeStyle: 'medium' })
const size = (bytes: number) =>
  bytes < 1024 * 1024 ? t('dcs.size.kb', { n: Math.max(1, Math.round(bytes / 1024)) }) : t('dcs.size.mb', { n: (bytes / 1024 / 1024).toFixed(1) })

async function backupNow() {
  working.value = 'backup'
  try {
    const backup = await api.createDcsBackup()
    toast.add({ severity: 'success', summary: t('dcs.backup.done'), detail: `${tn('dcs.files', backup.files)}, ${size(backup.size)}`, life: 4000 })
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.backup.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    working.value = ''
  }
}

async function restore(id: string) {
  confirming.value = null
  working.value = id
  try {
    await api.restoreDcsBackup(id)
    forgetHatPreview()
    hatResult.value = null
    toast.add({
      severity: 'success',
      summary: t('dcs.restore.done'),
      detail: t('dcs.restore.detail'),
      life: 6000,
    })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.restore.failed'), detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('dcs.title')" :style="{ width: 'min(720px, 94vw)' }">
    <div class="body">
      <p class="intro">
        <Tr k="dcs.intro"><template #folder><code>Saved Games\DCS\Config\Input</code></template></Tr>
      </p>

      <p v-if="data?.dcs_running" class="warn" role="alert">
        <i class="pi pi-exclamation-triangle" /> {{ t('dcs.running') }}
      </p>
      <p v-else-if="data && data.dcs_running === null" class="warn" role="alert">
        <i class="pi pi-exclamation-triangle" /> {{ t('dcs.running_unknown') }}
      </p>
      <p v-if="error" class="warn" role="alert">{{ error }}</p>

      <p v-if="devicesError" class="warn" role="alert">{{ t('dcs.devices.unreadable', { error: devicesError }) }}</p>
      <section v-if="devices">
        <h3 class="eyebrow">{{ t('dcs.devices.title') }}</h3>
        <p class="intro">{{ t('dcs.devices.intro') }}</p>
        <ul class="rows devices">
          <li v-for="d in knownDevices" :key="d.fullName">
            <span class="dev">
              <span class="t">{{ d.name }}</span>
              <span class="s">{{ guid(d.fullName) }}{{ d.seen ? ` · ${t('dcs.devices.seen')}` : '' }}</span>
            </span>
            <ToggleSwitch
              :model-value="d.disabled"
              :disabled="!!working || data?.dcs_running !== false"
              :aria-label="t('dcs.devices.disable', { name: d.name })"
              @update:model-value="setDisabled(d.fullName, $event)"
            />
          </li>
        </ul>
      </section>

      <section v-if="devices">
        <h3 class="eyebrow">{{ t('dcs.absent.title') }}</h3>
        <p v-if="!devices.seen.length" class="intro">{{ t('dcs.absent.no_log') }}</p>
        <template v-else>
          <p class="intro">
            {{ t('dcs.absent.intro') }}<template v-if="devices.log_date">{{ ' ' + t('dcs.absent.log_date', { date: date(devices.log_date) }) }}</template>.
            {{ t('dcs.absent.intro2') }}
          </p>
          <ul v-if="devices.absent.length" class="rows devices">
            <li v-for="d in devices.absent" :key="d.device">
              <span class="dev">
                <span class="t">{{ d.device.replace(/\s*\{[^}]*\}$/, '') }}</span>
                <span class="s">{{ guid(d.device) }} · {{ tn('settings.devices.modules', d.profiles.length) }}{{ t('common.colon') }}{{ d.profiles.join(', ') }}</span>
              </span>
              <span class="act">
                <template v-if="forgetting === d.device">
                  <Button size="small" severity="danger" :label="t('dcs.forget.label')" @click="forget(d.device)" />
                  <Button size="small" text :label="t('common.cancel')" @click="forgetting = null" />
                </template>
                <Button
                  v-else
                  size="small"
                  text
                  icon="pi pi-trash"
                  :label="t('dcs.forget.ask')"
                  :loading="working === `forget:${d.device}`"
                  :disabled="!!working || data?.dcs_running !== false"
                  @click="forgetting = d.device"
                />
              </span>
            </li>
          </ul>
          <p v-else class="intro">{{ t('dcs.absent.none') }}</p>
        </template>
      </section>

      <p v-if="modifiersError" class="warn" role="alert">{{ t('dcs.modifiers.unreadable', { error: modifiersError }) }}</p>
      <section v-if="modifiers && (modifiers.issues.length || modifiers.deleted.length)">
        <h3 class="eyebrow">{{ t('dcs.modifiers.title') }}</h3>
        <template v-if="modifiers.issues.length">
          <p class="intro">{{ t('dcs.modifiers.intro') }}</p>
          <ul class="rows devices">
            <li v-for="i in modifiers.issues" :key="`${i.profile}/${i.modifier}`">
              <span class="dev">
                <span class="t">{{ i.modifier }} · {{ i.profile }}</span>
                <span v-if="i.new_device" class="s">{{ deviceName(i.device) }} → {{ deviceName(i.new_device) }} · {{ guid(i.device) }}</span>
                <span v-else class="s">{{ i.problem }}</span>
              </span>
            </li>
          </ul>
          <div class="head">
            <span />
            <Button
              size="small"
              icon="pi pi-wrench"
              :label="t('dcs.modifiers.fix')"
              :loading="working === 'modifiers'"
              :disabled="!fixable.length || !!working || data?.dcs_running !== false"
              @click="fixModifiers"
            />
          </div>
        </template>
        <template v-if="modifiers.deleted.length">
          <p class="intro">{{ t('dcs.modifiers.deleted') }}</p>
          <ul class="rows devices">
            <li v-for="d in modifiers.deleted" :key="d.profile">
              <span class="dev">
                <span class="t">{{ d.profile }}</span>
                <span class="s">{{ t('dcs.modifiers.backup_of', { date: date(d.created) }) }}</span>
              </span>
              <Button
                size="small"
                text
                icon="pi pi-replay"
                :label="t('dcs.modifiers.restore')"
                :loading="working === `modifiers:${d.profile}`"
                :disabled="!!working || data?.dcs_running !== false"
                @click="restoreModifiers(d.profile, d.backup)"
              />
            </li>
          </ul>
        </template>
      </section>

      <section>
        <div class="head">
          <h3 class="eyebrow">{{ t('dcs.hat.title') }}</h3>
          <Button size="small" severity="secondary" icon="pi pi-search" :label="hat ? t('dcs.read_again') : t('dcs.search')" :loading="hatLoading" :disabled="!!working" @click="loadHat" />
        </div>
        <p class="intro">
          {{ t('dcs.hat.intro') }}
        </p>
        <div class="options">
          <label><Checkbox v-model="everyDevice" binary :disabled="!!working || hatLoading" /> {{ t('dcs.hat.every_device') }}</label>
          <label><Checkbox v-model="allModules" binary :disabled="!!working || hatLoading" /> {{ t('dcs.hat.all_modules') }}</label>
        </div>
        <p v-if="hatError" class="warn" role="alert">{{ hatError }}</p>
        <template v-if="hat">
          <ul v-if="hat.devices.length" class="rows devices hat">
            <li v-for="d in hat.devices" :key="d.device" :class="{ off: !hatSelectable(d) }">
              <Checkbox
                :model-value="hatSelectable(d) && hatChosen.has(d.device)"
                binary
                :disabled="!hatSelectable(d) || !!working"
                :aria-label="t('dcs.hat.remove_of', { device: d.device })"
                @update:model-value="toggleHat(d.device, $event)"
              />
              <span class="dev">
                <span class="t">{{ d.device.replace(/\s*\{[^}]*\}$/, '') }}</span>
                <span class="s">{{ guid(d.device) }} · {{ hatSummary(d) }}</span>
                <span v-if="!d.hat_only_views" class="s why">
                  {{ t('dcs.hat.used', { list: d.own_hat.map((o) => t('dcs.hat.used_item', { command: o.command, key: o.key.replace('JOY_BTN_', ''), profile: o.profile })).join(t('dcs.list_sep')) + (d.own_hat_count > d.own_hat.length ? '…' : '') }) }}<template v-if="!everyDevice">{{ t('dcs.hat.used_hint') }}</template>
                </span>
                <details v-if="hatSelectable(d)">
                  <summary>{{ t('modules.title') }}</summary>
                  <ul class="modules">
                    <li v-for="m in d.modules" :key="m.profile">
                      {{ m.profile }} · {{ tn('dcs.views', m.views.length) }}<template v-if="m.new_file"> · {{ t('dcs.new_file') }}</template><template v-if="m.error"> · {{ t('dcs.ignored', { error: m.error }) }}</template>
                    </li>
                  </ul>
                </details>
              </span>
            </li>
          </ul>
          <p v-else class="intro">{{ allModules ? t('dcs.hat.none_installed') : t('dcs.hat.none_configured') }}</p>
          <div v-if="hat.devices.length" class="head">
            <span class="intro">{{ t('dcs.to_remove', { what: tn('dcs.views', hatTotals.views), where: tn('dcs.files', hatTotals.files) }) }}<template v-if="hatTotals.created">{{ tn('dcs.created', hatTotals.created) }}</template>.</span>
            <span class="act">
              <template v-if="hatConfirming">
                <Button size="small" severity="danger" :label="t('dcs.remove')" @click="removeHat" />
                <Button size="small" text :label="t('common.cancel')" @click="hatConfirming = false" />
              </template>
              <Button
                v-else
                size="small"
                icon="pi pi-eraser"
                :label="t('dcs.remove_ask')"
                :loading="working === 'hat'"
                :disabled="!!working || !hatTotals.views || data?.dcs_running !== false"
                @click="hatConfirming = true"
              />
            </span>
          </div>
          <p v-if="hatConfirming" class="intro">{{ t('dcs.hat.confirm') }}</p>
        </template>
        <div v-if="hatResult" class="result" role="status">
          <p v-if="!hatResult.differences.length">{{ t('dcs.result.ok') }}</p>
          <template v-else>
            <p><i class="pi pi-exclamation-triangle" /> {{ t('dcs.result.differ') }}</p>
            <ul><li v-for="(text, i) in hatResult.differences" :key="i">{{ text }}</li></ul>
          </template>
          <p v-if="hatResult.written.some((w) => w.deleted)">
            {{ t('dcs.result.deleted', { files: hatResult.written.filter((w) => w.deleted).map((w) => `${w.device} (${w.profile})`).join(', ') }) }}
          </p>
        </div>
      </section>

      <section>
        <div class="head">
          <h3 class="eyebrow">{{ t('dcs.generic.title') }}</h3>
          <Button size="small" severity="secondary" icon="pi pi-search" :label="generic ? t('dcs.read_again') : t('dcs.search')" :loading="genericLoading" :disabled="!!working || !store.state.settings?.buttonless_devices.length" @click="loadGeneric" />
        </div>
        <p class="intro">
          {{ t('dcs.generic.intro') }}
        </p>
        <ul class="rows marks">
          <li v-for="name in deviceNames" :key="name">
            <label><Checkbox :model-value="isButtonless(name)" binary :disabled="!!working" @update:model-value="setButtonless(name, $event)" /> {{ name }}</label>
          </li>
        </ul>
        <div class="options">
          <label><Checkbox v-model="genericAllModules" binary :disabled="!!working || genericLoading" /> {{ t('dcs.generic.all_modules') }}</label>
        </div>
        <p v-if="genericError" class="warn" role="alert">{{ genericError }}</p>
        <template v-if="generic">
          <ul v-if="generic.devices.length" class="rows devices">
            <li v-for="d in generic.devices" :key="d.device">
              <span class="dev">
                <span class="t">{{ d.name }}</span>
                <span class="s">{{ guid(d.device) }} · {{ t('dcs.in', { what: tn('dcs.buttons', genericOk(d).reduce((n, m) => n + m.bindings.length, 0)), where: tn('settings.devices.modules', genericOk(d).length) }) }}</span>
                <details>
                  <summary>{{ t('modules.title') }}</summary>
                  <ul class="modules">
                    <li v-for="m in d.modules" :key="m.profile">
                      {{ m.profile }} · {{ m.bindings.map((b) => `${b.key.replace('JOY_', '')} ${b.command}`).join(', ') }}<template v-if="m.new_file"> · {{ t('dcs.new_file') }}</template><template v-if="m.error"> · {{ t('dcs.ignored', { error: m.error }) }}</template>
                      <span v-if="m.unknown.length" class="s why">
                        {{ t('dcs.generic.unknown', { list: m.unknown.map((b) => `${b.key.replace('JOY_', '')} ${b.command}`).join(', ') }) }}
                      </span>
                    </li>
                  </ul>
                </details>
              </span>
            </li>
          </ul>
          <p v-else class="intro">{{ genericAllModules ? t('dcs.generic.none_installed') : t('dcs.generic.none_configured') }}</p>
          <div v-if="generic.devices.length" class="head">
            <span class="intro">{{ t('dcs.to_remove', { what: tn('devices.bindings', genericTotals.buttons), where: tn('dcs.files', genericTotals.files) }) }}<template v-if="genericTotals.created">{{ tn('dcs.created', genericTotals.created) }}</template>.</span>
            <span class="act">
              <template v-if="genericConfirming">
                <Button size="small" severity="danger" :label="t('dcs.remove')" @click="removeGeneric" />
                <Button size="small" text :label="t('common.cancel')" @click="genericConfirming = false" />
              </template>
              <Button
                v-else
                size="small"
                icon="pi pi-eraser"
                :label="t('dcs.remove_ask')"
                :loading="working === 'generic'"
                :disabled="!!working || !genericTotals.buttons || data?.dcs_running !== false"
                @click="genericConfirming = true"
              />
            </span>
          </div>
          <p v-if="genericConfirming" class="intro">{{ t('dcs.generic.confirm') }}</p>
        </template>
        <div v-if="genericResult" class="result" role="status">
          <p v-if="!genericResult.differences.length">{{ t('dcs.result.ok') }}</p>
          <template v-else>
            <p><i class="pi pi-exclamation-triangle" /> {{ t('dcs.result.differ') }}</p>
            <ul><li v-for="(text, i) in genericResult.differences" :key="i">{{ text }}</li></ul>
          </template>
          <p><Button size="small" severity="secondary" outlined :label="t('dcs.undo.label')" :loading="working === genericResult.backup.id" :disabled="!!working" @click="undoGeneric" /></p>
        </div>
      </section>

      <section>
        <div class="head">
          <h3 class="eyebrow">{{ t('dcs.backup.title') }}</h3>
          <Button size="small" severity="secondary" icon="pi pi-save" :label="t('dcs.backup.now')" :loading="working === 'backup'" :disabled="!!working" @click="backupNow" />
        </div>
        <ul v-if="data?.backups.length" class="rows">
          <li v-for="b in data.backups" :key="b.id">
            <span class="when">{{ date(b.created) }}</span>
            <span class="reason">{{ b.reason }}</span>
            <span class="n">{{ tn('dcs.files', b.files) }} · {{ size(b.size) }}</span>
            <span class="act">
              <template v-if="confirming === b.id">
                <Button size="small" severity="danger" :label="t('dcs.restore.label')" @click="restore(b.id)" />
                <Button size="small" text :label="t('common.cancel')" @click="confirming = null" />
              </template>
              <Button
                v-else
                size="small"
                text
                icon="pi pi-history"
                :label="t('dcs.restore.ask')"
                :loading="working === b.id"
                :disabled="!!working || data.dcs_running !== false"
                @click="confirming = b.id"
              />
            </span>
          </li>
        </ul>
        <p v-else-if="data" class="intro">{{ t('dcs.backup.none') }}</p>
        <p v-if="confirming" class="intro">{{ t('dcs.restore.confirm') }}</p>
        <p v-if="data" class="intro folder"><Tr k="dcs.backup.folder"><template #folder><code>{{ data.folder }}</code></template></Tr></p>
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
.rows.marks { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0 12px; padding: 6px 8px; }
.rows.marks li { display: block; border: 0; padding: 3px 0; }
.rows.marks label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.rows li:last-child { border-bottom: 0; }
.when { font-variant-numeric: tabular-nums; }
.reason { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ink-2); }
.devices li { grid-template-columns: minmax(0, 1fr) auto; }
.dev { display: flex; flex-direction: column; min-width: 0; }
.dev .t { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dev .s { font: 12px var(--f-mono); color: var(--ink-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.act { display: flex; gap: 4px; justify-content: flex-end; }
.options { display: flex; flex-direction: column; gap: 4px; margin: 6px 0; font-size: 13px; }
.options label { display: flex; align-items: center; gap: 8px; }
.hat li { grid-template-columns: auto minmax(0, 1fr); align-items: start; }
.hat li.off .t { color: var(--ink-3); }
.dev .why { white-space: normal; }
.hat details { font-size: 12px; color: var(--ink-3); }
.hat .modules { margin: 2px 0 0; padding-left: 16px; }
.result { font-size: 13px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px; }
.result p, .result ul { margin: 0 0 4px; }
@media (max-width: 600px) { .rows li { grid-template-columns: 1fr auto; } .reason, .n { grid-column: 1; } }
</style>
