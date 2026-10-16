#!/usr/bin/env python3
"""QA screenshots with headless Chromium. Serves site/ under BASE_PATH on a local port.

    BASE_PATH=/gnosis-health-site python scripts/build.py && python scripts/screenshots.py
"""
import functools, http.server, os, shutil, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("BASE_PATH", "/gnosis-health-site").rstrip("/")
SHOTS = ROOT / "screenshots"
MAX_H = 6000   # cap very tall pages (long essays) to the first 6000 css px
LONG = os.environ.get("LONG_POST", "narcissism-test")
PAGES = {
    "home": "/",
    "blog": "/blog/",
    "post-youtube": "/blog/kants-critique-of-pure-reason/",
    "post-long-essay": f"/blog/{LONG}/",
    "post-audio": "/blog/what-is-truth/",
    "about": "/about/",
    "work": "/doing-business/",
    "contact": "/contact/",
}

tmp = Path(tempfile.mkdtemp())
(tmp / BASE.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
os.symlink(ROOT / "site", tmp / BASE.lstrip("/")) if BASE else None
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass
handler = functools.partial(Quiet, directory=str(tmp if BASE else ROOT / "site"))
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

SHOTS.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for label, w, h, scale in (("desktop", 1280, 900, 1), ("mobile", 390, 844, 2)):
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale, is_mobile=(label == "mobile"))
        pg = ctx.new_page()
        for name, path in PAGES.items():
            pg.goto(f"http://127.0.0.1:{port}{BASE}{path}", wait_until="load")
            pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
            pg.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=700){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,60));}window.scrollTo(0,0);}")
            try:
                pg.wait_for_function("[...document.images].every(i => i.complete)", timeout=30000)
            except Exception:
                print('images not all loaded:', name, label)
            pg.wait_for_timeout(500)
            overflow = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            clip = None
            full = name not in ("blog",)
            height = pg.evaluate('document.documentElement.scrollHeight')
            if height > MAX_H:
                # tall pages: grow the viewport instead of a clipped full-page capture (avoids sticky-header artefacts)
                pg.set_viewport_size({"width": w, "height": MAX_H}); pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(800)
                pg.screenshot(path=str(SHOTS / f"{name}-{label}.png"))
                pg.set_viewport_size({"width": w, "height": h})
            else:
                pg.screenshot(path=str(SHOTS / f"{name}-{label}.png"), full_page=True)
            if overflow > 0:
                print(f"HORIZONTAL OVERFLOW {overflow}px on {name} ({label})")
        ctx.close()
    b.close()
srv.shutdown()
print("screenshots saved in", SHOTS)
