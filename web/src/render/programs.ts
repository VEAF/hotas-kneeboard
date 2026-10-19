// Buttons other programs use (SRS, VectorXR, entered by hand): which ones land on a device, and
// how each program is drawn (a tag and a colour, like a modifier layer).

import type { ProgramBinding } from '../lib/types'

export interface ProgramStyle {
  tag: string
  color: string
}

export interface ProgramMark {
  program: string
  action: string
}

/** input (JOY_BTN24) -> what other programs do with it */
export type ProgramMarks = Record<string, ProgramMark[]>

export const SRS = 'SRS'

/** Colours that stay readable on the kneeboard's white paper, apart from the layers' ones */
export const PROGRAM_COLORS = ['#1d5fbf', '#2f7d32', '#8a5a00', '#a12a8f', '#3f4a5a', '#c0392b']
const KNOWN: Record<string, ProgramStyle> = {
  SRS: { tag: 'SRS', color: '#1d5fbf' },
  VectorXR: { tag: 'VXR', color: '#2f7d32' },
}

export function normalizeGuid(guid: string): string {
  return guid.trim().replace(/^\{|\}$/g, '').toLowerCase()
}

/** Tag and colour of each program: the user's colour, else its own, else the first one free */
export function programStyles(programs: string[], colors: Record<string, string>): Map<string, ProgramStyle> {
  const styles = new Map<string, ProgramStyle>()
  const usedTags = new Set<string>()
  const usedColors = new Set(programs.map((p) => colors[p] ?? KNOWN[p]?.color).filter(Boolean))
  for (const program of programs) {
    let tag = KNOWN[program]?.tag ?? (program.replace(/[^A-Za-z0-9]/g, '').slice(0, 3).toUpperCase() || '?')
    for (let n = 2; usedTags.has(tag); n++) tag = `${tag.slice(0, 3)}${n}`
    usedTags.add(tag)
    let color = colors[program] ?? KNOWN[program]?.color
    if (!color) {
      color = PROGRAM_COLORS.find((c) => !usedColors.has(c)) ?? PROGRAM_COLORS[styles.size % PROGRAM_COLORS.length]
      usedColors.add(color)
    }
    styles.set(program, { tag, color })
  }
  return styles
}

/** What other programs do on one device's inputs, programs hidden by the user left out */
export function marksFor(deviceGuid: string, bindings: ProgramBinding[], hidden: string[]): ProgramMarks {
  const guid = normalizeGuid(deviceGuid)
  const marks: ProgramMarks = {}
  for (const b of bindings) {
    if (normalizeGuid(b.device_guid) !== guid || hidden.includes(b.program)) continue
    const list = (marks[b.input] ??= [])
    if (!list.some((m) => m.program === b.program && m.action === b.action)) list.push({ program: b.program, action: b.action })
  }
  return marks
}
