"""Kortingspercentage afleiden uit prijs/oude prijs of uit de actietekst."""
import re


def _num(s):
    return float(s.replace(",", "."))


def discount_pct(price, old_price, deal: str):
    """Geeft het kortingspercentage (0-100) of None als het niet te bepalen is."""
    d = (deal or "").lower().replace("\xa0", " ")

    m = re.search(r"(\d{1,2})\s*%", d)                       # "-20%", "25% korting"
    if m:
        return float(m.group(1))
    if re.search(r"(2e|tweede)\s*halve\s*prijs", d):
        return 25.0
    m = re.search(r"(\d+)\s*\+\s*(\d+)\s*gratis", d)          # 1+1, 2+1, 3+1 gratis
    if m:
        buy, free = int(m.group(1)), int(m.group(2))
        return round(100 * free / (buy + free), 1)
    m = re.search(r"(2e|tweede)\s*gratis", d)
    if m:
        return 50.0
    if isinstance(price, (int, float)) and isinstance(old_price, (int, float)) and old_price > 0:
        m = re.search(r"(\d+)\s*(?:voor|for)\s*€?\s*(\d+[.,]\d{2})", d)   # "2 voor 8,00"
        if m:
            unit = _num(m.group(2)) / int(m.group(1))
            if unit < old_price:
                return round(100 * (1 - unit / old_price), 1)
        if old_price > price:
            return round(100 * (1 - price / old_price), 1)
    return None
