"""Plus (en daarmee ook de voormalige Coop-winkels): rendert plus.nl/aanbiedingen,
beide tabbladen (t/m dinsdag en vanaf woensdag)."""
import re

from . import Offer
from .browser import click_text, open_page, text_fallback

URL = "https://www.plus.nl/aanbiedingen"


def _wait_stable(page, locator, rounds=20):
    prev, stable = -1, 0
    for _ in range(rounds):
        page.wait_for_timeout(500)
        n = locator.count()
        stable = stable + 1 if n == prev else 0
        prev = n
        if stable >= 3 and n > 0:
            return


class Plus:
    name = "Plus"

    def _read(self, page, seen) -> list[Offer]:
        out = []
        period = re.search(r"\w+dag \d{1,2} \w+ t/m \w+dag \d{1,2} \w+", page.inner_text("body"))
        for card in page.locator(".plp-item-wrapper").all():
            try:
                m = re.search(r"item__(\d+)", card.get_attribute("class") or "")
                pid = m.group(1) if m else None
                if pid and pid in seen:
                    continue
                name = card.locator(".plp-item-name span")
                title = name.first.inner_text().strip() if name.count() else ""
                if not title:
                    continue
                pi = card.locator(".product-header-price-integer")
                pd = card.locator(".product-header-price-decimals")
                price = None
                if pi.count():
                    i = re.sub(r"\D", "", pi.first.inner_text())
                    d = re.sub(r"\D", "", pd.first.inner_text()) if pd.count() else "00"
                    price = float(f"{i}.{d or '00'}") if i else None
                label = card.locator(".promo-offer-label span")
                desc = card.locator(".plp-item-complementary span")
                out.append(Offer(
                    store=self.name, product_id=pid or title, title=title,
                    size=desc.first.inner_text().strip() if desc.count() else "",
                    price=price, deal=label.first.inner_text().strip() if label.count() else "Actie",
                    valid_until=period.group(0) if period else "", url=URL,
                ))
                if pid:
                    seen.add(pid)
            except Exception:
                continue
        return out

    def fetch_all(self) -> list[Offer]:
        offers, seen = [], set()
        with open_page(URL) as page:
            cards = page.locator(".plp-item-wrapper")
            _wait_stable(page, cards)
            offers += self._read(page, seen)
            if click_text(page, "Vanaf woensdag"):
                _wait_stable(page, cards)
                offers += self._read(page, seen)
            if not offers:
                offers = text_fallback(page, self.name, URL)
        return offers
