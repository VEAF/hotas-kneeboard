<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import { useStore } from '../lib/store'

const visible = defineModel<boolean>('visible', { required: true })
const store = useStore()
const { state } = store

const install = ref('')
const savedGames = ref('')
const pageHeight = ref(1024)
const saving = ref(false)
const error = ref('')

watch(visible, (open) => {
  if (!open || !state.settings) return
  install.value = state.settings.dcs_install_dir ?? ''
  savedGames.value = state.settings.saved_games_dir ?? ''
  pageHeight.value = state.settings.page_height
  error.value = ''
})

async function save() {
  saving.value = true
  error.value = ''
  try {
    store.changeSettings({ page_height: pageHeight.value })
    const folders: [string | null, string | null] = [install.value.trim() || null, savedGames.value.trim() || null]
    if (folders[0] !== state.settings?.dcs_install_dir || folders[1] !== state.settings?.saved_games_dir) {
      await store.saveFolders(...folders)
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
  <Dialog v-model:visible="visible" modal header="Réglages" :style="{ width: 'min(620px, 94vw)' }">
    <form class="form" @submit.prevent="save">
      <label class="field" for="install-dir">
        <span class="eyebrow">Dossier d'installation de DCS</span>
        <InputText id="install-dir" v-model="install" :placeholder="state.dcs?.install_detected ? (state.dcs?.install_dir ?? 'non trouvé') : ''" fluid />
        <small>Vide : trouvé dans le registre Windows<template v-if="state.dcs?.install_detected && state.dcs.install_dir"> ({{ state.dcs.install_dir }})</template>.</small>
      </label>
      <label class="field" for="saved-games-dir">
        <span class="eyebrow">Dossier Saved Games de DCS</span>
        <InputText id="saved-games-dir" v-model="savedGames" :placeholder="state.dcs?.saved_games_detected ? (state.dcs?.saved_games_dir ?? 'non trouvé') : ''" fluid />
        <small>Vide : <code>Saved Games\DCS</code> de ton profil Windows<template v-if="state.dcs?.saved_games_detected && state.dcs.saved_games_dir"> ({{ state.dcs.saved_games_dir }})</template>.</small>
      </label>
      <label class="field" for="page-height">
        <span class="eyebrow">Hauteur des pages kneeboard (pixels)</span>
        <InputNumber id="page-height" v-model="pageHeight" :min="256" :max="4096" :step="128" show-buttons :use-grouping="false" />
        <small>La largeur suit les proportions du dessin.</small>
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions">
        <Button type="button" label="Annuler" severity="secondary" text @click="visible = false" />
        <Button type="submit" label="Enregistrer" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field small { color: var(--ink-3); }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.error { color: var(--bad); margin: 0; }
</style>
