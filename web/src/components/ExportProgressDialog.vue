<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'
import type { ExportProgress } from '../lib/exportAll'
import { t } from '../lib/i18n'

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
        <span>{{ progress.done < progress.total ? t('progress.module', { n: progress.done + 1, total: progress.total }) : t('progress.done', { total: progress.total }) }}</span>
        <strong>{{ progress.module }}</strong>
      </p>
      <ProgressBar :value="percent" :show-value="false" style="height: 8px" />
      <p v-if="progress.stopping" class="note">{{ t('progress.stopping') }}</p>
    </template>
    <template #footer>
      <Button :label="t('progress.stop')" severity="secondary" outlined :disabled="progress?.stopping" @click="emit('stop')" />
    </template>
  </Dialog>
</template>

<style scoped>
.where { display: flex; justify-content: space-between; gap: 12px; margin: 0 0 12px; }
.where span { color: var(--ink-2); }
.note { margin: 12px 0 0; color: var(--ink-2); }
</style>
