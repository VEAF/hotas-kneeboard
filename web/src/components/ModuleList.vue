<script setup lang="ts">
import { computed, ref } from 'vue'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import { useStore } from '../lib/store'
import { t } from '../lib/i18n'

const store = useStore()
const { state } = store
const search = ref<{ $el: HTMLInputElement } | null>(null)

const shown = computed(() => {
  const q = state.filter.trim().toLowerCase()
  return store.profiles.value.filter(
    (p) => !q || [p.display_name, p.name, p.unit_type ?? ''].some((s) => s.toLowerCase().includes(q)),
  )
})

function exportedCount(name: string): [number, number] {
  const p = store.profiles.value.find((x) => x.name === name)
  if (!p) return [0, 0]
  return [p.devices.filter((d) => store.isExported(p.name, d)).length, p.devices.filter((d) => !store.isHidden(d.name)).length]
}

function select(name: string) {
  state.profileName = name
  state.deviceKey = store.orderedDevices(store.profile.value)[0]?.full_name ?? ''
}

defineExpose({ focusSearch: () => search.value?.$el.focus(), shown })
</script>

<template>
  <section class="col" :aria-label="t('modules.title')">
    <header class="colhead">
      <span class="eyebrow">{{ t('modules.title') }}</span>
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          ref="search"
          v-model="state.filter"
          size="small"
          :placeholder="`${t('common.filter')}   /`"
          :aria-label="t('modules.filter')"
          fluid
          @keydown.esc="($event.target as HTMLInputElement).blur()"
        />
      </IconField>
    </header>
    <div class="list" role="listbox" :aria-label="t('modules.title')">
      <div
        v-for="p in shown"
        :key="p.name"
        class="row"
        :class="{ on: p.name === state.profileName }"
        role="option"
        :aria-selected="p.name === state.profileName"
        tabindex="-1"
        @click="select(p.name)"
      >
        <span class="meta">
          <span class="t" v-tooltip.right="p.display_name !== p.name ? t('modules.profile', { name: p.name }) : undefined">{{ p.display_name }}</span>
          <span class="s">
            <template v-if="p.display_name !== p.name && !p.display_name.includes(`(${p.name})`)">{{ p.name }} · </template>
            <template v-if="!p.found">{{ t('modules.not_installed') }}</template>
            <template v-else-if="p.unit_type">{{ t('modules.kneeboard', { unit: p.unit_type }) }}</template>
            <template v-else>{{ t('modules.no_aircraft') }}</template>
          </span>
        </span>
        <span class="n" v-tooltip.right="t('modules.count')">
          {{ exportedCount(p.name)[0] }}/{{ exportedCount(p.name)[1] }}
        </span>
      </div>
      <p v-if="!shown.length && store.profiles.value.length" class="empty">{{ t('modules.none') }}</p>
    </div>
  </section>
</template>

<style scoped>
.row { grid-template-columns: minmax(0, 1fr) auto; }
</style>
