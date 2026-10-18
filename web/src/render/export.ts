// PNG (kneeboard) and PDF (print) from the page SVGs, in the browser: no Chromium nor Cairo to ship.

import { jsPDF } from 'jspdf'
import latin600 from '@fontsource/barlow-condensed/files/barlow-condensed-latin-600-normal.woff2?inline'
import latinExt600 from '@fontsource/barlow-condensed/files/barlow-condensed-latin-ext-600-normal.woff2?inline'
import latin700 from '@fontsource/barlow-condensed/files/barlow-condensed-latin-700-normal.woff2?inline'
import type { Page } from './page'

/** The label font, embedded: an SVG drawn as an image cannot use the page's fonts */
export const FONT_CSS = [
  [latin600, 600, 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2190-21FF,U+20AC,U+2212'],
  [latinExt600, 600, 'U+0100-024F,U+1E00-1EFF,U+20A0-20AB,U+20AD-20CF,U+2C60-2C7F,U+A720-A7FF'],
  [latin700, 700, 'U+0000-00FF,U+2000-206F,U+2190-21FF'],
]
  .map(
    ([url, weight, range]) =>
      `@font-face{font-family:"Barlow Condensed";font-weight:${weight};src:url(${url}) format("woff2");unicode-range:${range}}`,
  )
  .join('')

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('page impossible à dessiner'))
    image.src = url
  })
}

/** The page drawn at `height` pixels (the width follows), as a canvas */
export async function pageCanvas(page: Page, height: number): Promise<HTMLCanvasElement> {
  const url = URL.createObjectURL(new Blob([page.svg], { type: 'image/svg+xml' }))
  try {
    const image = await loadImage(url)
    // fonts inside an SVG image load asynchronously: give them a frame before drawing
    await new Promise((r) => setTimeout(r, 30))
    const canvas = document.createElement('canvas')
    canvas.height = Math.round(height)
    canvas.width = Math.round((page.width * height) / page.height)
    const context = canvas.getContext('2d')!
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return canvas
  } finally {
    URL.revokeObjectURL(url)
  }
}

export async function pagePngBase64(page: Page, height: number): Promise<string> {
  const canvas = await pageCanvas(page, height)
  return canvas.toDataURL('image/png').split(',')[1]
}

const A4 = { width: 210, height: 297 }
const PDF_MARGIN = 8
const PDF_PIXEL_HEIGHT = 2200 // about 200 dpi on A4

/** One A4 page per page, the picture as large as it fits */
export async function pagesPdf(pages: Page[], fileName: string): Promise<void> {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait', compress: true })
  for (const [index, page] of pages.entries()) {
    if (index > 0) doc.addPage('a4', 'portrait')
    const canvas = await pageCanvas(page, PDF_PIXEL_HEIGHT)
    const maxWidth = A4.width - 2 * PDF_MARGIN
    const maxHeight = A4.height - 2 * PDF_MARGIN
    const scale = Math.min(maxWidth / page.width, maxHeight / page.height)
    const [w, h] = [page.width * scale, page.height * scale]
    doc.addImage(canvas, 'JPEG', (A4.width - w) / 2, (A4.height - h) / 2, w, h, undefined, 'FAST')
  }
  doc.save(fileName)
}
