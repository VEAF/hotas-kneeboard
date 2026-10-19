<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'
import type { ExportProgress } from '../lib/exportAll'

const props = defineProps<{ progress: ExportProgress | null }>()
const emit = defineEmits<{ stop: [] }>()

const percent = computed(() => (props.progress ? Math.round((100 * props.progress.done) / props.progress.total) : 0))
</script>

<template>
  <Dialog
    :visible="!!progress"
    modal
    :closable="false"
    :close-on-escape="false"
    :header="progress?.title"
    :style="{ width: 'min(460px, 94vw)' }"
  >
    <template v-if="progress">
      <p class="where" role="status">
        <span>{{ progress.done < progress.total ? `Module ${progress.done + 1} sur ${progress.total}` : `${progress.total} modules` }}</span>
        <strong>{{ progress.module }}</strong>
      </p>
      <ProgressBar :value="percent" :show-value="false" style="height: 8px" />
      <p v-if="progress.stopping" class="note">Arrêt à la fin de ce module…</p>
    </template>
    <template #footer>
      <Button label="Arrêter" severity="secondary" outlined :disabled="progress?.stopping" @click="emit('stop')" />
    </template>
  </Dialog>
</template>

<style scoped>
.where { display: flex; justify-content: space-between; gap: 12px; margin: 0 0 12px; }
.where span { color: var(--ink-2); }
.note { margin: 12px 0 0; color: var(--ink-2); }
</style>
