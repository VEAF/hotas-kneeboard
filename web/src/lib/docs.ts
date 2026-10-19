const SITE = 'https://veaf.github.io/hotas-kneeboard/'

/** The documentation of this version of the app (mike publishes one per release), so that the
 * .exe and its documentation always agree; the site's latest while the version is not known yet */
export function docUrl(version: string): string {
  return /^\d+\.\d+\.\d+$/.test(version) ? `${SITE}${version}/` : SITE
}
