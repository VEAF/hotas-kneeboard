<script setup lang="ts">
import { ref } from 'vue'
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
        :class="{ on: d.full_name === state.deviceKey, over: over === i && dragged !== i, dragging: dragged === i }"
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
          :aria-label="`Exporter ${d.name}`"
          @click.stop
          @update:model-value="store.toggleExported(store.profile.value!.name, d)"
        />
        <span class="meta">
          <span class="t" :title="d.full_name">{{ d.name }}</span>
          <span class="s">{{ d.binding_count }} liaisons{{ layersText(d) }}</span>
        </span>
        <span v-if="store.templateIdFor(d)" class="pill ok">gabarit</span>
        <span v-else class="pill">liste</span>
      </div>
      <p v-if="store.profile.value && !store.devices.value.length" class="empty">Aucun périphérique configuré pour ce module.</p>
    </div>
  </section>
</template>

<style scoped>
.row { grid-template-columns: 20px minmax(0, 1fr) auto; cursor: grab; }
.row.dragging { opacity: 0.45; }
.row.over { box-shadow: inset 0 2px 0 var(--amber); }
.hint { font-size: 12px; color: var(--ink-3); }
</style>
