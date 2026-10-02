"""Advance over HTTP: one page, one question endpoint. Standard library only, so it deploys anywhere.

    PYTHONPATH=src python3 -m advance.web                 # http://127.0.0.1:8790

POST /api/ask {"text": "Phoebe Bridgers in Chicago and Denver"} returns the plan the agent made,
the brief built from Qloo, the advice, and which of model/patterns/template answered each step.
"""
import http.server
import json
import os
import pathlib
import sys
import time

from . import brief as briefing
from . import plan as planning
from .qloo import Empty, Qloo, QlooError

PAGE = pathlib.Path(__file__).with_name("page.html")


def ask(text, q=None):
    started = time.perf_counter()
    q = q or Qloo.from_env()
    steps, meta = planning.plan(text)
    try:
        built = briefing.build(q, steps["headliner"], cities=steps["cities"], share=steps["opener_share"],
                               market=steps.get("market") or None)
    except Empty:
        return {"error": f"Qloo does not know an artist called {steps['headliner']!r}.", "plan": steps, "plan_meta": meta}
    brief = built.to_dict()
    advice, advice_meta = planning.advise(brief)
    return {"plan": steps, "plan_meta": meta, "brief": brief, "advice": advice, "advice_meta": advice_meta,
            "qloo_calls": q.calls, "ms": round((time.perf_counter() - started) * 1000)}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "advance/0.1"

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/healthz":
            spec = planning.endpoint()
            self._send(200, {"ok": True, "model": spec and spec["model"]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/api/ask":
            self._send(404, {"error": "not found"})
            return
        try:
            length = min(int(self.headers.get("content-length") or 0), 4096)
            text = str(json.loads(self.rfile.read(length) or b"{}").get("text", "")).strip()[:300]
        except ValueError:
            self._send(400, {"error": "send JSON: {\"text\": ...}"})
            return
        if not text:
            self._send(400, {"error": "Name a headliner, and a city if you have one."})
            return
        try:
            self._send(200, ask(text))
        except QlooError as error:
            self._send(502, {"error": f"Qloo did not answer: {error}"})

    def log_message(self, fmt, *args):
        sys.stdout.write("%s %s\n" % (self.address_string(), fmt % args))


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8790"))
    server = http.server.ThreadingHTTPServer((host, port), Handler)
    print(f"http://{host}:{port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
