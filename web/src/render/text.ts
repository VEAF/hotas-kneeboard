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
  /** width of the widest line (with its chip), which may exceed the box at the smallest size */
  width: number
}

export const MAX_LABEL_SIZE = 11
export const MIN_LABEL_SIZE = 6.5
const LINE_SPACING = 1.12

export interface TextSizes {
  max: number
  min: number
}

export const DEFAULT_SIZES: TextSizes = { max: MAX_LABEL_SIZE, min: MIN_LABEL_SIZE }

/** The same measurer, for another weight (bold labels are wider) */
export function weighted(measurer: Measurer, weight: number): Measurer {
  return { width: (text, size, w = weight) => measurer.width(text, size, w) }
}

/** Largest size from `sizes.max` down to `sizes.min` at which every text fits the box. The text
 * never goes below `sizes.min`: when it still does not fit, it overflows and the box grows. */
export function fitTexts<T>(
  items: T[],
  textOf: (item: T) => string,
  indentOf: (item: T, size: number) => number,
  width: number,
  height: number,
  measurer: Measurer,
  sizes: TextSizes = DEFAULT_SIZES,
): Fit<T> {
  let fit: Fit<T> | null = null
  for (let step = Math.max(sizes.max, sizes.min); ; step -= 0.5) {
    const size = Math.max(step, sizes.min)
    const blocks = items.map((item) => ({
      item,
      lines: wrap(textOf(item), size, width, measurer, indentOf(item, size)),
    }))
    const lineCount = blocks.reduce((n, b) => n + b.lines.length, 0)
    const widest = Math.max(
      0,
      ...blocks.flatMap((b) => b.lines.map((l, i) => measurer.width(l, size) + (i === 0 ? indentOf(b.item, size) : 0))),
    )
    fit = { size, lineHeight: size * LINE_SPACING, blocks, height: lineCount * size * LINE_SPACING, width: widest }
    if ((fit.height <= height && widest <= width) || size <= sizes.min) break
  }
  return fit as Fit<T>
}
