// Interface language, the way VEAF-Mission-Creation-Tools does it (veaf_libs/i18n.py): one flat
// JSON catalog per language, dotted keys, `{name}` placeholders; English is the reference and
// the fallback of a key missing from another catalog, the key itself the last resort.

import { ref } from 'vue'
import en from '../locales/en.json'
import fr from '../locales/fr.json'

export const LANGUAGES = ['fr', 'en'] as const
export type Lang = (typeof LANGUAGES)[number]

type Catalog = Record<string, string>
const CATALOGS: Record<Lang, Catalog> = { fr, en }
// the choice is kept by the server (settings.json); this copy only spares a flash of the other
// language before the settings are read
const STORAGE_KEY = 'hotas-kneeboard-language'

/** The language of a choice: "fr" or "en" as chosen, else (null, "auto") the browser's */
export function resolveLang(choice: string | null | undefined, browser: string = navigator.language): Lang {
  if (choice === 'fr' || choice === 'en') return choice
  return browser.toLowerCase().startsWith('fr') ? 'fr' : 'en'
}

function stored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

/** The language the interface speaks now; reactive: what reads it is redrawn when it changes */
export const lang = ref<Lang>(resolveLang(stored()))

/** Applies the user's choice (null: the browser's language) */
export function setLanguage(choice: string | null | undefined): void {
  lang.value = resolveLang(choice)
  document.documentElement.lang = lang.value
  try {
    localStorage.setItem(STORAGE_KEY, lang.value)
  } catch {
    // private window, storage blocked: the server's copy is enough
  }
}

function format(text: string, params?: Record<string, unknown>): string {
  if (!params) return text
  return text.replace(/\{(\w+)\}/g, (whole, name: string) => (name in params ? String(params[name]) : whole))
}

/** The text of a key in a given language (a kneeboard page follows the commands' language) */
export function tIn(language: Lang, key: string, params?: Record<string, unknown>): string {
  return format(CATALOGS[language][key] ?? CATALOGS.en[key] ?? key, params)
}

/** The text of a key in the interface's language */
export function t(key: string, params?: Record<string, unknown>): string {
  return tIn(lang.value, key, params)
}

/** A count: `<key>.one` for one (and zero in French), `<key>.other` otherwise; `{n}` is the count */
export function tn(key: string, n: number, params?: Record<string, unknown>): string {
  return t(pluralKey(key, n), { ...params, n })
}

/** `<key>.one` or `<key>.other`, by the interface language's rule */
export function pluralKey(key: string, n: number): string {
  const one = lang.value === 'fr' ? n <= 1 : n === 1
  return `${key}.${one ? 'one' : 'other'}`
}

/** The language of a kneeboard page's own words: the commands' when the app speaks it, else
 * English, so that a page never mixes two languages */
export function pageLanguage(commandsLanguage: string | null | undefined): Lang {
  return commandsLanguage === 'fr' ? 'fr' : 'en'
}

/** The catalogs, for the test that checks they agree */
export const catalogs = CATALOGS
