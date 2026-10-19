/** Widths of the module and device columns, dragged by the user; null keeps the default, which
 * follows the window's width */
export interface ColumnWidths {
  modules: number | null
  devices: number | null
}

export const COLUMN_MIN = 140
export const COLUMN_MAX = 560

/** A dragged width, kept readable: the page column keeps at least a third of the window */
export function clampColumn(width: number, windowWidth: number): number {
  const max = Math.max(COLUMN_MIN, Math.min(COLUMN_MAX, windowWidth / 3))
  return Math.round(Math.min(max, Math.max(COLUMN_MIN, width)))
}
