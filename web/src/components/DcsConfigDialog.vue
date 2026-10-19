<script setup lang="ts">
// Changes to DCS's own controls files (Saved Games\DCS\Config\Input): devices disabled in DCS,
// devices DCS no longer sees, modifiers on a renamed device, the generic hat views removed in bulk, and the backups made before
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
  HatViewsDevice,
  HatViewsPreview,
  HatViewsResult,
  ModifiersResponse,
} from '../lib/types'

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
    forgetHatPreview()
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

// --- modifiers DCS drops because their device was renamed by its driver ---------------------------
const fixable = computed(() => (modifiers.value?.issues ?? []).filter((i) => i.new_device))
const deviceName = (fullName: string) => fullName.replace(/\s*\{[^}]*\}$/, '')

async function changeModifiers(what: string, call: () => Promise<{ fixed: unknown[] }>, done: string) {
  working.value = what
  try {
    const result = await call()
    toast.add({ severity: 'success', summary: done, detail: `${result.fixed.length} modificateur(s) renommé(s)`, life: 6000 })
    await load()
    await store.load(true)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Modification impossible', detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

const fixModifiers = () => changeModifiers('modifiers', api.fixModifiers, 'Modificateurs réparés')
const restoreModifiers = (profile: string, backup: string) =>
  changeModifiers(`modifiers:${profile}`, () => api.restoreModifiers(profile, backup), `modifiers.lua de ${profile} ramené`)

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
const plural = (n: number, word: string, many = `${word}s`) => `${n} ${n > 1 ? many : word}`
const hatSummary = (d: HatViewsDevice) => {
  const ok = hatOk(d)
  const created = ok.filter((m) => m.new_file).length
  return (
    `${plural(ok.reduce((n, m) => n + m.views.length, 0), 'vue')} dans ${plural(ok.length, 'module')}` +
    (created ? ` (${plural(created, 'nouveau fichier', 'nouveaux fichiers')})` : '')
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
      if (!w) differences.push(`${m.file} (${m.profile}) : prévu à l'aperçu, rien n'a été écrit`)
      else if (w.removed !== m.views.length && w.removed === w.expected)
        differences.push(`${m.file} (${m.profile}) : ${w.removed} vue(s) retirée(s), ${m.views.length} à l'aperçu`)
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
      summary: differ ? 'Vues retirées, avec des écarts' : 'Vues du chapeau retirées',
      detail:
        `${plural(removed, 'vue retirée', 'vues retirées')} dans ${plural(files, 'fichier')}` +
        (differ ? ' : voir le détail dans la fenêtre' : ", relu et conforme à l'aperçu"),
      life: 8000,
    })
    await Promise.all([load(), store.load(true), loadHat()])
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Retrait impossible', detail: (e as Error).message, life: 10000 })
    await load()
  } finally {
    working.value = ''
  }
}

watch(visible, (open) => {
  confirming.value = null
  forgetting.value = null
  hatResult.value = null
  forgetHatPreview()
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
    forgetHatPreview()
    hatResult.value = null
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

      <p v-if="modifiersError" class="warn" role="alert">Modificateurs illisibles : {{ modifiersError }}</p>
      <section v-if="modifiers && (modifiers.issues.length || modifiers.deleted.length)">
        <h3 class="eyebrow">Modificateurs</h3>
        <template v-if="modifiers.issues.length">
          <p class="intro">
            Ces modificateurs nomment leur périphérique sous un ancien nom : son pilote l'a renommé, le GUID est le même.
            DCS les ignore, et les liaisons qui s'en servent s'affichent mais ne marchent pas en jeu.
            « Réparer » leur donne le nom que DCS utilise maintenant, dans tous les modules, après une sauvegarde.
          </p>
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
              label="Réparer"
              :loading="working === 'modifiers'"
              :disabled="!fixable.length || !!working || data?.dcs_running !== false"
              @click="fixModifiers"
            />
          </div>
        </template>
        <template v-if="modifiers.deleted.length">
          <p class="intro">
            Ces modules n'ont plus de fichier de modificateurs : DCS le supprime quand il n'y reste que les réglages par défaut, ce qui arrive quand il ignore un modificateur.
            Une sauvegarde l'a encore ; il revient avec les noms de périphériques réparés. Si tu l'as supprimé toi-même, laisse-le.
          </p>
          <ul class="rows devices">
            <li v-for="d in modifiers.deleted" :key="d.profile">
              <span class="dev">
                <span class="t">{{ d.profile }}</span>
                <span class="s">sauvegarde du {{ date(d.created) }}</span>
              </span>
              <Button
                size="small"
                text
                icon="pi pi-replay"
                label="Ramener"
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
          <h3 class="eyebrow">Vues du chapeau</h3>
          <Button size="small" severity="secondary" icon="pi pi-search" :label="hat ? 'Relire' : 'Chercher'" :loading="hatLoading" :disabled="!!working" @click="loadHat" />
        </div>
        <p class="intro">
          Tous les modules mettent les 8 vues lentes (« View Up slow »…) sur le premier chapeau de chaque périphérique, même un palonnier, un ICP ou un MFD.
          Avec TrackIR ou la VR, elles ne servent à rien et encombrent les pages. Seules ces 8 liaisons par défaut sont retirées ; ce que tu as mis toi-même sur un chapeau reste.
        </p>
        <div class="options">
          <label><Checkbox v-model="everyDevice" binary :disabled="!!working || hatLoading" /> Tous les périphériques, chapeaux utilisés compris</label>
          <label><Checkbox v-model="allModules" binary :disabled="!!working || hatLoading" /> Tous les modules installés, pas seulement ceux que tu as configurés (crée un fichier par module)</label>
        </div>
        <p v-if="hatError" class="warn" role="alert">{{ hatError }}</p>
        <template v-if="hat">
          <ul v-if="hat.devices.length" class="rows devices hat">
            <li v-for="d in hat.devices" :key="d.device" :class="{ off: !hatSelectable(d) }">
              <Checkbox
                :model-value="hatSelectable(d) && hatChosen.has(d.device)"
                binary
                :disabled="!hatSelectable(d) || !!working"
                :aria-label="`Retirer les vues du chapeau de ${d.device}`"
                @update:model-value="toggleHat(d.device, $event)"
              />
              <span class="dev">
                <span class="t">{{ d.device.replace(/\s*\{[^}]*\}$/, '') }}</span>
                <span class="s">{{ guid(d.device) }} · {{ hatSummary(d) }}</span>
                <span v-if="!d.hat_only_views" class="s why">
                  Chapeau utilisé ({{ d.own_hat.map((o) => `${o.command} en ${o.key.replace('JOY_BTN_', '')}, ${o.profile}`).join(' ; ') }}{{ d.own_hat_count > d.own_hat.length ? '…' : '' }})<template v-if="!everyDevice"> : coche « Tous les périphériques » pour en retirer quand même les vues par défaut</template>
                </span>
                <details v-if="hatSelectable(d)">
                  <summary>Modules</summary>
                  <ul class="modules">
                    <li v-for="m in d.modules" :key="m.profile">
                      {{ m.profile }} · {{ plural(m.views.length, 'vue') }}<template v-if="m.new_file"> · nouveau fichier</template><template v-if="m.error"> · ignoré : {{ m.error }}</template>
                    </li>
                  </ul>
                </details>
              </span>
            </li>
          </ul>
          <p v-else class="intro">Aucun périphérique ne porte ces vues dans {{ allModules ? 'les modules installés' : 'les modules configurés' }}.</p>
          <div v-if="hat.devices.length" class="head">
            <span class="intro">{{ plural(hatTotals.views, 'vue') }} à retirer dans {{ plural(hatTotals.files, 'fichier') }}<template v-if="hatTotals.created">, dont {{ plural(hatTotals.created, 'créé', 'créés') }}</template>.</span>
            <span class="act">
              <template v-if="hatConfirming">
                <Button size="small" severity="danger" label="Retirer" @click="removeHat" />
                <Button size="small" text label="Annuler" @click="hatConfirming = false" />
              </template>
              <Button
                v-else
                size="small"
                icon="pi pi-eraser"
                label="Retirer…"
                :loading="working === 'hat'"
                :disabled="!!working || !hatTotals.views || data?.dcs_running !== false"
                @click="hatConfirming = true"
              />
            </span>
          </div>
          <p v-if="hatConfirming" class="intro">Une seule sauvegarde est faite avant, restaurable ci-dessous ; les commandes sont relues après l'écriture.</p>
        </template>
        <div v-if="hatResult" class="result" role="status">
          <p v-if="!hatResult.differences.length">Relu après l'écriture : conforme à l'aperçu.</p>
          <template v-else>
            <p><i class="pi pi-exclamation-triangle" /> Relu après l'écriture, des écarts avec l'aperçu :</p>
            <ul><li v-for="(text, i) in hatResult.differences" :key="i">{{ text }}</li></ul>
          </template>
          <p v-if="hatResult.written.some((w) => w.deleted)">
            Fichier supprimé, comme DCS le fait quand il ne reste aucune différence avec les réglages par défaut :
            {{ hatResult.written.filter((w) => w.deleted).map((w) => `${w.device} (${w.profile})`).join(', ') }}.
            Ce périphérique n'apparaît plus dans ces modules de l'application : ce n'est pas une perte.
          </p>
        </div>
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
