# Changelog

## v1.2.0 — 2026-09-28

- Kortingsfilter verwijderd (minimum per product, standaardminimum en filter in de resultaten). Bestaande configs met `monster 30%` of `min_discount` worden automatisch omgezet naar alleen het zoekwoord

## v1.1.0 — 2026-09-28

- Voortgangsbalk met percentage en huidige winkel tijdens een scan, ook op de scanknop
- Een product dat je al volgt nogmaals toevoegen werkt nu alleen het minimum bij in plaats van een dubbele regel te maken

## v1.0.0 — 2026-09-28

Eerste release.

- Scant AH, Jumbo, Lidl, Aldi, Dirk, DekaMarkt en Plus (incl. voormalige Coop) op je producten
- GUI op poort 4040: producten volgen, resultaten per product, winkels aan/uit, schema, logboek
- Minimale korting per product of als standaard, met automatische berekening van het kortingspercentage
- Filter op kortingspercentage in de resultaten
- Meldingen via ntfy, Telegram, Discord en Pushover, met testknop
- Kant-en-klare `stack.yml` en multi-arch image (amd64/arm64) op GHCR
