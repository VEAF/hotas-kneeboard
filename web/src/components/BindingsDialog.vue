<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { api } from '../lib/api'
import { useStore } from '../lib/store'
import type { DcsBackup, DeviceBinding, DeviceBindingsResponse } from '../lib/types'
import { compareInputs, inputName } from '../render/inputs'
import { t, tn } from '../lib/i18n'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const toast = useToast()

const data = ref<DeviceBindingsResponse | null>(null)
const loading = ref(false)
const error = ref('')
const filter = ref('')
const picked = ref<Set<string>>(new Set())
const confirming = ref(false)
const busy = ref(false)
/** The last removal, which Undo undoes by restoring the backup made just before it */
const done = ref<{ removed: number; backup: DcsBackup } | null>(null)

// label and hint: catalog keys
const ORIGINS = {
  user: { label: 'bindings.origin.user', class: 'ok', hint: 'bindings.origin.user_tip' },
  device: { label: 'bindings.origin.device', class: '', hint: 'bindings.origin.device_tip' },
  generic: { label: 'bindings.origin.generic', class: 'warn', hint: 'bindings.origin.generic_tip' },
} as const
const id = (b: DeviceBinding) => `${b.kind}|${b.hash}|${b.key}|${b.reformers.join('+')}`
const modifier = (b: DeviceBinding) => b.reformers.map((r) => inputName(r)).join(' + ')

const rows = computed(() => {
  const q = filter.value.trim().toLowerCase()
  return [...(data.value?.bindings ?? [])]
    .filter((b) => !q || [inputName(b.key), b.key, b.command, modifier(b)].some((s) => s.toLowerCase().includes(q)))
    .sort((a, b) => compareInputs(a.key, b.key) || modifier(a).localeCompare(modifier(b)) || a.command.localeCompare(b.command))
})
const chosen = computed(() => (data.value?.bindings ?? []).filter((b) => picked.value.has(id(b))))

async function load() {
  const p = store.profile.value
  const d = store.device.value
  if (!p || !d) return
  loading.value = true
  error.value = ''
  try {
    data.value = await api.deviceBindings(p.name, d.full_name)
  } catch (e) {
    data.value = null
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

watch(visible, (open) => {
  if (!open) return
  picked.value = new Set()
  confirming.value = false
  done.value = null
  filter.value = ''
  load()
})

function toggle(b: DeviceBinding, on: boolean) {
  const next = new Set(picked.value)
  if (on) next.add(id(b))
  else next.delete(id(b))
  picked.value = next
}

async function remove() {
  const p = store.profile.value
  if (!data.value || !p || !chosen.value.length) return
  busy.value = true
  try {
    const refs = chosen.value.map(({ kind, hash, key, reformers }) => ({ kind, hash, key, reformers }))
    const result = await api.removeBindings(data.value.profile, data.value.device, refs)
    done.value = { removed: result.removed, backup: result.backup }
    picked.value = new Set()
    confirming.value = false
    await Promise.all([load(), store.load(true)])
    if (result.removed < result.asked) {
      toast.add({
        severity: 'warn',
        summary: t('bindings.partial', { removed: result.removed, asked: result.asked }),
        detail: t('bindings.partial_detail'),
        life: 8000,
      })
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.remove_failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = false
  }
}

async function undo() {
  if (!done.value) return
  busy.value = true
  try {
    await api.restoreDcsBackup(done.value.backup.id)
    done.value = null
    await Promise.all([load(), store.load(true)])
    toast.add({ severity: 'success', summary: t('dcs.undo.done'), detail: t('dcs.undo.detail'), life: 5000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('dcs.undo.failed'), detail: (e as Error).message, life: 10000 })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('bindings.title', { device: store.device.value?.name ?? '' })"
    :style="{ width: 'min(760px, 96vw)' }"
  >
    <p class="where">
      {{ store.profile.value?.display_name }} · {{ t('bindings.intro') }}
    </p>

    <div v-if="done" class="done" role="status">
      <i class="pi pi-check-circle" />
      <span>{{ tn('bindings.done', done.removed) }}</span>
      <Button :label="t('bindings.undo')" size="small" severity="secondary" outlined :loading="busy" @click="undo" />
    </div>

    <div v-if="loading" class="center"><ProgressSpinner style="width: 32px; height: 32px" /></div>
    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
    <template v-else-if="data">
      <p v-if="!data.editable" class="error">
        {{ t('bindings.not_installed') }}
      </p>
      <InputText v-model="filter" size="small" :placeholder="t('bindings.filter')" fluid :aria-label="t('bindings.filter_aria')" />
      <div class="table">
        <table>
          <thead>
            <tr><th /><th>{{ t('bindings.col.input') }}</th><th>{{ t('bindings.col.modifier') }}</th><th>{{ t('bindings.col.command') }}</th><th>{{ t('bindings.col.origin') }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="b in rows" :key="id(b)" :class="{ on: picked.has(id(b)), fixed: !b.removable }" @click="data.editable && b.removable && toggle(b, !picked.has(id(b)))">
              <td @click.stop>
                <Checkbox
                  :model-value="picked.has(id(b))"
                  binary
                  :disabled="!data.editable || !b.removable"
                  v-tooltip.right="b.removable ? undefined : t('bindings.unknown_tip')"
                  :aria-label="t('bindings.remove_of', { command: b.command, input: inputName(b.key) })"
                  @update:model-value="(on: boolean) => toggle(b, on)"
                />
              </td>
              <td class="mono">{{ inputName(b.key) }}</td>
              <td>{{ modifier(b) }}</td>
              <td>{{ b.command }}</td>
              <td>
                <span class="pill" :class="ORIGINS[b.origin].class" v-tooltip.left="t(ORIGINS[b.origin].hint)">{{ t(ORIGINS[b.origin].label) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!rows.length" class="empty">{{ filter ? t('bindings.none_match') : t('bindings.none') }}</p>
      </div>
    </template>

    <template #footer>
      <template v-if="confirming">
        <span class="confirm">
          {{ tn('bindings.confirm', chosen.length, { module: store.profile.value?.display_name }) }}
        </span>
        <Button :label="t('bindings.back')" severity="secondary" text :disabled="busy" @click="confirming = false" />
        <Button :label="t('dcs.remove')" severity="danger" icon="pi pi-trash" :loading="busy" @click="remove" />
      </template>
      <template v-else>
        <Button :label="t('common.close')" severity="secondary" text @click="visible = false" />
        <Button
          :label="t('bindings.delete', { n: chosen.length })"
          severity="danger"
          icon="pi pi-trash"
          :disabled="!chosen.length || busy"
          @click="confirming = true"
        />
      </template>
    </template>
  </Dialog>
</template>

<style scoped>
.where { margin: 0 0 12px; color: var(--ink-2); }
.done { display: flex; align-items: center; gap: 10px; margin: 0 0 12px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px; }
.done .pi { color: var(--ok); }
.done span { flex: 1; }
.table { max-height: min(55vh, 520px); overflow: auto; margin-top: 10px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-weight: 600; color: var(--ink-3); position: sticky; top: 0; background: var(--panel); }
th, td { padding: 5px 6px; border-bottom: 1px solid var(--line); }
tbody tr { cursor: pointer; }
tbody tr.on { background: var(--sel); }
tbody tr.fixed { cursor: default; color: var(--ink-3); }
.mono { font-family: var(--f-mono); white-space: nowrap; }
.empty, .center { padding: 12px; color: var(--ink-3); text-align: center; }
.error { color: var(--bad); }
.confirm { margin-right: auto; }
</style>
