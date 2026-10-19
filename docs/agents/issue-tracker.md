# Suivi : les tickets GitHub

Les lots, leurs PRD et leurs tickets sont des tickets GitHub du dépôt `VEAF/hotas-kneeboard`.
C'est l'organisation de VEAF-Mission-Creation-Tools (`.backlog/<LOT-ID>/PRD.md` et `tickets/NN-slug.md`), transposée dans GitHub.

## Conventions

| VMCT (`.backlog/`) | Ici (GitHub) |
|---|---|
| un dossier `.backlog/<LOT-ID>/` | un ticket étiqueté `lot`, titré `<LOT-ID> — <titre>` |
| `PRD.md` (gabarit de PRD de Matt) | le corps du ticket du lot ; ses conditions de fin en cases à cocher (`## Done when`) |
| `tickets/<NN>-<slug>.md` | un sous-ticket du lot, étiqueté `ticket`, titré `<LOT-ID> NN — <titre>`, numéroté à partir de `01` dans l'ordre des dépendances |
| la ligne `Status:` | une étiquette de statut (voir [triage-labels.md](triage-labels.md)) |
| les index `README.md`, `ACTIVE.md`, `READY.md`, `DONE.md` | les recherches ci-dessous, et le PRD [#1](https://github.com/VEAF/hotas-kneeboard/issues/1), dont les lots sont les sous-tickets (barre d'avancement) |
| `archive/` | les tickets fermés |

- Les identifiants de lot suivent VMCT : `FEAT-…`, `FIX-…`, `CHORE-…`, `DOC-…`, `INVESTIGATE-…`, en majuscules, tirets.
- Un ticket qui en bloque un autre est indiqué par la relation « blocked by » de GitHub, et rappelé dans le corps (`Blocked by #N`).
- Un lot = une branche (`feature/`, `fix/` ou `chore/<LOT-ID>`) et une seule PR vers `develop`, qui porte `Closes #<ticket>` pour chacun de ses tickets et `Closes #<lot>`.
  `develop` est la branche par défaut du dépôt : ces mots-clés ferment les tickets à la fusion.

## Où regarder

- Le PRD et l'avancement des lots : [#1](https://github.com/VEAF/hotas-kneeboard/issues/1).
- [Lots en cours ou en attente](https://github.com/VEAF/hotas-kneeboard/issues?q=is%3Aopen+label%3Alot) (`is:open label:lot`).
- [Lots prêts à être pris](https://github.com/VEAF/hotas-kneeboard/issues?q=is%3Aopen+label%3Alot+label%3A%22%E2%AC%9C+ready%22) (`is:open label:lot label:"⬜ ready"`).
- [Ce qui attend David](https://github.com/VEAF/hotas-kneeboard/issues?q=is%3Aopen+label%3A%22%F0%9F%A7%91+waiting-human%22) (`is:open label:"🧑 waiting-human"`).
- [Lots terminés](https://github.com/VEAF/hotas-kneeboard/issues?q=is%3Aclosed+label%3Alot+reason%3Acompleted) (`is:closed label:lot reason:completed`).

## Quand un skill dit « publier dans le tracker »

- Un PRD → un ticket étiqueté `lot` et `⬜ ready`, titré `<LOT-ID> — …`, rattaché comme sous-ticket au PRD #1 (`gh api -X POST repos/VEAF/hotas-kneeboard/issues/1/sub_issues -F sub_issue_id=<id du ticket>`).
- Un ticket → un ticket étiqueté `ticket` et `⬜ ready`, titré `<LOT-ID> NN — …`, rattaché comme sous-ticket à son lot, avec ses relations « blocked by ».
- Tout ce qui est créé l'est à `⬜ ready`.

## Quand un skill dit « lire le ticket »

`gh issue view <numéro> --repo VEAF/hotas-kneeboard --comments`, et pour un lot ses sous-tickets : `gh api repos/VEAF/hotas-kneeboard/issues/<numéro>/sub_issues`.
David donne d'habitude le numéro du lot ou du ticket.

## Les signalements extérieurs

Un ticket ouvert par quelqu'un d'autre (un bug, une suggestion) n'est pas un lot.
Quand on le prend en charge, on crée le lot qui le traite et on ferme le signalement en pointant vers lui ; un signalement qui reste ouvert veut dire « noté, personne ne l'a pris ».
