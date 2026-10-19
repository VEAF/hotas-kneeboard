const SITE = 'https://veaf.github.io/hotas-kneeboard/'

/** The documentation of this version of the app (mike publishes one per release), so that the
 * .exe and its documentation always agree; the site's latest while the version is not known yet.
 * French is the site's default language, English is under en/ (mkdocs-static-i18n). */
export function docUrl(version: string, language: 'fr' | 'en' = 'fr'): string {
  const root = /^\d+\.\d+\.\d+$/.test(version) ? `${SITE}${version}/` : SITE
  return language === 'en' ? `${root}en/` : root
}
