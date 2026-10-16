#!/usr/bin/env python3
"""Screenshot a handful of posts (desktop + mobile, light + dark) into a folder.
    python scripts/shots_posts.py screenshots/posts-before [slug ...]
"""
import functools, http.server, os, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("BASE_PATH", "/gnosis-health-site").rstrip("/")
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
slugs = sys.argv[2:] or ["schopenhauers-world-as-will-and-representation", "kants-critique-of-pure-reason",
    "review-the-velocipastor", "human-development-case-study", "emotion-focused-therapy",
    "exploring-autism", "narcissism-test", "using-the-correlational-method-to-study-cannabis-use-in-the-adolescent-brain"]
H = int(os.environ.get("SHOT_H", "2600"))
tmp = Path(tempfile.mkdtemp()); os.symlink(ROOT / "site", tmp / BASE.lstrip("/"))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(tmp)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    for label, w, sc, mob in (("desktop", 1280, 1, False), ("mobile", 390, 2, True)):
        for scheme in ("light", "dark"):
            if scheme == "dark" and label == "mobile": continue
            ctx = b.new_context(viewport={"width": w, "height": H}, device_scale_factor=sc, is_mobile=mob, color_scheme=scheme)
            pg = ctx.new_page()
            for s in slugs:
                pg.goto(f"http://127.0.0.1:{port}{BASE}/blog/{s}/", wait_until="load")
                pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
                pg.evaluate("async()=>{for(let y=0;y<4000;y+=600){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,50));}window.scrollTo(0,0);}")
                pg.wait_for_timeout(600)
                suffix = label + ("-dark" if scheme == "dark" else "")
                pg.screenshot(path=str(out / f"{s[:40]}-{suffix}.png"))
            ctx.close()
    b.close()
srv.shutdown(); print("saved", out)
