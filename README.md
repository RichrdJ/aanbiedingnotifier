# aanbiedingnotifier

Scant elke week de acties van **Albert Heijn, Jumbo, Lidl, Aldi, Dirk, DekaMarkt en Plus**
(inclusief voormalige Coop-winkels) op producten die jij opgeeft, bijv. Monster of Fitmeals,
en stuurt je een pushmelding.

## Starten

```bash
cp config.example.yaml config.yaml   # zet je producten + meldingen erin
docker compose up -d --build
docker compose logs -f               # meekijken
```

Bij opstarten draait meteen een scan, daarna elke maandag om 08:00.

## Hoe het per winkel werkt

| Winkel | Methode |
|---|---|
| Albert Heijn | App-API (anoniem token), zoekt per zoekwoord op bonusproducten |
| Dirk, DekaMarkt | Acties uit de server-gerenderde aanbiedingenpagina (geen browser nodig) |
| Jumbo, Lidl, Aldi, Plus | Headless Chromium rendert de aanbiedingenpagina en leest de productkaarten |

Als een winkel zijn layout verandert en de productkaarten niet meer herkend worden,
valt de scanner terug op het doorzoeken van alle tekst op de aanbiedingenpagina, zodat
je in de meeste gevallen toch een melding krijgt. Faalt een winkel helemaal, dan gaan de
andere gewoon door; de fout staat in de logs.

**Coop:** Coop NL is opgegaan in Plus (coop.nl stuurt door naar plus.nl), daarom scant
de `plus`-bron ook "Coop". `coop: true` in de config werkt als alias.

## Meldingen

Makkelijkst: installeer de gratis **ntfy**-app en abonneer je op het topic uit `config.yaml`.
Telegram en Discord kunnen ook.

## Instellingen (docker-compose.yml)

| Variabele | Standaard | Uitleg |
|---|---|---|
| `SCHEDULE` | `0 8 * * 1` | Cron-schema (min uur dag maand weekdag) |
| `RUN_ON_START` | `true` | Direct scannen bij opstarten |
| `RUN_ONCE` | `false` | Eén keer scannen en stoppen |

## Kant-en-klare image

De GitHub Action in `.github/workflows/docker.yml` bouwt bij elke push naar `main`
een image voor amd64 en arm64 (Raspberry Pi/NAS) naar
`ghcr.io/<gebruiker>/aanbiedingnotifier:latest`.

## Output

`./data/latest.md` (overzicht), `latest.json` (ruwe data), `seen.json` (voor `only_new`).

## Let op

Geen van deze supermarkten heeft een officiële openbare API. Pagina's en app-API's kunnen
zonder aankondiging veranderen; dan moet een bron in `app/sources/` worden bijgewerkt.

## Winkel toevoegen

Maak een klasse in `app/sources/` met `fetch_all() -> list[Offer]` (alle acties) of
`search(query) -> list[Offer]` (alleen producten in de aanbieding) en registreer hem in
`SOURCES` in `app/main.py`.
