"""Dirk en DekaMarkt (beide van Detailresult). De aanbiedingenpagina is server-side
gerenderd met Nuxt; alle actuele acties staan in de __NUXT_DATA__-payload, dus er is
geen browser of API-sleutel nodig. Lukt dat niet, dan valt hij terug op de browser."""
import json
import re

import requests

from . import Offer
from .browser import UA, open_page, text_fallback

_PAYLOAD_RE = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)
_REACTIVE = {"ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef"}
_CONTAINERS = {"Set", "Map", "Date"}


class _Nuxt:
    """Minimale decoder voor Nuxt's devalue-formaat."""

    def __init__(self, arr):
        self.a, self.cache = arr, {}

    def unwrap(self, i):
        v = self.a[i]
        if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] in _REACTIVE:
            return self.unwrap(v[1])
        return v

    def resolve(self, i):
        if not isinstance(i, int) or i < 0 or i >= len(self.a):
            return i
        if i in self.cache:
            return self.cache[i]
        self.cache[i] = None
        v = self.a[i]
        if isinstance(v, dict):
            out = {k: self.resolve(x) for k, x in v.items()}
        elif isinstance(v, list):
            if len(v) == 2 and isinstance(v[0], str) and v[0] in (_REACTIVE | _CONTAINERS):
                tag, idx = v
                if tag == "Set":
                    inner = self.a[idx]
                    out = [self.resolve(x) for x in inner] if isinstance(inner, list) else []
                elif tag == "Map":
                    out = {str(self.resolve(k)): self.resolve(x) for k, x in self.a[idx]}
                else:
                    out = self.resolve(idx)
            else:
                out = [self.resolve(x) for x in v]
        else:
            out = v
        self.cache[i] = out
        return out


def _find_offers(node, found):
    """Zoek recursief naar dicts die op een aanbieding lijken (headerText + offerPrice)."""
    if isinstance(node, dict):
        if "headerText" in node and "offerPrice" in node:
            found.append(node)
            return
        for v in node.values():
            _find_offers(v, found)
    elif isinstance(node, list):
        for v in node:
            _find_offers(v, found)


class _DetailResult:
    name = ""
    base = ""

    def fetch_all(self) -> list[Offer]:
        url = f"{self.base}/aanbiedingen"
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            m = _PAYLOAD_RE.search(r.text)
            if not m:
                raise ValueError("geen __NUXT_DATA__ op de pagina")
            nuxt = _Nuxt(json.loads(m.group(1)))
            root = nuxt.unwrap(0)
            data = nuxt.resolve(root["data"]) if isinstance(root, dict) and "data" in root else {}
            raw = []
            _find_offers(data, raw)
            offers = [self._to_offer(o, url) for o in raw]
            offers = [o for o in offers if o]
            if offers:
                return offers
            raise ValueError("payload gevonden maar geen acties")
        except Exception as e:
            print(f"[{self.name}] payload uitlezen mislukt ({e}), probeer browser")
        with open_page(url) as page:
            return text_fallback(page, self.name, url)

    def _to_offer(self, o: dict, url: str):
        title = (o.get("headerText") or "").strip()
        if not title:
            return None
        price = o.get("offerPrice")
        normal = o.get("normalPrice") or 0
        if not normal and o.get("products"):
            normal = (o["products"][0] or {}).get("normalPrice") or 0
        deal = next((str(o[k]) for k in ("priceLabel", "offerLabel", "textPriceSign", "subText")
                     if o.get(k)), "")
        if not deal and normal and price and normal > price:
            deal = f"van €{normal:.2f} voor €{price:.2f}".replace(".", ",")
        return Offer(
            store=self.name, product_id=str(o.get("offerId") or title), title=title,
            size=str(o.get("packaging") or ""),
            price=float(price) if isinstance(price, (int, float)) else None,
            old_price=float(normal) if normal else None,
            deal=deal or "Actie", valid_until=str(o.get("endDate") or "")[:10], url=url,
        )


class Dirk(_DetailResult):
    name = "Dirk"
    base = "https://www.dirk.nl"


class DekaMarkt(_DetailResult):
    name = "DekaMarkt"
    base = "https://www.dekamarkt.nl"
