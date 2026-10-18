// How inputs and layers are named on a page.

const HAT_ARROWS: Record<string, string> = {
  U: '↑',
  UR: '↗',
  R: '→',
  DR: '↘',
  D: '↓',
  DL: '↙',
  L: '←',
  UL: '↖',
}
const HAT_ORDER = Object.keys(HAT_ARROWS)

/** "JOY_BTN14" -> "Bouton 14", "JOY_BTN_POV1_U" -> "Hat 1 ↑", "JOY_RZ" -> "Axe RZ" */
export function inputName(key: string): string {
  let m: RegExpMatchArray | null
  if ((m = key.match(/^JOY_BTN_POV(\d+)_([A-Z]+)$/))) return `Hat ${m[1]} ${HAT_ARROWS[m[2]] ?? m[2]}`
  if ((m = key.match(/^JOY_BTN(\d+)$/))) return `Bouton ${m[1]}`
  if ((m = key.match(/^JOY_SLIDER(\d+)$/))) return `Curseur ${m[1]}`
  if ((m = key.match(/^JOY_(R?[XYZ])$/))) return `Axe ${m[1]}`
  return key
}

/** Buttons, then hats (in compass order), then axes and the rest */
export function compareInputs(a: string, b: string): number {
  const rank = (key: string): [number, number, string] => {
    let m: RegExpMatchArray | null
    if ((m = key.match(/^JOY_BTN(\d+)$/))) return [0, Number(m[1]), '']
    if ((m = key.match(/^JOY_BTN_POV(\d+)_([A-Z]+)$/))) return [1, Number(m[1]) * 10 + HAT_ORDER.indexOf(m[2]), '']
    return [2, 0, key]
  }
  const [x, y] = [rank(a), rank(b)]
  return x[0] - y[0] || x[1] - y[1] || x[2].localeCompare(y[2])
}

export const BASE_LAYER = ''

/** Short tag of each modifier layer, unique on the page: "Paddle" -> "P", "JOY_BTN5" -> "B5" */
export function layerTags(layers: string[]): Map<string, string> {
  const tags = new Map<string, string>()
  const used = new Set<string>()
  for (const layer of layers) {
    if (layer === BASE_LAYER) continue
    const parts = layer.split(' + ').map((part) => {
      const button = part.match(/^JOY_BTN(\d+)$/)
      return button ? `B${button[1]}` : part
    })
    const short = parts.map((p) => (/^B\d+$/.test(p) ? p : p.replace(/[^A-Za-z0-9]/g, '')))
    let length = 1
    let tag = ''
    do {
      tag = short.map((p) => (/^B\d+$/.test(p) ? p : p.slice(0, length).toUpperCase() || '?')).join('+')
      length += 1
    } while (used.has(tag) && length <= Math.max(...short.map((p) => p.length)) + 1)
    if (used.has(tag)) tag = `${tag}${used.size}`
    used.add(tag)
    tags.set(layer, tag)
  }
  return tags
}

/** Colour of each modifier layer: orange, teal, violet, then again */
const LAYER_COLORS = ['#c46a00', '#0f7f7a', '#7a4cc2', '#b03a5b']
export function layerColor(index: number): string {
  return LAYER_COLORS[index % LAYER_COLORS.length]
}

export function layerLabel(layer: string): string {
  return layer === BASE_LAYER ? 'base' : layer
}
