import requests


def send(cfg: dict, title: str, body: str):
    n = cfg.get("notify", {}) or {}

    c = n.get("ntfy") or {}
    if c.get("enabled"):
        _try("ntfy", lambda: requests.post(
            f"{c.get('server', 'https://ntfy.sh').rstrip('/')}/{c['topic']}",
            data=body.encode("utf-8"),
            headers={"Title": title.encode("utf-8"), "Tags": "shopping_cart", "Markdown": "yes"},
            timeout=20).raise_for_status())

    c = n.get("telegram") or {}
    if c.get("enabled"):
        text = f"*{title}*\n\n{body}"
        for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)]:
            _try("telegram", lambda chunk=chunk: requests.post(
                f"https://api.telegram.org/bot{c['bot_token']}/sendMessage",
                json={"chat_id": c["chat_id"], "text": chunk, "parse_mode": "Markdown",
                      "disable_web_page_preview": True},
                timeout=20).raise_for_status())

    c = n.get("discord") or {}
    if c.get("enabled"):
        text = f"**{title}**\n{body}"
        for chunk in [text[i:i + 1900] for i in range(0, len(text), 1900)]:
            _try("discord", lambda chunk=chunk: requests.post(
                c["webhook_url"], json={"content": chunk}, timeout=20).raise_for_status())


def _try(name, fn):
    try:
        fn()
        print(f"[notify] {name}: verzonden")
    except Exception as e:
        print(f"[notify] {name}: MISLUKT - {e}")
