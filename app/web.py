"""Kleine webserver (alleen standaardbibliotheek) voor de GUI op poort 4040."""
import base64
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from croniter import croniter

import main
import notify

STATIC = Path(__file__).with_name("static")
PASSWORD = os.getenv("GUI_PASSWORD", "")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    # ---- helpers ----
    def _authorized(self):
        if not PASSWORD:
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                return base64.b64decode(h[6:]).decode().split(":", 1)[1] == PASSWORD
            except Exception:
                return False
        return False

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _guard(self):
        if self._authorized():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="aanbiedingnotifier"')
        self.end_headers()
        return False

    # ---- routes ----
    def do_GET(self):
        if not self._guard():
            return
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if p == "/api/status":
            cfg = main.load_config()
            return self._send(200, {**main.STATE, "schedule": main.get_schedule(cfg),
                                    "stores": main.STORE_NAMES})
        if p == "/api/offers":
            f = main.DATA / "latest.json"
            return self._send(200, json.loads(f.read_text(encoding="utf-8")) if f.exists() else [])
        if p == "/api/config":
            cfg = main.load_config()
            cfg.setdefault("schedule", main.get_schedule(cfg))
            return self._send(200, cfg)
        if p == "/api/log":
            return self._send(200, list(main.LOG)[-300:])
        self._send(404, {"error": "niet gevonden"})

    def do_POST(self):
        if not self._guard():
            return
        p = self.path.split("?")[0]
        try:
            body = self._body()
        except Exception:
            return self._send(400, {"error": "ongeldige JSON"})
        if p == "/api/scan":
            ok = main.start_scan_async(notify_enabled=bool(body.get("notify", True)))
            return self._send(202 if ok else 409, {"started": ok})
        if p == "/api/config":
            sched = str(body.get("schedule") or "")
            if sched and not croniter.is_valid(sched):
                return self._send(400, {"error": f"Schema '{sched}' is geen geldige cron-regel"})
            body["keywords"] = main.keyword_list(body)
            body["exclude"] = [str(k).strip() for k in body.get("exclude", []) if str(k).strip()]
            for old in ("min_discount", "include_unknown_discount"):
                body.pop(old, None)
            main.save_config(body)
            print("Instellingen opgeslagen via GUI")
            return self._send(200, {"saved": True})
        if p == "/api/test-notify":
            notify.send(main.load_config(), "🛒 Testmelding", "Meldingen van aanbiedingnotifier werken.")
            return self._send(200, {"sent": True})
        self._send(404, {"error": "niet gevonden"})


def start(port: int):
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"GUI draait op http://0.0.0.0:{port}" + (" (met wachtwoord)" if PASSWORD else ""))
