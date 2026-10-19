<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import { useStore } from '../lib/store'
import type { Device } from '../lib/types'

const store = useStore()
const { state } = store
const dragged = ref<number | null>(null)
const over = ref<number | null>(null)

function layersText(d: Device): string {
  const others = d.layers.filter((l) => l !== '')
  return others.length ? ` · calque ${others.join(', ')}` : ''
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
  <section class="col" aria-label="Périphériques">
    <header class="colhead">
      <span class="eyebrow">Périphériques<template v-if="store.profile.value"> · {{ store.profile.value.name }}</template></span>
      <span class="hint">Cochés = pages exportées · glisser pour l'ordre des pages</span>
    </header>
    <div class="list" role="listbox" aria-label="Périphériques">
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
          :aria-label="`Exporter ${d.name}`"
          @click.stop
          @update:model-value="store.toggleExported(store.profile.value!.name, d)"
        />
        <span class="meta">
          <span class="t" :title="d.full_name">{{ d.name }}</span>
          <span class="s">{{ d.binding_count }} liaisons{{ layersText(d) }}</span>
        </span>
        <span v-if="d.dcs_disabled" class="pill" v-tooltip.left="'Désactivé dans DCS : le jeu ignore ce périphérique (fenêtre Commandes DCS)'">désactivé</span>
        <span v-else-if="store.isHidden(d.name)" class="pill">caché</span>
        <span v-else-if="store.templateIdFor(d)" class="pill ok">gabarit</span>
        <span v-else class="pill">liste</span>
        <Button
          class="eye"
          text
          rounded
          size="small"
          :icon="store.isHidden(d.name) ? 'pi pi-eye' : 'pi pi-eye-slash'"
          :aria-label="store.isHidden(d.name) ? `Montrer ${d.name}` : `Cacher ${d.name}`"
          v-tooltip.left="store.isHidden(d.name) ? 'Montrer ce périphérique (H)' : 'Cacher ce périphérique dans tous les modules (H)'"
          @click.stop="store.setHidden(d.name, !store.isHidden(d.name))"
        />
      </div>
      <p v-if="store.profile.value && !store.devices.value.length && !store.hiddenCount.value" class="empty">Aucun périphérique configuré pour ce module.</p>
    </div>
    <footer v-if="store.hiddenCount.value" class="hidden-bar">
      <span>{{ store.hiddenCount.value }} caché{{ store.hiddenCount.value > 1 ? 's' : '' }}</span>
      <Button size="small" text :label="state.showHidden ? 'Masquer' : 'Afficher'" @click="state.showHidden = !state.showHidden" />
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
