import json
import os
import time
from datetime import datetime
from pathlib import Path

import yaml
from croniter import croniter

import notify
from sources import Offer
from sources.ah import AlbertHeijn
from sources.aldi import Aldi
from sources.detailresult import DekaMarkt, Dirk
from sources.jumbo import Jumbo
from sources.lidl import Lidl
from sources.plus import Plus

CONFIG = Path(os.getenv("CONFIG_PATH", "/config/config.yaml"))
DATA = Path(os.getenv("DATA_DIR", "/data"))
SOURCES = {"ah": AlbertHeijn, "jumbo": Jumbo, "lidl": Lidl, "aldi": Aldi,
           "dirk": Dirk, "dekamarkt": DekaMarkt, "plus": Plus}
ALIASES = {"coop": "plus", "albertheijn": "ah", "deka": "dekamarkt"}


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def matches(offer: Offer, keyword: str, exclude: list[str]) -> bool:
    text = f"{offer.brand} {offer.title}".lower()
    if any(x.lower() in text for x in exclude):
        return False
    return all(word in text for word in keyword.lower().split())


def scan(cfg: dict) -> list[Offer]:
    keywords = [str(k) for k in cfg.get("keywords", [])]
    exclude = [str(x) for x in cfg.get("exclude", []) or []]
    found: dict[str, Offer] = {}

    enabled = []
    for key, on in (cfg.get("sources") or {}).items():
        key = ALIASES.get(str(key).lower(), str(key).lower())
        if on and key in SOURCES and key not in enabled:
            enabled.append(key)

    def add(o: Offer, kw: str):
        if matches(o, kw, exclude):
            hit = found.setdefault(o.key, o)
            if kw not in hit.matched:
                hit.matched.append(kw)

    for key in enabled:
        try:
            src = SOURCES[key]()
            if hasattr(src, "fetch_all"):
                # Winkel levert alle actuele acties; wij filteren zelf op je zoekwoorden
                all_offers = src.fetch_all()
                print(f"[{key}] {len(all_offers)} acties opgehaald")
                for o in all_offers:
                    for kw in keywords:
                        add(o, kw)
            else:
                for kw in keywords:
                    try:
                        for o in src.search(kw):
                            add(o, kw)
                    except Exception as e:
                        print(f"[{key}] zoeken op '{kw}' mislukt: {e}")
                    time.sleep(1)
        except Exception as e:
            print(f"[{key}] mislukt: {e}")
    return list(found.values())


def fmt_price(v):
    return f"€{v:.2f}".replace(".", ",") if isinstance(v, (int, float)) else ""


def build_report(offers: list[Offer]) -> str:
    lines = []
    for store in sorted({o.store for o in offers}):
        lines.append(f"**{store}**")
        for o in sorted((o for o in offers if o.store == store), key=lambda o: o.title):
            price = fmt_price(o.price)
            if o.old_price and o.price and o.old_price > o.price:
                price = f"{price} (was {fmt_price(o.old_price)})"
            extra = f" · t/m {o.valid_until[:10]}" if o.valid_until else ""
            size = f" {o.size}" if o.size else ""
            lines.append(f"• {o.title}{size} - {o.deal} {price}{extra}".strip())
        lines.append("")
    return "\n".join(lines).strip()


def run_once():
    cfg = load_config()
    DATA.mkdir(parents=True, exist_ok=True)
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] scan gestart voor: {', '.join(map(str, cfg.get('keywords', [])))}")

    offers = scan(cfg)

    seen_file = DATA / "seen.json"
    seen = set(json.loads(seen_file.read_text())) if seen_file.exists() else set()
    if cfg.get("only_new"):
        offers = [o for o in offers if o.key not in seen]
    seen.update(o.key for o in offers)
    seen_file.write_text(json.dumps(sorted(seen)))

    (DATA / "latest.json").write_text(
        json.dumps([o.__dict__ for o in offers], ensure_ascii=False, indent=2), encoding="utf-8")

    if offers:
        title = f"🛒 {len(offers)} aanbieding(en) gevonden"
        body = build_report(offers)
    else:
        title = "🛒 Geen aanbiedingen deze week"
        body = "Geen van je producten is deze week in de aanbieding."
    (DATA / "latest.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    print(f"{title}\n{body}\n")
    notify.send(cfg, title, body)


def main():
    schedule = os.getenv("SCHEDULE", "0 8 * * 1")
    if os.getenv("RUN_ON_START", "true").lower() == "true":
        run_once()
    if os.getenv("RUN_ONCE", "false").lower() == "true":
        return
    it = croniter(schedule, datetime.now())
    while True:
        nxt = it.get_next(datetime)
        print(f"Volgende scan: {nxt:%A %d-%m-%Y %H:%M}")
        while datetime.now() < nxt:
            time.sleep(min(60, max(1, (nxt - datetime.now()).total_seconds())))
        try:
            run_once()
        except Exception as e:
            print(f"Scan mislukt: {e}")


if __name__ == "__main__":
    main()
