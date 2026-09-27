"""Lidl: rendert de aanbiedingenpagina (3 tabbladen: maandag/woensdag/vrijdag) en leest
de JSON in het data-gridbox-impression-attribuut van elke tegel."""
import json
import re
from urllib.parse import unquote

from . import Offer
from .browser import click_text, open_page, text_fallback

BASE = "https://www.lidl.nl"
URL = f"{BASE}/c/aanbiedingen/a10008785"
TABS = ["Maandag", "Woensdag", "Vrijdag"]


class Lidl:
    name = "Lidl"
    weight = 4   # browser-scan duurt langer; telt zwaarder mee in de voortgang

    def fetch_all(self) -> list[Offer]:
        offers, seen = [], set()
        with open_page(URL) as page:
            for tab in TABS:
                click_text(page, tab)
                for tile in page.locator("[data-gridbox-impression]").all():
                    try:
                        info = json.loads(unquote(tile.get_attribute("data-gridbox-impression") or "{}"))
                        pid, name = str(info.get("id") or ""), info.get("name")
                        if not name or (pid and pid in seen):
                            continue
                        seen.add(pid)
                        text = tile.inner_text()
                        valid = re.search(r"vanaf \d{2}/\d{2}(\s*-\s*\d{2}/\d{2})?", text)
                        disc = re.search(r"-\d+%|\d+\+\d+ gratis|\d+e halve prijs", text, re.I)
                        link = tile.locator("a")
                        href = link.first.get_attribute("href") if link.count() else ""
                        offers.append(Offer(
                            store=self.name, product_id=pid or name, title=name,
                            brand=info.get("brand", "") or "",
                            price=float(info["price"]) if info.get("price") is not None else None,
                            deal=disc.group(0) if disc else f"Actie ({tab.lower()})",
                            valid_until=valid.group(0) if valid else "",
                            url=f"{BASE}{href}" if href and href.startswith("/") else URL,
                        ))
                    except Exception:
                        continue
            if not offers:
                offers = text_fallback(page, self.name, URL)
        return offers
