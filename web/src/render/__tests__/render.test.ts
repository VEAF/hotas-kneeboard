import { describe, expect, it } from 'vitest'
import { compareInputs, inputName, layerTags } from '../inputs'
import { approximateMeasurer, fitTexts, MIN_LABEL_SIZE, wrap } from '../text'
import { cutsOf, devicePages, diagramPage, diagramPages, entriesByInput, listPages, type PageContext } from '../page'
import type { Device, Template } from '../../lib/types'

const device: Device = {
  full_name: 'Throttle - HOTAS Warthog {8F576560-6142-11ef-8006-444553540000}',
  name: 'Throttle - HOTAS Warthog',
  guid: '{8F576560-6142-11ef-8006-444553540000}',
  source: 'effective',
  error: null,
  layers: ['', 'Paddle'],
  binding_count: 5,
  auto_template_id: 'warthog',
  dcs_disabled: false,
  inputs: {
    JOY_BTN17: { '': { text: 'LG Handle - UP / DN', pressed: ['LG Handle - UP'], released: ['LG Handle - DN'] } },
    JOY_BTN2: {
      '': { text: 'IFF IN', pressed: ['IFF IN'], released: [] },
      Paddle: { text: 'IFF OUT', pressed: ['IFF OUT'], released: [] },
    },
    JOY_BTN9: { '': { text: 'Switch Released', pressed: [], released: ['Switch Released'] } },
    JOY_Z: { '': { text: 'Throttle <Right>', pressed: ['Throttle <Right>'], released: [] } },
  },
}

const template: Template = {
  id: 'warthog',
  name: 'Warthog',
  devices: ['Throttle - HOTAS Warthog'],
  size: [800, 1000],
  credits: { author: 'Joystick Diagrams contributors', license: 'GPL-2.0' },
  image: 'background.svg',
  user: false,
  checked: null,
  inputs: {
    JOY_BTN17: { box: [10, 10, 120, 24] },
    JOY_BTN2: { box: [10, 60, 120, 24], more_boxes: [[300, 60, 120, 24]] },
    JOY_BTN9: { box: [10, 120, 120, 24] },
    JOY_BTN30: { box: [10, 200, 120, 24] },
    JOY_Z: { box: [600, 992, 40, 6], anchor: [700, 500] },
  },
}

const ctx = (layer: string | null, withTemplate = true): PageContext => ({
  profile: 'F-16C_50',
  device,
  template: withTemplate ? { data: template, image: 'data:image/svg+xml;base64,AA' } : null,
  layer,
  measurer: approximateMeasurer,
})

describe('inputs', () => {
  it('names inputs for a pilot', () => {
    expect(inputName('JOY_BTN14')).toBe('Bouton 14')
    expect(inputName('JOY_BTN_POV1_UL')).toBe('Hat 1 ↖')
    expect(inputName('JOY_RZ')).toBe('Axe RZ')
    expect(inputName('JOY_SLIDER2')).toBe('Curseur 2')
  })

  it('orders buttons, then hats in compass order, then axes', () => {
    const keys = ['JOY_Z', 'JOY_BTN_POV1_L', 'JOY_BTN10', 'JOY_BTN_POV1_U', 'JOY_BTN2']
    expect(keys.sort(compareInputs)).toEqual(['JOY_BTN2', 'JOY_BTN10', 'JOY_BTN_POV1_U', 'JOY_BTN_POV1_L', 'JOY_Z'])
  })

  it('gives each layer a short unique tag', () => {
    const tags = layerTags(['', 'Paddle', 'Pinky', 'JOY_BTN5', 'JOY_BTN5 + Paddle'])
    expect(tags.get('Paddle')).toBe('P')
    expect(tags.get('Pinky')).toBe('PI')
    expect(tags.get('JOY_BTN5')).toBe('B5')
    expect(tags.get('JOY_BTN5 + Paddle')).toBe('B5+P')
    expect(tags.has('')).toBe(false)
  })
})

describe('text', () => {
  it('wraps on words and keeps a long word whole', () => {
    expect(wrap('Landing Gear Up / Down', 10, 50, approximateMeasurer)).toEqual(['Landing', 'Gear Up /', 'Down'])
    expect(wrap('Supercalifragilistic', 10, 20, approximateMeasurer)).toEqual(['Supercalifragilistic'])
  })

  it('shrinks the text to fit, down to the floor', () => {
    const roomy = fitTexts(['Fire'], (t) => t, () => 0, 100, 20, approximateMeasurer)
    expect(roomy.size).toBe(11)
    const tight = fitTexts(['A very long command name that cannot fit'], (t) => t, () => 0, 40, 10, approximateMeasurer)
    expect(tight.size).toBe(MIN_LABEL_SIZE)
    expect(tight.height).toBeGreaterThan(10)
  })
})

describe('pages', () => {
  it('lists the entries of each input in layer order, or of one layer', () => {
    const all = entriesByInput(device, null)
    expect([...all.keys()]).toEqual(['JOY_BTN2', 'JOY_BTN9', 'JOY_BTN17', 'JOY_Z'])
    expect(all.get('JOY_BTN2')!.map((e) => e.layer)).toEqual(['', 'Paddle'])
    expect(all.get('JOY_BTN9')![0]).toMatchObject({ text: 'relâché : Switch Released', released: true })
    expect([...entriesByInput(device, 'Paddle').keys()]).toEqual(['JOY_BTN2'])
  })

  it('draws a label in every box of an input, an empty box for a free one, the rest under the drawing', () => {
    const page = diagramPage(ctx(null))
    expect(page.svg.match(/>IFF IN</g)).toHaveLength(2) // box and more_boxes
    expect(page.svg).toContain('>IFF OUT<')
    expect(page.svg).toContain('stroke-dasharray') // JOY_BTN30, not bound
    expect(page.svg).not.toContain('HORS GABARIT') // every bound input has a box
    expect(page.svg).toContain('&lt;Right&gt;') // escaped
    expect(page.svg).toContain('x2="700" y2="500"') // leader line to the anchor
    expect(page.svg).toContain('P = Paddle')
    expect(page.title).toBe('Throttle - HOTAS Warthog')
  })

  it('keeps a grown box on the drawing and draws it last', () => {
    const svg = diagramPage(ctx(null)).svg
    // JOY_Z's box (40 x 6 at y 992) grows: it moves up to end at the drawing's bottom (1000)
    const rect = svg.match(/<rect x="600" y="([\d.]+)" width="40" height="([\d.]+)"/)!
    expect(Number(rect[1]) + Number(rect[2])).toBeCloseTo(1000)
    expect(svg.lastIndexOf('x="600"')).toBeGreaterThan(svg.lastIndexOf('IFF OUT'))
  })

  it('lists the bound inputs without a box under the drawing', () => {
    const { JOY_Z: _, ...inputs } = template.inputs
    const page = diagramPage({ ...ctx(null), template: { data: { ...template, inputs }, image: 'x' } })
    expect(page.svg).toContain('HORS GABARIT')
    expect(page.svg).toContain('Axe Z')
    expect(page.height).toBeGreaterThan(1000)
  })

  it('cuts a drawing into pages where its template says', () => {
    // JOY_Z without box: the band of bindings without box has something to show
    const { JOY_Z: _z, ...inputs } = template.inputs
    const wide: Template = { ...template, size: [2000, 1000], inputs, split_at: [1080] }
    const cut = 1080
    const pages = diagramPages({ ...ctx(null), template: { data: wide, image: 'x' } }, true)
    expect(pages.map((p) => p.title)).toEqual(['Throttle - HOTAS Warthog (1/2)', 'Throttle - HOTAS Warthog (2/2)'])
    expect(pages[0].width).toBe(cut)
    expect(pages[1].width).toBe(2000 - cut)
    expect(pages[1].svg).toContain(`viewBox="${cut} 0 ${2000 - cut} 1000"`)
    expect(pages[0].svg).not.toContain('HORS GABARIT') // the bindings without box go on the last page
    expect(pages[1].svg).toContain('HORS GABARIT')
    // not cut when asked so, nor when the template says nothing
    expect(diagramPages({ ...ctx(null), template: { data: wide, image: 'x' } }, false)).toHaveLength(1)
    expect(diagramPages(ctx(null), true)).toHaveLength(1)
    // cuts outside the drawing are ignored, two cuts make three pages
    expect(cutsOf({ ...wide, split_at: [-5, 2500, 1500, 500, 500] })).toEqual([500, 1500])
    expect(diagramPages({ ...ctx(null), template: { data: { ...wide, split_at: [500, 1500] }, image: 'x' } }, true)).toHaveLength(3)
  })

  it('makes one page per layer in split mode', () => {
    const pages = devicePages({ ...ctx(null), layer: undefined } as never, 'split')
    expect(pages.map((p) => p.title)).toEqual(['Throttle - HOTAS Warthog', 'Throttle - HOTAS Warthog (Paddle)'])
    expect(pages[1].svg).toContain('>IFF OUT<')
    expect(pages[1].svg).not.toContain('>IFF IN<')
  })

  it('makes list pages without template, continued when long', () => {
    const many: Device = {
      ...device,
      inputs: Object.fromEntries(
        Array.from({ length: 80 }, (_, i) => [`JOY_BTN${i + 1}`, { '': { text: `Command ${i + 1}`, pressed: [`Command ${i + 1}`], released: [] } }]),
      ),
    }
    const pages = listPages({ ...ctx(null, false), device: many })
    expect(pages.length).toBeGreaterThan(1)
    expect(pages[1].title).toBe('Throttle - HOTAS Warthog (suite 2)')
    expect(pages.map((p) => p.svg).join('')).toContain('>Command 80<')
    expect(pages[0].svg).toContain('Bouton 1')
  })
})
