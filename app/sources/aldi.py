"""Aldi: rendert aldi.nl/aanbiedingen.html en leest de producttegels."""
import re

from . import Offer
from .browser import euro, open_page, scroll_to_bottom, text_fallback

URL = "https://www.aldi.nl/aanbiedingen.html"


class Aldi:
    name = "Aldi"
    weight = 4   # browser-scan duurt langer; telt zwaarder mee in de voortgang

    def fetch_all(self) -> list[Offer]:
        offers = []
        with open_page(URL) as page:
            scroll_to_bottom(page, 15)
            for tile in page.locator(".product-tile").all():
                try:
                    n = tile.locator(".product-tile__content__upper__product-name")
                    title = n.first.inner_text().strip().replace("\xad", "") if n.count() else ""
                    if not title:
                        continue
                    b = tile.locator(".product-tile__content__upper__brand-name")
                    brand = b.first.inner_text().strip() if b.count() else ""
                    text = tile.inner_text()
                    disc = re.search(r"-\d+%|OP=OP|\d+\+\d+ gratis", text)
                    link = tile.locator("a")
                    href = link.first.get_attribute("href") if link.count() else ""
                    offers.append(Offer(
                        store=self.name, product_id=href or f"{brand}{title}", title=title, brand=brand,
                        price=euro(text), deal=disc.group(0) if disc else "Actie",
                        url=f"https://www.aldi.nl{href}" if href and href.startswith("/") else URL,
                    ))
                except Exception:
                    continue
            if not offers:
                offers = text_fallback(page, self.name, URL)
        return offers
