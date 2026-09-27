import collections
import json
import os
import shutil
import sys
import threading
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


EXAMPLE = Path(__file__).with_name("config.example.yaml")
STORE_NAMES = {"ah": "Albert Heijn", "jumbo": "Jumbo", "lidl": "Lidl", "aldi": "Aldi",
               "dirk": "Dirk", "dekamarkt": "DekaMarkt", "plus": "Plus / Coop"}

# ---------- logboek (voor de GUI) ----------
LOG = collections.deque(maxlen=500)


class _Tee:
    def __init__(self, stream):
        self.stream, self.buf = stream, ""

    def write(self, s):
        self.stream.write(s)
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if line.strip():
                LOG.append(f"{datetime.now():%d-%m %H:%M:%S}  {line}")

    def flush(self):
        self.stream.flush()


sys.stdout = _Tee(sys.stdout)

# ---------- status ----------
STATE = {"running": False, "last_scan": None, "last_count": None, "last_error": None,
         "next_scan": None, "per_store": {}}
_scan_lock = threading.Lock()
_status_file = DATA / "status.json"


def _load_state():
    try:
        STATE.update(json.loads(_status_file.read_text()))
        STATE["running"] = False
    except Exception:
        pass


def _save_state():
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        _status_file.write_text(json.dumps({k: v for k, v in STATE.items() if k != "running"}))
    except Exception:
        pass


def load_config() -> dict:
    if not CONFIG.exists():
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(EXAMPLE, CONFIG)
        print(f"Nieuwe config aangemaakt op {CONFIG}")
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(cfg: dict):
    text = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    with open(CONFIG, "w", encoding="utf-8") as f:   # overschrijven i.p.v. rename: werkt ook op bind-mounts
        f.write(text)


def get_schedule(cfg: dict | None = None) -> str:
    cfg = cfg if cfg is not None else load_config()
    sched = str(cfg.get("schedule") or os.getenv("SCHEDULE", "0 8 * * 1"))
    return sched if croniter.is_valid(sched) else "0 8 * * 1"


def matches(offer: Offer, keyword: str, exclude: list[str]) -> bool:
    text = f"{offer.brand} {offer.title}".lower()
    if any(x.lower() in text for x in exclude):
        return False
    return all(word in text for word in keyword.lower().split())


def scan(cfg: dict) -> list[Offer]:
    keywords = [str(k) for k in cfg.get("keywords", [])]
    exclude = [str(x) for x in cfg.get("exclude", []) or []]
    found: dict[str, Offer] = {}

    STATE["per_store"] = {}
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
                STATE["per_store"][key] = {"ok": True, "offers": len(all_offers)}
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
                STATE["per_store"][key] = {"ok": True, "offers": None}
        except Exception as e:
            STATE["per_store"][key] = {"ok": False, "error": str(e)[:200]}
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


def run_once(notify_enabled: bool = True):
    if not _scan_lock.acquire(blocking=False):
        print("Er loopt al een scan, overgeslagen")
        return False
    STATE.update(running=True, last_error=None)
    try:
        cfg = load_config()
        DATA.mkdir(parents=True, exist_ok=True)
        print(f"Scan gestart voor: {', '.join(map(str, cfg.get('keywords', [])))}")
        offers = scan(cfg)

        seen_file = DATA / "seen.json"
        seen = set(json.loads(seen_file.read_text())) if seen_file.exists() else set()
        for o in offers:
            o.__dict__["new"] = o.key not in seen
        (DATA / "latest.json").write_text(
            json.dumps([o.__dict__ for o in offers], ensure_ascii=False, indent=2), encoding="utf-8")

        to_send = [o for o in offers if o.__dict__["new"]] if cfg.get("only_new") else offers
        seen.update(o.key for o in offers)
        seen_file.write_text(json.dumps(sorted(seen)))

        if to_send:
            title = f"🛒 {len(to_send)} aanbieding(en) gevonden"
            body = build_report(to_send)
        else:
            title = "🛒 Geen aanbiedingen deze week"
            body = "Geen van je producten is deze week in de aanbieding."
        (DATA / "latest.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        print(f"{title}\n{body}")
        if notify_enabled:
            notify.send(cfg, title, body)
        STATE.update(last_scan=datetime.now().isoformat(timespec="seconds"), last_count=len(offers))
        return True
    except Exception as e:
        STATE["last_error"] = str(e)
        print(f"Scan mislukt: {e}")
        return False
    finally:
        STATE["running"] = False
        _save_state()
        _scan_lock.release()


def start_scan_async(notify_enabled: bool = True) -> bool:
    if STATE["running"]:
        return False
    threading.Thread(target=run_once, args=(notify_enabled,), daemon=True).start()
    return True


def scheduler_loop():
    while True:
        sched = get_schedule()
        nxt = croniter(sched, datetime.now()).get_next(datetime)
        STATE["next_scan"] = nxt.isoformat(timespec="minutes")
        dag = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"][nxt.weekday()]
        print(f"Volgende scan: {dag} {nxt:%d-%m-%Y %H:%M} ({sched})")
        while datetime.now() < nxt:
            time.sleep(20)
            if get_schedule() != sched:      # schema aangepast via de GUI
                break
        else:
            run_once()


def main():
    sys.modules["main"] = sys.modules[__name__]   # zodat web.py dezelfde STATE deelt
    _load_state()
    load_config()
    if os.getenv("RUN_ONCE", "false").lower() == "true":
        run_once()
        return
    import web
    web.start(int(os.getenv("GUI_PORT", "4040")))
    if os.getenv("RUN_ON_START", "false").lower() == "true":
        start_scan_async()
    scheduler_loop()


if __name__ == "__main__":
    main()
