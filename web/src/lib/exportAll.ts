import type { Device, Profile } from './types'

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
  return failures.map((f) => `${f.module} : ${f.error}`).join('\n')
}
