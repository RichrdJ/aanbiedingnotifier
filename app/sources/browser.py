"""Gedeelde helpers om aanbiedingspagina's met een echte (headless) browser te openen.
Jumbo, Lidl, Aldi en Plus blokkeren hun API's voor scripts, maar hun eigen
website rendert gewoon in Chromium."""
import hashlib
import re
from contextlib import contextmanager

from . import Offer

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
COOKIE_BUTTONS = ("Akkoord", "Accepteer alles", "Alles accepteren", "Accepteren",
                  "Accepteer", "Ik ga akkoord", "Cookies accepteren")


@contextmanager
def open_page(url: str, wait_ms: int = 3000):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = browser.new_page(user_agent=UA, locale="nl-NL",
                                    viewport={"width": 1400, "height": 900})
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(wait_ms)
            accept_cookies(page)
            yield page
        finally:
            browser.close()


def accept_cookies(page):
    for label in COOKIE_BUTTONS:
        try:
            page.get_by_role("button", name=label, exact=True).first.click(timeout=1500)
            page.wait_for_timeout(1500)
            return
        except Exception:
            continue


def scroll_to_bottom(page, max_rounds: int = 30):
    last = 0
    stable = 0
    for _ in range(max_rounds):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        h = page.evaluate("document.body.scrollHeight")
        stable = stable + 1 if h == last else 0
        last = h
        if stable >= 3:
            break


def click_text(page, text: str) -> bool:
    try:
        page.get_by_text(text, exact=True).first.click(timeout=4000)
        page.wait_for_timeout(2500)
        return True
    except Exception:
        return False


def text_fallback(page, store: str, url: str) -> list[Offer]:
    """Als de productkaarten niet meer te herkennen zijn (layout gewijzigd), lever dan
    elke tekstregel van de pagina als 'aanbieding' op. De keyword-filter in main.py
    haalt er dan nog steeds de relevante regels uit."""
    try:
        body = page.inner_text("body")
    except Exception:
        return []
    out, seen = [], set()
    for line in body.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not (4 <= len(line) <= 160) or line in seen:
            continue
        seen.add(line)
        out.append(Offer(store=store, product_id=hashlib.md5(line.encode()).hexdigest()[:10],
                         title=line, deal="gevonden op aanbiedingspagina", url=url))
    print(f"[{store}] productkaarten niet gevonden, tekst-fallback gebruikt ({len(out)} regels)")
    return out


def euro(text: str):
    m = re.search(r"(\d+)[.,](\d{2})", text or "")
    return float(f"{m.group(1)}.{m.group(2)}") if m else None
