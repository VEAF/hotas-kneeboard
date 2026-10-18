// Text measuring and wrapping for the SVG pages. SVG has no automatic line wrapping: lines are
// cut here, with the width the browser will give the text.

export const LABEL_FONT = '"Barlow Condensed", "Arial Narrow", sans-serif'
export const LABEL_WEIGHT = 600

export interface Measurer {
  width(text: string, size: number, weight?: number): number
}

/** Exact widths, from a canvas using the page's font (to call once the font is loaded). */
export function canvasMeasurer(): Measurer {
  const context = document.createElement('canvas').getContext('2d')
  if (!context) return approximateMeasurer
  const cache = new Map<string, number>()
  return {
    width(text, size, weight = LABEL_WEIGHT) {
      const key = `${weight}|${size}|${text}`
      let width = cache.get(key)
      if (width === undefined) {
        context.font = `${weight} ${size}px ${LABEL_FONT}`
        width = context.measureText(text).width
        cache.set(key, width)
      }
      return width
    },
  }
}

/** Average width of a condensed face: for tests, where there is no canvas. */
export const approximateMeasurer: Measurer = {
  width: (text, size) => text.length * size * 0.42,
}

/** Lines of at most `width`; the first one is `indent` shorter (room for a layer chip).
 * A word longer than a line stays whole on its own line (it overflows rather than vanishes). */
export function wrap(text: string, size: number, width: number, measurer: Measurer, indent = 0): string[] {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const candidate = line ? `${line} ${word}` : word
    const available = width - (lines.length === 0 ? indent : 0)
    if (!line || measurer.width(candidate, size) <= available) {
      line = candidate
    } else {
      lines.push(line)
      line = word
    }
  }
  if (line) lines.push(line)
  return lines
}

export interface FittedBlock<T> {
  item: T
  lines: string[]
}

export interface Fit<T> {
  size: number
  lineHeight: number
  blocks: FittedBlock<T>[]
  /** height of the text, which may exceed the box at the smallest size */
  height: number
}

export const MAX_LABEL_SIZE = 11
export const MIN_LABEL_SIZE = 6.5
const LINE_SPACING = 1.12

/** Largest size from MAX_LABEL_SIZE down to MIN_LABEL_SIZE at which every text fits the box. */
export function fitTexts<T>(
  items: T[],
  textOf: (item: T) => string,
  indentOf: (item: T, size: number) => number,
  width: number,
  height: number,
  measurer: Measurer,
): Fit<T> {
  let fit: Fit<T> | null = null
  for (let size = MAX_LABEL_SIZE; size >= MIN_LABEL_SIZE; size -= 0.5) {
    const blocks = items.map((item) => ({
      item,
      lines: wrap(textOf(item), size, width, measurer, indentOf(item, size)),
    }))
    const lineCount = blocks.reduce((n, b) => n + b.lines.length, 0)
    const widest = Math.max(
      0,
      ...blocks.flatMap((b) => b.lines.map((l, i) => measurer.width(l, size) + (i === 0 ? indentOf(b.item, size) : 0))),
    )
    fit = { size, lineHeight: size * LINE_SPACING, blocks, height: lineCount * size * LINE_SPACING }
    if (fit.height <= height && widest <= width) break
  }
  return fit as Fit<T>
}
