# HOTAS Kneeboard — 0.3.1

**Des pages lisibles dans DCS, et une cause de « aucun périphérique » en moins.**
Les pages en largeur ne sortent plus écrasées dans le kneeboard, et un mod d'avion bavard ne fait plus disparaître tous tes périphériques.

---

## 📋 Le kneeboard

- **Plus rien n'est déformé** : DCS étirait chaque page pour remplir son cadre, plus étroit que haut.
  Les pages en largeur (ICP, MFD WinWing…) sortaient comprimées de moitié et illisibles.
  Elles sont maintenant écrites aux proportions du cadre, le dessin centré dans des marges blanches : une page en largeur tient toute la largeur, centrée en hauteur.
- **Le pied de page ne se chevauche plus** : le crédit du gabarit passe sur sa propre ligne quand il recouvrirait le nom du module, du périphérique ou la légende SRS et VectorXR (sur une moitié de throttle par exemple).

---

## 🕹️ « Bindings could not be read »

Avec cette erreur, aucun périphérique ne s'affichait.
Une cause connue est corrigée : certains mods d'avions affichent un message en se chargeant, et ce message suffisait à faire échouer toute la lecture des commandes.
Il va maintenant dans le journal de l'application.

Si tu as encore l'erreur, elle montre désormais ce que DCS a renvoyé : envoie-nous-la, elle dit d'où vient le problème.

Merci à **GunHed**, qui l'a signalée.

---

## ⚠️ Ce que tu as à faire

Réexporte tes pages kneeboard : celles déjà dans DCS gardent l'ancien format, étiré.
Les nouvelles ont des marges blanches, c'est normal : c'est ce qui les garde aux bonnes proportions.

Un souci ? Signale-le sur <https://github.com/VEAF/hotas-kneeboard/issues> ou sur le Discord VEAF, avec le fichier `%APPDATA%\HOTAS Kneeboard\hotas-kneeboard.log` : il dit ce qui s'est passé.

---

## 🇬🇧 In English

**Readable pages in DCS, and one cause of "no devices" less.**
Landscape pages no longer come out squashed in the kneeboard, and a chatty aircraft mod no longer makes all your devices disappear.

**Documentation**: https://veaf.github.io/hotas-kneeboard/0.3.1/en/

### 📋 The kneeboard

- **Nothing is distorted anymore**: DCS stretched every page to fill its frame, which is narrower than it is tall.
  Landscape pages (WinWing ICP, MFDs…) came out squeezed to half their width and unreadable.
  They are now written in the frame's proportions, the drawing centred in white margins: a landscape page spans the full width, centred vertically.
- **The footer no longer overlaps**: the template credit moves to its own line when it would cover the module or device name, or the SRS and VectorXR legend (on a throttle half, for instance).

### 🕹️ "Bindings could not be read"

With this error, no device showed up.
A known cause is fixed: some aircraft mods print a message while loading, and that message was enough to make reading the controls fail entirely.
It now goes to the app's log.

If you still get the error, it now shows what DCS sent back: send it to us, it tells where the problem comes from.

Thanks to **GunHed** for reporting it.

### ⚠️ What you have to do

Export your kneeboard pages again: the ones already in DCS keep the old, stretched format.
The new ones have white margins, that's expected: they are what keeps the proportions right.

Something wrong? Report it on <https://github.com/VEAF/hotas-kneeboard/issues> or on the VEAF Discord, with the file `%APPDATA%\HOTAS Kneeboard\hotas-kneeboard.log`: it says what happened.
