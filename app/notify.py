import requests


def send(cfg: dict, title: str, body: str, icon: str = ""):
    n = cfg.get("notify", {}) or {}

    c = n.get("ntfy") or {}
    if c.get("enabled"):
        headers = {"Title": title.encode("utf-8"), "Tags": "shopping_cart", "Markdown": "yes"}
        if icon:
            headers["Icon"] = icon
        _try("ntfy", lambda: requests.post(
            f"{c.get('server', 'https://ntfy.sh').rstrip('/')}/{c['topic']}",
            data=body.encode("utf-8"),
            headers=headers,
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


    c = n.get("pushover") or {}
    if c.get("enabled"):
        # Pushover: max 1024 tekens per bericht, dus zo nodig opsplitsen op regelgrenzen
        chunks, cur = [], ""
        for line in body.replace("**", "").splitlines():
            if len(cur) + len(line) + 1 > 1000:
                chunks.append(cur)
                cur = ""
            cur += line + "\n"
        chunks.append(cur)
        for i, chunk in enumerate(chunks):
            t = title if len(chunks) == 1 else f"{title} ({i + 1}/{len(chunks)})"
            data = {"token": c.get("app_token", ""), "user": c.get("user_key", ""),
                    "title": t, "message": chunk.strip() or "-"}
            if c.get("device"):
                data["device"] = c["device"]
            if c.get("priority") not in (None, ""):
                data["priority"] = int(c["priority"])
            _try("pushover", lambda data=data: requests.post(
                "https://api.pushover.net/1/messages.json", data=data, timeout=20).raise_for_status())


def _try(name, fn):
    try:
        fn()
        print(f"[notify] {name}: verzonden")
    except Exception as e:
        print(f"[notify] {name}: MISLUKT - {e}")
