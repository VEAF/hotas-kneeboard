import { describe, expect, it } from 'vitest'
import { marksFor, normalizeGuid, PROGRAM_COLORS, programStyles } from '../programs'
import { diagramPage, entriesByInput, listPages, pageLayers, type PageContext } from '../page'
import { approximateMeasurer } from '../text'
import type { Device, ProgramBinding, Template } from '../../lib/types'

const GUID = 'd281fb60-b9ad-11f0-8001-444553540000'

const device: Device = {
  full_name: `Orion Throttle {${GUID.toUpperCase()}}`,
  name: 'Orion Throttle',
  guid: `{${GUID.toUpperCase()}}`,
  source: 'effective',
  error: null,
  layers: ['', 'Paddle'],
  binding_count: 1,
  auto_template_id: null,
  dcs_disabled: false,
  inputs: { JOY_BTN24: { Paddle: { text: 'Transmit UHF', pressed: ['Transmit UHF'], released: [] } } },
}

const bindings: ProgramBinding[] = [
  { program: 'SRS', device_guid: GUID, input: 'JOY_BTN24', action: 'Radio 1' },
  { program: 'VectorXR', device_guid: `{${GUID}}`, input: 'JOY_BTN55', action: 'Overlay' },
  { program: 'SRS', device_guid: 'another-device', input: 'JOY_BTN1', action: 'PTT radio' },
]

const template: Template = {
  id: 'orion',
  name: 'Orion',
  devices: ['Orion Throttle'],
  size: [800, 600],
  credits: {},
  image: 'background.svg',
  user: false,
  checked: null,
  inputs: { JOY_BTN24: { box: [10, 10, 200, 40] } },
}

describe('other programs', () => {
  it('keeps the buttons of this device, whatever the GUID is written like', () => {
    const marks = marksFor(device.guid, bindings, [])
    expect(marks).toEqual({ JOY_BTN24: [{ program: 'SRS', action: 'Radio 1' }], JOY_BTN55: [{ program: 'VectorXR', action: 'Overlay' }] })
    expect(normalizeGuid(`{${GUID.toUpperCase()}}`)).toBe(GUID)
  })

  it('leaves out the programs the user hides', () => {
    expect(Object.keys(marksFor(device.guid, bindings, ['SRS']))).toEqual(['JOY_BTN55'])
  })

  it('gives each program a tag and a colour, the user choice first, then a free one', () => {
    const styles = programStyles(['SRS', 'VectorXR', 'VoiceAttack', 'Voicemeeter'], { VectorXR: PROGRAM_COLORS[3] })
    expect(styles.get('SRS')).toEqual({ tag: 'SRS', color: PROGRAM_COLORS[0] })
    expect(styles.get('VectorXR')).toEqual({ tag: 'VXR', color: PROGRAM_COLORS[3] })
    expect(styles.get('VoiceAttack')?.tag).toBe('VOI')
    expect(styles.get('Voicemeeter')?.tag).toBe('VOI2')
    const colors = [...styles.values()].map((s) => s.color)
    expect(new Set(colors).size).toBe(colors.length)
  })

  const ctx = (layer: string | null, withTemplate = true): PageContext => ({
    profile: 'F-16C_50',
    device,
    template: withTemplate ? { data: template, image: 'data:image/svg+xml;base64,AA' } : null,
    layer,
    measurer: approximateMeasurer,
    programs: { marks: marksFor(device.guid, bindings, []), styles: programStyles(['SRS', 'VectorXR'], {}) },
  })

  it('adds the programs after the DCS commands, on every layer', () => {
    const marks = ctx(null).programs!.marks
    expect(entriesByInput(device, null, marks).get('JOY_BTN24')?.map((e) => e.program ?? e.layer)).toEqual(['Paddle', 'SRS'])
    // on the base layer's page of split mode, the paddle's command goes, SRS stays
    expect(entriesByInput(device, '', marks).get('JOY_BTN24')?.map((e) => e.text)).toEqual(['Radio 1'])
    expect(pageLayers(device, 'split')).toEqual(['', 'Paddle'])
  })

  it('draws them in their colour with their tag, in the box, under the drawing and in the legend', () => {
    const svg = diagramPage(ctx(null)).svg
    expect(svg).toContain(`fill="${PROGRAM_COLORS[0]}"`)
    expect(svg).toContain('>Radio 1<')
    expect(svg).toContain('>SRS<')
    // no box for button 55: in the band under the drawing
    expect(svg).toContain('Bouton 55')
    expect(svg).toContain('>Overlay<')
    expect(svg).toMatch(/SRS {3}VXR = VectorXR/)
    // a page of one layer still shows the programs, with their tag
    expect(diagramPage(ctx('Paddle')).svg).toContain('>VXR<')
  })

  it('lists them on a page without template', () => {
    const svg = listPages(ctx(null, false))[0].svg
    expect(svg).toContain('>Radio 1<')
    expect(svg).toContain('Bouton 55')
  })
})
