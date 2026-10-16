#!/usr/bin/env python3
"""Render assets/og-default.jpg (1200x630 social card) with headless Chromium. Output is committed."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = f"""<!doctype html><meta charset=utf-8><style>
@import url('file://{ROOT}/assets/css/fonts.css');
html,body{{margin:0}}
.c{{width:1200px;height:630px;position:relative;overflow:hidden;color:#FFF8E6;font-family:'EB Garamond',serif;
background:linear-gradient(180deg,#1B2150 0%,#2F3479 38%,#84588C 58%,#E58F5E 80%,#F7C873 100%)}}
svg{{position:absolute;left:50%;bottom:-330px;transform:translateX(-50%)}}
.t{{position:absolute;top:96px;width:100%;text-align:center}}
h1{{font-weight:500;font-size:112px;margin:0;letter-spacing:.01em}}
p{{margin:14px 0 0;font-style:italic;font-size:38px;color:#EFE7D3}}
</style><div class=c><div class=t><h1>Gnosis Health</h1><p>Notes on psychology, counseling, and philosophy</p></div>
<svg width="760" height="760" viewBox="-380 -380 760 760"><defs><radialGradient id="g"><stop offset="0" stop-color="#FFE9A8" stop-opacity=".95"/><stop offset=".4" stop-color="#F6C453" stop-opacity=".5"/><stop offset="1" stop-color="#F6C453" stop-opacity="0"/></radialGradient>
<linearGradient id="d" x1="0" y1="-1" x2="0" y2="1"><stop offset="0" stop-color="#FFF1BF"/><stop offset="1" stop-color="#F2B33D"/></linearGradient></defs>
<circle r="380" fill="url(#g)"/><g stroke="#FBE3A0" stroke-linecap="round">{"".join(f'<line x1="0" y1="-150" x2="0" y2="-{200 if i%2==0 else 178}" transform="rotate({i*11.25})" stroke-width="{5 if i%2==0 else 3}" opacity="{0.85 if i%2==0 else .55}"/>' for i in range(32))}</g>
<circle r="120" fill="url(#d)"/></svg></div>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.set_content(HTML); pg.wait_for_timeout(600)
    pg.screenshot(path=str(ROOT / "assets" / "og-default.jpg"), type="jpeg", quality=88); b.close()
print("og-default.jpg written")
