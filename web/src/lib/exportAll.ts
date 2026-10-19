import type { Device, Profile } from './types'
import { t } from './i18n'

/** The modules "all the modules" exports, in the order of the module list: an aircraft (it has a
 * kneeboard folder; Default, UiLayer and the like are left out) with at least one device ticked.
 * The same set for the kneeboard and the PDF. */
export function exportableModules(
  profiles: Profile[],
  isExported: (profileName: string, d: Device) => boolean,
): Profile[] {
  return profiles.filter((p) => !!p.unit_type && p.devices.some((d) => isExported(p.name, d)))
}

export interface ModuleFailure {
  module: string
  error: string
}

/** One line for the end of an export of all the modules */
export function failuresDetail(failures: ModuleFailure[]): string {
  return failures.map((f) => `${f.module}${t('common.colon')}${f.error}`).join('\n')
}

/** An export of all the modules in progress (ExportProgressDialog) */
export interface ExportProgress {
  title: string // "Kneeboard of every module"
  done: number // modules finished
  total: number
  module: string // the one in progress, or the last step ("Writing the PDF…")
  stopping: boolean // Stop was clicked: the module in progress ends first
}
