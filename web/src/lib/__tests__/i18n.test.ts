import { describe, expect, it } from 'vitest'
import { catalogs, lang, pageLanguage, resolveLang, t, tIn, tn } from '../i18n'

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('catalogs', () => {
  it('have the same keys in every language', () => {
    expect(Object.keys(catalogs.fr).sort()).toEqual(Object.keys(catalogs.en).sort())
  })

  it('have the same placeholders in every language', () => {
    const different = Object.keys(catalogs.en).filter(
      (key) => JSON.stringify(placeholders(catalogs.en[key])) !== JSON.stringify(placeholders(catalogs.fr[key] ?? '')),
    )
    expect(different).toEqual([])
  })

  it('have no empty text', () => {
    for (const catalog of Object.values(catalogs)) expect(Object.entries(catalog).filter(([, text]) => !text.trim())).toEqual([])
  })

  it('have every key the code asks for', () => {
    // literal keys only: t('a.b'), tn('a.b', …), k="a.b"; the keys built at run time (shortcuts,
    // origins) are literals in their own file too
    const used = new Set<string>()
    const sources = import.meta.glob(['../../**/*.{ts,vue}', '!../../**/__tests__/**'], { query: '?raw', import: 'default', eager: true })
    for (const source of Object.values(sources) as string[]) {
      for (const m of source.matchAll(/\b(?:t|tn|tIn\(\w+,)\s*\(?\s*'([a-z_]+(?:\.[a-z_0-9]+)+)'/g)) used.add(m[1])
      for (const m of source.matchAll(/\bk="([a-z_]+(?:\.[a-z_0-9]+)+)"/g)) used.add(m[1])
      for (const m of source.matchAll(/(?:label|hint): '([a-z_]+(?:\.[a-z_0-9]+)+)'/g)) used.add(m[1])
    }
    const plural = (key: string) => key in catalogs.en || (`${key}.one` in catalogs.en && `${key}.other` in catalogs.en)
    expect([...used].filter((key) => !plural(key))).toEqual([])
    expect(used.size).toBeGreaterThan(300)
  })
})

describe('t', () => {
  it('fills the placeholders, leaves an unknown one as it is', () => {
    expect(tIn('en', 'editor.identify.found', { input: 'Button 3', device: 'Stick' })).toBe('Button 3 on Stick')
    expect(tIn('fr', 'editor.identify.found', { input: 'Bouton 3' })).toBe('Bouton 3 sur {device}')
  })

  it('falls back to the key itself', () => {
    expect(t('no.such.key')).toBe('no.such.key')
  })

  it('follows the interface language', () => {
    lang.value = 'fr'
    expect(t('common.save')).toBe('Enregistrer')
    lang.value = 'en'
    expect(t('common.save')).toBe('Save')
  })

  it('counts with the rule of each language: zero is singular in French', () => {
    lang.value = 'fr'
    expect(tn('devices.bindings', 0)).toBe('0 liaison')
    expect(tn('devices.bindings', 2)).toBe('2 liaisons')
    lang.value = 'en'
    expect(tn('devices.bindings', 0)).toBe('0 bindings')
    expect(tn('devices.bindings', 1)).toBe('1 binding')
  })
})

describe('choice of the language', () => {
  it('takes the choice, else the browser language, else English', () => {
    expect(resolveLang('fr', 'en-US')).toBe('fr')
    expect(resolveLang('en', 'fr-FR')).toBe('en')
    expect(resolveLang(null, 'fr-CA')).toBe('fr')
    expect(resolveLang(null, 'de-DE')).toBe('en')
    expect(resolveLang('auto', 'fr')).toBe('fr')
  })

  it('draws a page in the commands language when the app speaks it, else in English', () => {
    expect(pageLanguage('fr')).toBe('fr')
    expect(pageLanguage('en')).toBe('en')
    expect(pageLanguage('de')).toBe('en')
    expect(pageLanguage(null)).toBe('en')
  })
})
