"""Jumbo: rendert jumbo.com/aanbiedingen/nu en leest de promotiekaarten."""
from . import Offer
from .browser import open_page, scroll_to_bottom, text_fallback

URL = "https://www.jumbo.com/aanbiedingen/nu"


class Jumbo:
    name = "Jumbo"
    weight = 4   # browser-scan duurt langer; telt zwaarder mee in de voortgang

    def fetch_all(self) -> list[Offer]:
        offers = []
        with open_page(URL) as page:
            scroll_to_bottom(page)
            for card in page.locator('[data-testid="promotion-card"]').all():
                try:
                    title = card.locator("h3").first.inner_text().strip()
                    tag = card.locator(".tag")
                    sub = card.locator(".subtitle")
                    link = card.locator("a")
                    href = link.first.get_attribute("href") if link.count() else ""
                    offers.append(Offer(
                        store=self.name,
                        product_id=card.get_attribute("id") or title,
                        title=title,
                        size=sub.first.inner_text().strip() if sub.count() else "",
                        deal=tag.first.inner_text().strip() if tag.count() else "Actie",
                        url=f"https://www.jumbo.com{href}" if href and href.startswith("/") else (href or URL),
                    ))
                except Exception:
                    continue
            if not offers:
                offers = text_fallback(page, self.name, URL)
        return offers
