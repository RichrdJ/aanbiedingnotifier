"""Albert Heijn via de (onofficiële) mobiele app-API."""
import requests
from . import Offer

BASE = "https://api.ah.nl"
HEADERS = {
    "User-Agent": "Appie/8.22.3",
    "X-Application": "AHWEBSHOP",
    "Content-Type": "application/json",
}


class AlbertHeijn:
    name = "Albert Heijn"

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        r = self.s.post(f"{BASE}/mobile-auth/v1/auth/token/anonymous",
                        json={"clientId": "appie"}, timeout=20)
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def search(self, query: str) -> list[Offer]:
        r = self.s.get(f"{BASE}/mobile-services/product/search/v2",
                       params={"query": query, "sortOn": "RELEVANCE", "size": 100, "page": 0},
                       timeout=20)
        r.raise_for_status()
        offers = []
        for p in r.json().get("products", []):
            if not p.get("isBonus"):
                continue
            deal = p.get("bonusMechanism") or ""
            if not deal:
                labels = p.get("discountLabels") or []
                deal = ", ".join(l.get("defaultDescription", "") for l in labels if l)
            pid = str(p.get("webshopId", ""))
            offers.append(Offer(
                store=self.name,
                product_id=pid,
                title=p.get("title", ""),
                brand=p.get("brand", ""),
                size=p.get("salesUnitSize", ""),
                price=p.get("currentPrice"),
                old_price=p.get("priceBeforeBonus"),
                deal=deal or "Bonus",
                valid_until=p.get("bonusEndDate", ""),
                url=f"https://www.ah.nl/producten/product/wi{pid}" if pid else "",
            ))
        return offers
