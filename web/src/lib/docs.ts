const SITE = 'https://veaf.github.io/hotas-kneeboard/'

/** The documentation of this version of the app (mike publishes one per release), so that the
 * .exe and its documentation always agree; the site's latest while the version is not known yet.
 * French is the site's default language, English is under en/ (mkdocs-static-i18n) of a version:
 * the site's root only redirects to latest/, it has no en/ of its own. */
export function docUrl(version: string, language: 'fr' | 'en' = 'fr'): string {
  if (/^\d+\.\d+\.\d+$/.test(version)) return language === 'en' ? `${SITE}${version}/en/` : `${SITE}${version}/`
  return language === 'en' ? `${SITE}latest/en/` : SITE
}
