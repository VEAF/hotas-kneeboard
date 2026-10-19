import { describe, expect, it } from 'vitest'
import { exportableModules, failuresDetail } from '../exportAll'
import type { Device, Profile } from '../types'
import { lang } from '../i18n'

const device = (full_name: string) => ({ full_name, name: full_name }) as Device
const profile = (name: string, unit_type: string | null, devices: Device[]) =>
  ({ name, unit_type, found: true, devices }) as Profile

describe('exportableModules', () => {
  const stick = device('Stick')
  const pedals = device('Pedals')
  const profiles = [
    profile('A-10C II', 'A-10C_2', [stick, pedals]),
    profile('UiLayer', null, [stick]),
    profile('F-16C_50', 'F-16C_50', [pedals]),
    profile('Ka-50 III', 'Ka-50_3', [stick]),
  ]
  // the pedals are ticked off in the F-16 only
  const isExported = (p: string, d: Device) => !(p === 'F-16C_50' && d === pedals)

  it('keeps the aircraft with a device ticked, in the list order', () => {
    expect(exportableModules(profiles, isExported).map((p) => p.name)).toEqual(['A-10C II', 'Ka-50 III'])
  })

  it('leaves out a module that is not an aircraft, even with devices ticked', () => {
    expect(exportableModules(profiles, () => true).map((p) => p.name)).not.toContain('UiLayer')
  })
})

describe('failuresDetail', () => {
  it('says which module failed and why, with the typography of the language', () => {
    lang.value = 'fr'
    expect(failuresDetail([{ module: 'F-16C_50', error: 'disque plein' }])).toBe('F-16C_50 : disque plein')
    lang.value = 'en'
    expect(failuresDetail([{ module: 'F-16C_50', error: 'disk full' }])).toBe('F-16C_50: disk full')
  })
})
