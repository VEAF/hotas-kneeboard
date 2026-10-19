// The inputs DCS names on a joystick, offered when placing an input

import { compareInputs, inputName } from '../render/inputs'
import { t } from '../lib/i18n'

const HATS = ['U', 'UR', 'R', 'DR', 'D', 'DL', 'L', 'UL']
export const AXES = ['JOY_X', 'JOY_Y', 'JOY_Z', 'JOY_RX', 'JOY_RY', 'JOY_RZ', 'JOY_SLIDER1', 'JOY_SLIDER2']
const BUTTON_COUNT = 128
const HAT_COUNT = 4

export interface CatalogGroup {
  label: string
  items: { label: string; value: string }[]
}

const GROUPS: { label: string; values: string[] }[] = [
  { label: 'editor.catalog.buttons', values: Array.from({ length: BUTTON_COUNT }, (_, i) => `JOY_BTN${i + 1}`) },
  { label: 'editor.catalog.hats', values: Array.from({ length: HAT_COUNT }, (_, h) => HATS.map((d) => `JOY_BTN_POV${h + 1}_${d}`)).flat() },
  { label: 'editor.catalog.axes', values: AXES },
]

/** The catalog in the interface's language (read it again when the language changes) */
export function catalog(): CatalogGroup[] {
  return GROUPS.map((g) => ({ label: t(g.label), items: g.values.map((v) => ({ value: v, label: inputName(v) })) }))
}

export const ALL_INPUTS = GROUPS.flatMap((g) => g.values)

/** First input of the catalog not used yet, after `after` when given (the next button) */
export function nextFree(used: Iterable<string>, after?: string): string {
  const taken = new Set(used)
  const start = after ? ALL_INPUTS.indexOf(after) + 1 : 0
  for (const key of [...ALL_INPUTS.slice(start), ...ALL_INPUTS.slice(0, start)]) {
    if (!taken.has(key)) return key
  }
  return ALL_INPUTS[0]
}

export function sortedKeys(keys: Iterable<string>): string[] {
  return [...keys].sort(compareInputs)
}
