<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { useStore } from '../lib/store'
import { PROGRAM_COLORS } from '../render/programs'
import { t, tn } from '../lib/i18n'
import Tr from './Tr'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const { state } = store

const install = ref('')
const savedGames = ref('')
const pageHeight = ref<number | null>(1024)
const language = ref('auto')
// DCS's l10n folders
const languages = computed(() => [
  { label: t('settings.language.game'), value: 'auto' },
  ...Object.entries({ en: 'English', fr: 'Français', de: 'Deutsch', es: 'Español', it: 'Italiano', ru: 'Русский', pl: 'Polski', cs: 'Čeština', cn: '中文', jp: '日本語', ko: '한국어' }).map(
    ([value, label]) => ({ label, value }),
  ),
])
// the interface's own languages, named in their language
const uiLanguages = computed(() => [
  { label: t('settings.ui_language.auto'), value: 'auto' },
  { label: 'Français', value: 'fr' },
  { label: 'English', value: 'en' },
])
const tab = ref('general')
const deviceFilter = ref('')
const shownDevices = computed(() => {
  const q = deviceFilter.value.trim().toLowerCase()
  return store.allDevices.value.filter((d) => !q || d.name.toLowerCase().includes(q))
})
const hiddenTotal = computed(() => store.allDevices.value.filter((d) => store.isHidden(d.name)).length)
const saving = ref(false)
const error = ref('')

// --- other programs ------------------------------------------------------------------------------
const srsDir = ref('')
const srsSaving = ref(false)
const srsError = ref('')
async function saveSrsDir() {
  srsSaving.value = true
  srsError.value = ''
  try {
    await store.saveSrsDir(srsDir.value.trim() || null)
  } catch (e) {
    srsError.value = (e as Error).message
  } finally {
    srsSaving.value = false
  }
}

watch(visible, (open) => {
  if (!open || !state.settings) return
  srsDir.value = state.settings.srs_dir ?? ''
  srsError.value = ''
  install.value = state.settings.dcs_install_dir ?? ''
  savedGames.value = state.settings.saved_games_dir ?? ''
  pageHeight.value = state.settings.page_height
  language.value = state.settings.language ?? 'auto'
  error.value = ''
})

async function save() {
  saving.value = true
  error.value = ''
  try {
    // an emptied number field gives null: the server would refuse it, and the export break
    if (!pageHeight.value) throw new Error(t('settings.page_height.missing'))
    store.changeSettings({ page_height: pageHeight.value })
    const reading = {
      dcs_install_dir: install.value.trim() || null,
      saved_games_dir: savedGames.value.trim() || null,
      language: language.value === 'auto' ? null : language.value,
    }
    const current = state.settings
    if (current && (Object.keys(reading) as (keyof typeof reading)[]).some((k) => reading[k] !== current[k])) {
      await store.saveReading(reading)
    }
    visible.value = false
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('settings.title')" :style="{ width: 'min(640px, 94vw)' }">
    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="general">{{ t('settings.tab.general') }}</Tab>
        <Tab value="devices">{{ t('settings.tab.devices') }}<span v-if="hiddenTotal" class="tab-count">{{ tn('settings.hidden', hiddenTotal) }}</span></Tab>
        <Tab value="programs">{{ t('settings.tab.programs') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="general">
    <label class="field immediate" for="ui-language">
      <span class="eyebrow">{{ t('settings.ui_language.label') }}</span>
      <Select input-id="ui-language" :model-value="state.settings?.ui_language ?? 'auto'" :options="uiLanguages" option-label="label" option-value="value" @update:model-value="(v: string) => store.setUiLanguage(v === 'auto' ? null : v)" />
      <small>{{ t('settings.ui_language.hint') }}</small>
    </label>
    <form class="form" @submit.prevent="save">
      <label class="field" for="install-dir">
        <span class="eyebrow">{{ t('settings.install.label') }}</span>
        <InputText id="install-dir" v-model="install" :placeholder="state.dcs?.install_detected ? (state.dcs?.install_dir ?? t('settings.not_found')) : ''" fluid />
        <small>{{ t('settings.install.empty') }}<template v-if="state.dcs?.install_detected && state.dcs.install_dir"> ({{ state.dcs.install_dir }})</template>.</small>
      </label>
      <label class="field" for="saved-games-dir">
        <span class="eyebrow">{{ t('settings.saved_games.label') }}</span>
        <InputText id="saved-games-dir" v-model="savedGames" :placeholder="state.dcs?.saved_games_detected ? (state.dcs?.saved_games_dir ?? t('settings.not_found')) : ''" fluid />
        <small><Tr k="settings.saved_games.empty"><template #path><code>Saved Games\DCS</code></template></Tr><template v-if="state.dcs?.saved_games_detected && state.dcs.saved_games_dir"> ({{ state.dcs.saved_games_dir }})</template>.</small>
      </label>
      <label class="field" for="language">
        <span class="eyebrow">{{ t('settings.language.label') }}</span>
        <Select input-id="language" v-model="language" :options="languages" option-label="label" option-value="value" />
        <small><Tr k="settings.language.hint"><template #l10n><code>l10n</code></template></Tr><template v-if="state.dcs"> {{ t('settings.language.current', { language: state.dcs.language }) }}</template>.</small>
      </label>
      <label class="field" for="page-height">
        <span class="eyebrow">{{ t('settings.page_height.label') }}</span>
        <InputNumber id="page-height" v-model="pageHeight" :min="256" :max="4096" :step="128" show-buttons :use-grouping="false" />
        <small>{{ t('settings.page_height.hint') }}</small>
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions">
        <Button type="button" :label="t('common.cancel')" severity="secondary" text @click="visible = false" />
        <Button type="submit" :label="t('common.save')" :loading="saving" />
      </div>
    </form>
    <label class="check immediate" for="split-wide">
      <Checkbox input-id="split-wide" :model-value="state.settings?.split_wide ?? true" binary @update:model-value="(v: boolean) => store.changeSettings({ split_wide: v })" />
      <span>{{ t('settings.split_wide.label') }} <small>{{ t('settings.split_wide.hint') }}</small></span>
    </label>
        </TabPanel>
        <TabPanel value="devices">
          <div class="form">
            <p class="intro">
              {{ t('settings.devices.intro') }}
            </p>
            <InputText v-model="deviceFilter" size="small" :placeholder="t('common.filter')" :aria-label="t('settings.devices.filter')" />
            <div class="device-list">
              <label v-for="d in shownDevices" :key="d.name" class="device-row" :for="`show-${d.name}`">
                <Checkbox :input-id="`show-${d.name}`" :model-value="!store.isHidden(d.name)" binary @update:model-value="(v: boolean) => store.setHidden(d.name, !v)" />
                <span class="device-name">{{ d.name }}</span>
                <span class="device-modules">{{ tn('settings.devices.modules', d.modules) }}</span>
              </label>
              <p v-if="!shownDevices.length" class="intro">{{ t('settings.devices.none') }}</p>
            </div>
            <div class="actions">
              <Button type="button" size="small" text :label="t('settings.devices.show_all')" :disabled="!hiddenTotal" @click="store.changeSettings({ hidden_devices: [] })" />
            </div>
          </div>
        </TabPanel>
        <TabPanel value="programs">
          <div class="form">
            <p class="intro">
              {{ t('settings.programs.intro') }}
            </p>
            <form class="field" @submit.prevent="saveSrsDir">
              <label class="eyebrow" for="srs-dir">{{ t('settings.srs.label') }}</label>
              <div class="with-button">
                <InputText id="srs-dir" v-model="srsDir" :placeholder="state.programs?.srs.folder ?? t('settings.not_found')" fluid />
                <Button type="submit" size="small" :label="t('common.apply')" :loading="srsSaving" />
              </div>
              <small>
                {{ t('settings.srs.empty') }}<template v-if="state.programs?.srs.folder">
                  ({{ tn('settings.srs.profiles', state.programs.srs.profiles.length, { folder: state.programs.srs.folder }) }})</template>.
              </small>
            </form>
            <p class="intro">
              VectorXR :
              <template v-if="state.programs?.vectorxr.file"><Tr k="settings.vectorxr.read" :n="state.programs.vectorxr.bindings.length"><template #file><code>{{ state.programs.vectorxr.file }}</code></template></Tr></template>
              <template v-else>{{ t('settings.vectorxr.missing') }}</template>
            </p>
            <p v-for="problem in [...(state.programs?.problems ?? []), ...(srsError ? [srsError] : [])]" :key="problem" class="error">{{ problem }}</p>
            <div class="device-list">
              <div v-for="p in store.programNames.value" :key="p" class="program-row">
                <Checkbox :input-id="`program-${p}`" :model-value="store.isProgramShown(p)" binary @update:model-value="(v: boolean) => store.setProgramShown(p, v)" />
                <label class="device-name" :for="`program-${p}`">
                  <span class="tag" :style="{ background: store.programStyles.value.get(p)?.color }">{{ store.programStyles.value.get(p)?.tag }}</span>
                  {{ p }}
                </label>
                <div class="swatches" role="radiogroup" :aria-label="t('settings.programs.color', { program: p })">
                  <button
                    v-for="c in PROGRAM_COLORS"
                    :key="c"
                    type="button"
                    class="swatch"
                    :class="{ on: store.programStyles.value.get(p)?.color === c }"
                    :style="{ background: c }"
                    role="radio"
                    :aria-checked="store.programStyles.value.get(p)?.color === c"
                    :aria-label="c"
                    @click="store.setProgramColor(p, c)"
                  />
                </div>
              </div>
              <p v-if="!store.programNames.value.length" class="intro">{{ t('settings.programs.none') }}</p>
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
    <p class="file"><Tr k="settings.file"><template #file><code>{{ state.settingsFile }}</code></template></Tr></p>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field small { color: var(--ink-3); }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.error { color: var(--bad); margin: 0; }
.form { padding-top: 14px; }
.intro { margin: 0; color: var(--ink-2); font-size: 13px; }
.device-list { display: flex; flex-direction: column; max-height: 340px; overflow: auto; border: 1px solid var(--line); border-radius: 6px; }
.device-row { display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 7px 10px; cursor: pointer; border-bottom: 1px solid var(--line); }
.device-row:last-child { border-bottom: 0; }
.device-row:hover { background: var(--panel-3); }
.device-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.device-modules { font-size: 12px; color: var(--ink-3); }
.tab-count { margin-left: 8px; font-size: 11px; color: var(--warn); }
.check { display: flex; gap: 10px; align-items: center; cursor: pointer; }
.check small { color: var(--ink-3); }
.check.immediate { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line); }
.with-button { display: flex; gap: 8px; align-items: center; }
.program-row { display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 7px 10px; border-bottom: 1px solid var(--line); }
.program-row:last-child { border-bottom: 0; }
.program-row .device-name { cursor: pointer; display: flex; gap: 8px; align-items: center; }
.tag { color: #fff; font: 700 11px var(--f-mono); border-radius: 3px; padding: 1px 5px; }
.swatches { display: flex; gap: 4px; }
.swatch { width: 18px; height: 18px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; padding: 0; }
.swatch.on { border-color: var(--ink); box-shadow: 0 0 0 1px var(--panel); }
.file { margin: 14px 0 0; font-size: 12px; color: var(--ink-3); overflow-wrap: anywhere; }
</style>
