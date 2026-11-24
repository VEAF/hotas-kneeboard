// Builds the pages of a device as SVG: the device drawing with a label per bound input, or a
// list when there is no template. The same SVG is shown on screen, drawn into the kneeboard PNG
// and into the PDF.

import type { Box, Device, Label, Template } from '../lib/types'
import { BASE_LAYER, compareInputs, inputName, layerColor, layerLabel, layerTags } from './inputs'
import { DEFAULT_SIZES, fitTexts, LABEL_FONT, LABEL_WEIGHT, MAX_LABEL_SIZE, weighted, wrap, type Measurer, type TextSizes } from './text'
import type { ProgramMarks, ProgramStyle } from './programs'
import { tIn, type Lang } from '../lib/i18n'

export interface Page {
  title: string
  width: number
  height: number
  svg: string
  /** the colour of its paper: what the margins of a kneeboard picture are filled with */
  paper: string
}

export interface PageContext {
  profile: string
  device: Device
  /** template and its picture as a data: URL; null for a list page */
  template: { data: Template; image: string } | null
  /** null: every layer on the page; a layer: only that one */
  layer: string | null
  measurer: Measurer
  /** @font-face rules to embed, so that the SVG renders the same once drawn as an image */
  fontCss?: string
  /** buttons other programs use on this device, and how each program is drawn */
  programs?: { marks: ProgramMarks; styles: Map<string, ProgramStyle> }
  /** the language of the page's own words: the commands' (pageLanguage); English when not told */
  lang?: Lang
  /** 'auto': the template's theme (light for a list page); else forced */
  theme?: 'auto' | 'light' | 'dark'
  /** labels: smallest size the text shrinks to, and bold or not */
  text?: { minSize?: number; bold?: boolean }
}

export type Theme = 'light' | 'dark'

/** What a page is drawn with */
interface Palette {
  dark: boolean
  paper: string
  ink: string
  muted: string
  rule: string
  softRule: string
  emptyStroke: string
}

const PALETTES: Record<Theme, Palette> = {
  light: { dark: false, paper: '#ffffff', ink: '#1b1f24', muted: '#5d6570', rule: '#c9ced5', softRule: '#e1e4e8', emptyStroke: '#9aa1aa' },
  dark: { dark: true, paper: '#1a1a1a', ink: '#f2f4f6', muted: '#a3abb5', rule: '#4a515a', softRule: '#2f353c', emptyStroke: '#6b737d' },
}

function themeOf(ctx: PageContext): Theme {
  if (ctx.theme === 'light' || ctx.theme === 'dark') return ctx.theme
  return ctx.template?.data.theme === 'dark' ? 'dark' : 'light'
}

/** The context with what the settings change: the weight measured is the weight drawn */
function styled(ctx: PageContext): PageContext {
  return { ...ctx, measurer: weighted(ctx.measurer, ctx.text?.bold ? BOLD_WEIGHT : LABEL_WEIGHT) }
}

function sizesOf(ctx: PageContext): TextSizes {
  const min = Math.max(ctx.text?.minSize ?? DEFAULT_SIZES.min, 1)
  return { max: Math.max(MAX_LABEL_SIZE, min), min }
}

interface Entry {
  layer: string
  text: string
  released: boolean
  /** another program's action, not a DCS command: on every layer, always with its tag */
  program?: string
}

const BOLD_WEIGHT = 700
const LIST_WIDTH = 827
const LIST_HEIGHT = 1169

export function esc(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}

function entryText(label: Label, language: Lang): { text: string; released: boolean } {
  if (label.pressed.length === 0 && label.released.length > 0) {
    return { text: tIn(language, 'page.released', { text: label.text }), released: true }
  }
  return { text: label.text, released: false }
}

/** Entries of each bound input, in layer order, filtered on one layer if asked; then what other
 * programs do with it, whatever the layer (they do not know DCS's modifiers) */
export function entriesByInput(device: Device, layer: string | null, marks: ProgramMarks = {}, language: Lang = 'en'): Map<string, Entry[]> {
  const result = new Map<string, Entry[]>()
  const keys = new Set([...Object.keys(device.inputs), ...Object.keys(marks)])
  for (const key of [...keys].sort(compareInputs)) {
    const labels = device.inputs[key] ?? {}
    const entries: Entry[] = device.layers
      .filter((l) => l in labels && (layer === null || l === layer))
      .map((l) => ({ layer: l, ...entryText(labels[l], language) }))
    for (const mark of marks[key] ?? []) entries.push({ layer: BASE_LAYER, text: mark.action, released: false, program: mark.program })
    if (entries.length) result.set(key, entries)
  }
  return result
}

/** Pages of a device: one per layer in split mode (each layer that has bindings) */
export function pageLayers(device: Device, mode: 'merge' | 'split'): (string | null)[] {
  return mode === 'merge' ? [null] : device.layers
}

function pageTitle(ctx: PageContext): string {
  return ctx.layer === null || ctx.layer === BASE_LAYER ? ctx.device.name : `${ctx.device.name} (${ctx.layer})`
}

function svgOpen(width: number, height: number, ctx: PageContext): string {
  const weight = ctx.text?.bold ? BOLD_WEIGHT : LABEL_WEIGHT
  const style = `${ctx.fontCss ?? ''} text{font-family:${LABEL_FONT};font-weight:${weight}}`
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ` +
    `viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">` +
    `<style>${style}</style><rect x="0" y="0" width="${width}" height="${height}" fill="${PALETTES[themeOf(ctx)].paper}"/>`
  )
}

/** White or near-black, whichever reads better on `color` (#rrggbb) */
function readableOn(color: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16))
  return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? '#111111' : '#ffffff'
}

function chip(x: number, baseline: number, size: number, tag: string, color: string): { svg: string; width: number } {
  const width = Math.max(size * 1.15, tag.length * size * 0.62 + size * 0.5)
  const height = size * 0.98
  return {
    width,
    svg:
      `<rect x="${x}" y="${baseline - size * 0.82}" width="${width}" height="${height}" rx="2" fill="${color}"/>` +
      `<text x="${x + width / 2}" y="${baseline - size * 0.08}" font-size="${size * 0.72}" fill="${readableOn(color)}" ` +
      `text-anchor="middle" font-weight="700">${esc(tag)}</text>`,
  }
}

interface Legend {
  pal: Palette
  tags: Map<string, string>
  colors: Map<string, string>
  /** the programs that have a button on this device */
  programs: Map<string, ProgramStyle>
}

function legendOf(ctx: PageContext): Legend {
  const { device } = ctx
  const pal = PALETTES[themeOf(ctx)]
  const tags = layerTags(device.layers)
  const colors = new Map<string, string>()
  device.layers.filter((l) => l !== BASE_LAYER).forEach((l, i) => colors.set(l, layerColor(i, pal.dark)))
  const programs = new Map<string, ProgramStyle>()
  for (const marks of Object.values(ctx.programs?.marks ?? {})) {
    for (const { program } of marks) programs.set(program, ctx.programs?.styles.get(program) ?? { tag: '?', color: pal.ink })
  }
  return { pal, tags, colors, programs }
}

/** Colour of an entry, and its tag when it has one: a layer's when chips are shown, a program's always */
function look(entry: Entry, legend: Legend, showChips: boolean): { color: string; tag: string | null } {
  if (entry.program) {
    const style = legend.programs.get(entry.program)
    return { color: style?.color ?? legend.pal.ink, tag: style?.tag ?? '?' }
  }
  if (entry.layer === BASE_LAYER) return { color: legend.pal.ink, tag: null }
  return { color: legend.colors.get(entry.layer) ?? legend.pal.ink, tag: showChips ? (legend.tags.get(entry.layer) ?? '?') : null }
}

function chipWidth(entry: Entry, size: number, legend: Legend, showChips: boolean): number {
  const { tag } = look(entry, legend, showChips)
  if (tag === null) return 0
  return Math.max(size * 1.15, tag.length * size * 0.62 + size * 0.5) + size * 0.25
}

interface DrawnLabel {
  svg: string
  /** grown past its box: drawn last, so that the next boxes do not hide its text */
  grown: boolean
}

/** A label box with the entries of one input, the text shrunk to fit, the box grown if needed
 * (downwards, or upwards when it would leave the drawing) */
function labelBox(
  box: Box,
  entries: Entry[],
  legend: Legend,
  measurer: Measurer,
  showChips: boolean,
  drawingHeight: number,
  sizes: TextSizes,
): DrawnLabel {
  const [x, top, width, height] = box
  const pad = 2.5
  const fit = fitTexts(
    entries,
    (e) => e.text,
    (e, size) => chipWidth(e, size, legend, showChips),
    width - 2 * pad,
    height - 2 * pad,
    measurer,
    sizes,
  )
  const boxHeight = Math.max(height, fit.height + 2 * pad)
  // at the smallest size a long word may still be wider than the box: the box widens, to the right
  const boxWidth = Math.max(width, fit.width + 2 * pad)
  const y = top + boxHeight > drawingHeight ? Math.max(0, drawingHeight - boxHeight) : top
  let out =
    `<rect x="${x}" y="${y}" width="${boxWidth}" height="${boxHeight}" rx="3" fill="${legend.pal.paper}" ` +
    `fill-opacity="0.94" stroke="${legend.pal.ink}" stroke-width="1"/>`
  let baseline = y + pad + (boxHeight - 2 * pad - fit.height) / 2 + fit.size * 0.9
  for (const block of fit.blocks) {
    const entry = block.item
    const { color, tag } = look(entry, legend, showChips)
    block.lines.forEach((line, i) => {
      let dx = 0
      if (i === 0 && tag !== null) {
        const c = chip(x + pad, baseline, fit.size, tag, color)
        out += c.svg
        dx = c.width + fit.size * 0.25
      }
      const italic = entry.released ? ' font-style="italic"' : ''
      out += `<text x="${x + pad + dx}" y="${baseline}" font-size="${fit.size}" fill="${color}"${italic}>${esc(line)}</text>`
      baseline += fit.lineHeight
    })
  }
  return { svg: out, grown: boxHeight > height || boxWidth > width }
}

/** Leader line from the box to the input on the picture (templates made by hand; the converted
 * ones have theirs in the picture) */
function leader(box: Box, anchor: [number, number], pal: Palette): string {
  const [x, y, width, height] = box
  const [ax, ay] = anchor
  const sx = Math.min(Math.max(ax, x), x + width)
  const sy = Math.min(Math.max(ay, y), y + height)
  return (
    `<line x1="${sx}" y1="${sy}" x2="${ax}" y2="${ay}" stroke="${pal.ink}" stroke-width="1.2"/>` +
    `<circle cx="${ax}" cy="${ay}" r="2.2" fill="${pal.ink}"/>`
  )
}

function emptyBox(box: Box, pal: Palette): string {
  const [x, y, width, height] = box
  return (
    `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="3" fill="${pal.paper}" fill-opacity="0.7" ` +
    `stroke="${pal.emptyStroke}" stroke-width="0.8" stroke-dasharray="3 2"/>`
  )
}

/** Lines "Button 30 · Throttle - OFF / IDLE" for the bound inputs the drawing has no box for */
function offTemplateBand(
  language: Lang,
  entries: [string, Entry[]][],
  top: number,
  width: number,
  legend: Legend,
  measurer: Measurer,
  showChips: boolean,
): { svg: string; height: number } {
  if (!entries.length) return { svg: '', height: 0 }
  const size = 11
  const lineHeight = size * 1.25
  const margin = 18
  const columnGap = 18
  const columnWidth = (width - 2 * margin - columnGap) / 2
  const nameWidth = 62
  const rows = entries.flatMap(([key, list]) =>
    list.map((entry, i) => ({ name: i === 0 ? inputName(key, language) : '', entry })),
  )
  const laidOut = rows.map((row) => ({
    ...row,
    lines: wrap(row.entry.text, size, columnWidth - nameWidth, measurer, chipWidth(row.entry, size, legend, showChips)),
  }))
  const totalLines = laidOut.reduce((n, r) => n + r.lines.length, 0)
  // fill the left column, then the right one
  let split = 0
  for (let acc = 0; split < laidOut.length && acc + laidOut[split].lines.length <= Math.ceil(totalLines / 2); split++) {
    acc += laidOut[split].lines.length
  }
  const columns = [laidOut.slice(0, split || 1), laidOut.slice(split || 1)]
  const titleHeight = 22
  let svg =
    `<line x1="${margin}" y1="${top + 6}" x2="${width - margin}" y2="${top + 6}" stroke="${legend.pal.rule}"/>` +
    `<text x="${margin}" y="${top + 20}" font-size="11" fill="${legend.pal.muted}" font-weight="700" letter-spacing="0.6">` +
    `${esc(tIn(language, 'page.off_template'))}</text>`
  let height = 0
  columns.forEach((column, c) => {
    const x = margin + c * (columnWidth + columnGap)
    let baseline = top + titleHeight + size + 4
    for (const row of column) {
      const { color, tag } = look(row.entry, legend, showChips)
      if (row.name) svg += `<text x="${x}" y="${baseline}" font-size="${size}" fill="${legend.pal.muted}">${esc(row.name)}</text>`
      row.lines.forEach((line, i) => {
        let dx = 0
        if (i === 0 && tag !== null) {
          const ch = chip(x + nameWidth, baseline, size, tag, color)
          svg += ch.svg
          dx = ch.width + size * 0.25
        }
        svg += `<text x="${x + nameWidth + dx}" y="${baseline}" font-size="${size}" fill="${color}">${esc(line)}</text>`
        baseline += lineHeight
      })
    }
    height = Math.max(height, baseline - top)
  })
  return { svg, height: height + 4 }
}

/** The line under the drawing; the template's credit goes on a line of its own when it does not fit
 * beside the rest */
function footer(ctx: PageContext, top: number, width: number, legend: Legend, part?: string): { svg: string; height: number } {
  const language = ctx.lang ?? 'en'
  const left = [ctx.profile, ctx.device.name, ctx.layer !== null ? tIn(language, 'page.layer', { layer: layerLabel(ctx.layer, language) }) : null, part]
    .filter(Boolean)
    .join(' · ')
  const layers = ctx.layer === null ? [...legend.tags].map(([layer, tag]) => `${tag} = ${layer}`) : []
  const programs = [...legend.programs].map(([program, style]) => (style.tag === program ? program : `${style.tag} = ${program}`))
  const legendText = [...layers, ...programs].join('   ')
  const credits = ctx.template ? creditLine(ctx.template.data, language) : ''
  const leftWidth = ctx.measurer.width(left, 12) + (legendText ? 14 + ctx.measurer.width(legendText, 12) : 0)
  const ownLine = credits !== '' && 16 + leftWidth + 16 + ctx.measurer.width(credits, 10) + 16 > width
  const svg =
    `<text x="16" y="${top + 18}" font-size="12" fill="${legend.pal.ink}">${esc(left)}` +
    (legendText ? `<tspan fill="${legend.pal.muted}" dx="14">${esc(legendText)}</tspan>` : '') +
    `</text>` +
    (credits
      ? `<text x="${width - 16}" y="${top + 18 + (ownLine ? CREDIT_LINE : 0)}" font-size="10" fill="${legend.pal.muted}" text-anchor="end">${esc(credits)}</text>`
      : '')
  return { svg, height: FOOTER_HEIGHT + (ownLine ? CREDIT_LINE : 0) }
}

export function creditLine(template: Template, language: Lang = 'en'): string {
  const author = template.credits?.author
  if (!author) return ''
  return tIn(language, 'page.credits', { author }) + (template.credits.license ? `, ${template.credits.license}` : '')
}

const FOOTER_HEIGHT = 28
const CREDIT_LINE = 14

/** Where a template is cut into pages: its `split_at` (vertical lines, set where the drawing has
 * room for it, e.g. between a throttle's base and its handles), kept inside the drawing */
export function cutsOf(template: Template): number[] {
  const [width] = template.size
  return [...new Set(template.split_at ?? [])].filter((x) => x > 0 && x < width).sort((a, b) => a - b)
}

export function diagramPage(ctx: PageContext): Page {
  return diagramPages(ctx, false)[0]
}

/** The device drawing; cut into pages at the template's `split_at` when `splitWide` */
export function diagramPages(context: PageContext, splitWide: boolean): Page[] {
  const ctx = styled(context)
  const sizes = sizesOf(ctx)
  const template = ctx.template!
  const [width, height] = template.data.size
  const legend = legendOf(ctx)
  const showChips = ctx.layer === null
  const language = ctx.lang ?? 'en'
  const entries = entriesByInput(ctx.device, ctx.layer, ctx.programs?.marks, language)
  let body = `<image x="0" y="0" width="${width}" height="${height}" href="${template.image}" preserveAspectRatio="xMidYMid meet"/>`
  const off: [string, Entry[]][] = []
  for (const [key, input] of Object.entries(template.data.inputs)) {
    if (!entries.has(key)) for (const box of [input.box, ...(input.more_boxes ?? [])]) body += emptyBox(box, legend.pal)
  }
  const labels: DrawnLabel[] = []
  for (const [key, list] of entries) {
    const input = template.data.inputs[key]
    if (!input) {
      off.push([key, list])
      continue
    }
    if (input.anchor) body += leader(input.box, input.anchor, legend.pal)
    for (const box of [input.box, ...(input.more_boxes ?? [])]) {
      labels.push(labelBox(box, list, legend, ctx.measurer, showChips, height, sizes))
    }
  }
  body += labels.filter((l) => !l.grown).map((l) => l.svg).join('')
  body += labels.filter((l) => l.grown).map((l) => l.svg).join('')
  const cuts = splitWide ? cutsOf(template.data) : []
  if (!cuts.length) {
    const band = offTemplateBand(language, off, height, width, legend, ctx.measurer, showChips)
    const foot = footer(ctx, height + band.height, width, legend)
    const total = height + band.height + foot.height
    const svg = svgOpen(width, total, ctx) + body + band.svg + foot.svg + '</svg>'
    return [{ title: pageTitle(ctx), width, height: total, svg, paper: legend.pal.paper }]
  }
  // one page per part, each showing its part of the same drawing; the bindings without box go on
  // the last
  const edges = [0, ...cuts, width]
  const parts = edges.slice(0, -1).map((from, i) => [from, edges[i + 1]] as [number, number])
  return parts.map(([from, to], index) => {
    const partWidth = to - from
    const last = index === parts.length - 1
    const band = last ? offTemplateBand(language, off, height, partWidth, legend, ctx.measurer, showChips) : { svg: '', height: 0 }
    const part = `${index + 1}/${parts.length}`
    const foot = footer(ctx, height + band.height, partWidth, legend, part)
    const total = height + band.height + foot.height
    const svg =
      svgOpen(partWidth, total, ctx) +
      `<svg x="0" y="0" width="${partWidth}" height="${height}" viewBox="${from} 0 ${partWidth} ${height}">${body}</svg>` +
      band.svg +
      foot.svg +
      '</svg>'
    return { title: `${pageTitle(ctx)} (${part})`, width: partWidth, height: total, svg, paper: legend.pal.paper }
  })
}

/** List pages of a device without template, as many as the rows need */
export function listPages(context: PageContext): Page[] {
  const ctx = styled(context)
  const legend = legendOf(ctx)
  const pal = legend.pal
  const showChips = ctx.layer === null
  const size = 14
  const lineHeight = size * 1.3
  const margin = 40
  const nameWidth = 96
  const textX = margin + nameWidth
  const textWidth = LIST_WIDTH - textX - margin
  const top = 104
  const bottom = LIST_HEIGHT - FOOTER_HEIGHT - 16
  const language = ctx.lang ?? 'en'
  const rows = [...entriesByInput(ctx.device, ctx.layer, ctx.programs?.marks, language)].flatMap(([key, list]) =>
    list.map((entry, i) => ({
      name: i === 0 ? inputName(key, language) : '',
      entry,
      first: i === 0,
      lines: wrap(entry.text, size, textWidth, ctx.measurer, chipWidth(entry, size, legend, showChips)),
    })),
  )
  const pages: Page[] = []
  let body = ''
  let baseline = top
  const flush = () => {
    const index = pages.length
    const heading =
      `<text x="${margin}" y="56" font-size="28" font-weight="700" fill="${pal.ink}">${esc(ctx.device.name)}</text>` +
      `<text x="${margin}" y="80" font-size="13" fill="${pal.muted}">` +
      `${esc(ctx.profile)} · ${esc(tIn(language, 'page.no_template'))}` +
      `${index ? ` ${esc(tIn(language, 'page.continued', { n: index + 1 }))}` : ''}</text>` +
      `<line x1="${margin}" y1="90" x2="${LIST_WIDTH - margin}" y2="90" stroke="${pal.ink}" stroke-width="1.5"/>`
    pages.push({
      title: index ? `${pageTitle(ctx)} ${tIn(language, 'page.continued', { n: index + 1 })}` : pageTitle(ctx),
      width: LIST_WIDTH,
      height: LIST_HEIGHT,
      paper: pal.paper,
      svg: svgOpen(LIST_WIDTH, LIST_HEIGHT, ctx) + heading + body + footer(ctx, LIST_HEIGHT - FOOTER_HEIGHT, LIST_WIDTH, legend).svg + '</svg>',
    })
    body = ''
    baseline = top
  }
  for (const row of rows) {
    const rowHeight = row.lines.length * lineHeight + (row.first ? 6 : 2)
    if (baseline + rowHeight > bottom && body) flush()
    if (row.first && baseline > top) {
      body += `<line x1="${margin}" y1="${baseline - size - 2}" x2="${LIST_WIDTH - margin}" y2="${baseline - size - 2}" stroke="${pal.softRule}"/>`
    }
    const { color, tag } = look(row.entry, legend, showChips)
    if (row.name) body += `<text x="${margin}" y="${baseline}" font-size="${size - 1}" fill="${pal.muted}">${esc(row.name)}</text>`
    row.lines.forEach((line, i) => {
      let dx = 0
      if (i === 0 && tag !== null) {
        const c = chip(textX, baseline, size, tag, color)
        body += c.svg
        dx = c.width + size * 0.25
      }
      const italic = row.entry.released ? ' font-style="italic"' : ''
      body += `<text x="${textX + dx}" y="${baseline}" font-size="${size}" fill="${color}"${italic}>${esc(line)}</text>`
      baseline += lineHeight
    })
    baseline += row.first ? 6 : 2
  }
  if (body || pages.length === 0) flush()
  return pages
}

export function devicePages(ctx: Omit<PageContext, 'layer'>, mode: 'merge' | 'split', splitWide = true): Page[] {
  return pageLayers(ctx.device, mode).flatMap((layer) => {
    const page = { ...ctx, layer }
    return page.template ? diagramPages(page, splitWide) : listPages(page)
  })
}

