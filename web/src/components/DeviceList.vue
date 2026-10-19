<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import { inactiveHint, useStore } from '../lib/store'
import type { Device } from '../lib/types'
import { t, tn } from '../lib/i18n'

const store = useStore()
const { state } = store
const dragged = ref<number | null>(null)
const over = ref<number | null>(null)

function layersText(d: Device): string {
  const others = d.layers.filter((l) => l !== '')
  return others.length ? ` · ${t('devices.layer', { layers: others.join(', ') })}` : ''
}

// the selected device hidden: select another one
watch(store.devices, (list) => {
  if (!list.some((d) => d.full_name === state.deviceKey)) state.deviceKey = list[0]?.full_name ?? ''
})

function onDrop(index: number) {
  if (dragged.value !== null && store.profile.value) store.moveDevice(store.profile.value.name, dragged.value, index)
  dragged.value = over.value = null
}
</script>

<template>
  <section class="col" :aria-label="t('devices.title')">
    <header class="colhead">
      <span class="eyebrow">{{ t('devices.title') }}<template v-if="store.profile.value"> · {{ store.profile.value.display_name }}</template></span>
      <span class="hint">{{ t('devices.hint') }}</span>
    </header>
    <div class="list" role="listbox" :aria-label="t('devices.title')">
      <div
        v-for="(d, i) in store.devices.value"
        :key="d.full_name"
        class="row"
        :class="{ on: d.full_name === state.deviceKey, over: over === i && dragged !== i, dragging: dragged === i, hidden: store.isHidden(d.name) }"
        role="option"
        :aria-selected="d.full_name === state.deviceKey"
        draggable="true"
        tabindex="-1"
        @click="state.deviceKey = d.full_name"
        @dragstart="dragged = i"
        @dragover.prevent="over = i"
        @dragleave="over = over === i ? null : over"
        @drop.prevent="onDrop(i)"
        @dragend="dragged = over = null"
      >
        <Checkbox
          :model-value="store.isExported(store.profile.value!.name, d)"
          binary
          :disabled="store.isHidden(d.name)"
          :aria-label="t('devices.export', { name: d.name })"
          @click.stop
          @update:model-value="store.toggleExported(store.profile.value!.name, d)"
        />
        <span class="meta">
          <span class="t" :title="d.full_name">{{ d.name }}</span>
          <span class="s">{{ tn('devices.bindings', d.binding_count) }}{{ layersText(d) }}</span>
        </span>
        <span v-if="d.inactive_modifiers.length" class="pill warn" v-tooltip.left="inactiveHint(d.inactive_modifiers)">{{ t('devices.pill.inactive_modifier') }}</span>
        <span v-if="d.dcs_disabled" class="pill" v-tooltip.left="t('devices.disabled_tip')">{{ t('devices.pill.disabled') }}</span>
        <span v-else-if="store.isHidden(d.name)" class="pill">{{ t('devices.pill.hidden') }}</span>
        <span v-else-if="store.templateIdFor(d)" class="pill ok">{{ t('devices.pill.template') }}</span>
        <span v-else class="pill">{{ t('devices.pill.list') }}</span>
        <Button
          class="eye"
          text
          rounded
          size="small"
          :icon="store.isHidden(d.name) ? 'pi pi-eye' : 'pi pi-eye-slash'"
          :aria-label="store.isHidden(d.name) ? t('devices.show', { name: d.name }) : t('devices.hide', { name: d.name })"
          v-tooltip.left="store.isHidden(d.name) ? t('devices.show_tip') : t('devices.hide_tip')"
          @click.stop="store.setHidden(d.name, !store.isHidden(d.name))"
        />
      </div>
      <p v-if="store.profile.value && !store.devices.value.length && !store.hiddenCount.value" class="empty">{{ t('devices.none') }}</p>
    </div>
    <footer v-if="store.hiddenCount.value" class="hidden-bar">
      <span>{{ tn('settings.hidden', store.hiddenCount.value) }}</span>
      <Button size="small" text :label="state.showHidden ? t('devices.hidden.hide') : t('devices.hidden.show')" @click="state.showHidden = !state.showHidden" />
    </footer>
  </section>
</template>

<style scoped>
.row { grid-template-columns: 20px minmax(0, 1fr) auto 28px; cursor: grab; }
.row.hidden .meta { opacity: 0.5; }
.eye { width: 28px !important; height: 28px !important; opacity: 0; transition: opacity 0.12s; }
.row:hover .eye, .row.on .eye, .row.hidden .eye, .eye:focus-visible { opacity: 1; }
.hidden-bar { display: flex; align-items: center; justify-content: space-between; padding: 4px 8px 4px 14px; border-top: 1px solid var(--line); font-size: 12px; color: var(--ink-3); }
.row.dragging { opacity: 0.45; }
.row.over { box-shadow: inset 0 2px 0 var(--amber); }
.hint { font-size: 12px; color: var(--ink-3); }
</style>
