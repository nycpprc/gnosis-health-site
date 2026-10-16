#!/usr/bin/env python3
"""Crawl site/ and verify every internal link, image, stylesheet, script, media source and #fragment.

    python scripts/check_links.py [--base /gnosis-health-site]

Exit code 1 if any internal reference is broken. Also reports <img> without alt attribute,
missing meta tags, and the redirect stubs.
"""
import argparse, json, os, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ap = argparse.ArgumentParser()
ap.add_argument("--base", default=None)
args = ap.parse_args()
cfg = json.loads((ROOT / "config.json").read_text())
BASE = args.base if args.base is not None else os.environ.get("BASE_PATH", cfg["base_path"])
BASE = "/" + BASE.strip("/") if BASE.strip("/") else ""
ORIGIN = os.environ.get("SITE_ORIGIN", cfg["site_origin"]).rstrip("/")


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.imgs_no_alt, self.meta = [], set(), 0, {}
        self.imgs = 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if a.get("id"): self.ids.add(a["id"])
        if tag == "a" and a.get("name"): self.ids.add(a["name"])
        if tag == "a" and a.get("href"): self.refs.append(("a", a["href"]))
        if tag == "link" and a.get("href") and a.get("rel") not in ("canonical",):
            self.refs.append(("link", a["href"]))
        if tag in ("script", "source", "audio", "video") and a.get("src"): self.refs.append((tag, a["src"]))
        if tag == "img":
            self.imgs += 1
            if a.get("src"): self.refs.append(("img", a["src"]))
            if "alt" not in a: self.imgs_no_alt += 1
        if tag == "meta":
            k = a.get("name") or a.get("property")
            if k: self.meta[k] = a.get("content")
        if tag == "meta" and a.get("http-equiv") == "refresh":
            self.meta["refresh"] = a.get("content")


def resolve(page_url, ref):
    """Map a reference to a file inside site/, or None if external / ignorable."""
    ref, frag = urldefrag(ref)
    if not ref:
        return page_url, frag
    pr = urlparse(ref)
    if pr.scheme in ("mailto", "tel", "javascript", "data"):
        return None
    if pr.scheme in ("http", "https"):
        if (pr.scheme + "://" + pr.netloc) == ORIGIN:
            path = pr.path
        else:
            return None
    elif ref.startswith("//"):
        return None
    elif ref.startswith("/"):
        path = pr.path
    else:
        d = page_url.rsplit("/", 1)[0] + "/"
        path = os.path.normpath(d + pr.path).replace(os.sep, "/")
        if pr.path.endswith("/") and not path.endswith("/"): path += "/"
    return unquote(path), frag


def to_file(url_path):
    if BASE and not (url_path == BASE or url_path.startswith(BASE + "/")):
        return None
    p = url_path[len(BASE):] if BASE else url_path
    f = SITE / p.lstrip("/")
    if p.endswith("/") or f.is_dir(): f = f / "index.html"
    return f


pages = {}
for f in SITE.rglob("*.html"):
    url = BASE + "/" + str(f.relative_to(SITE)).replace("index.html", "")
    url = url.replace("//", "/")
    pr = P(); pr.feed(f.read_text(encoding="utf-8")); pages[url] = (f, pr)

broken, checked, frag_missing = [], 0, []
ids_cache = {}
for url, (f, pr) in pages.items():
    for kind, ref in pr.refs:
        r = resolve(url, ref)
        if r is None: continue
        path, frag = r
        target = to_file(path)
        checked += 1
        if target is None or not target.exists():
            broken.append((url, kind, ref)); continue
        if frag and target.suffix == ".html":
            if target not in ids_cache:
                tp = P(); tp.feed(target.read_text(encoding="utf-8")); ids_cache[target] = tp.ids
            if frag not in ids_cache[target]:
                frag_missing.append((url, ref))

# sitemap + feed + redirect stubs
extra = []
for name in ("sitemap.xml", "feed.xml"):
    txt = (SITE / name).read_text(encoding="utf-8")
    for loc in re.findall(r"<(?:loc|link)>([^<]+)</(?:loc|link)>", txt):
        r = resolve("/", loc)
        if r and (to_file(r[0]) is None or not to_file(r[0]).exists()):
            extra.append((name, loc))
stubs = []
for url, (f, pr) in pages.items():
    if "refresh" in pr.meta:
        tgt = re.search(r"url=(\S+)", pr.meta["refresh"]).group(1)
        r = resolve(url, tgt); ok = r and to_file(r[0]) and to_file(r[0]).exists()
        stubs.append((url, tgt, bool(ok)))
        if not ok: broken.append((url, "redirect", tgt))

noindex_missing = [u for u, (f, pr) in pages.items() if "noindex" not in (pr.meta.get("robots") or "")]
real = [u for u in pages if u not in {s[0] for s in stubs}]
no_og = [u for u in real if not (pages[u][1].meta.get("og:title") and pages[u][1].meta.get("description"))]
imgs_total = sum(p.imgs for _, p in pages.values())
print(f"HTML pages: {len(pages)} ({len(stubs)} redirect stubs) | internal references checked: {checked} | images in HTML: {imgs_total}")
print(f"Broken internal references: {len(broken)}")
for b in broken[:50]: print("  BROKEN", b)
print(f"Missing #fragments: {len(frag_missing)}")
for b in frag_missing[:20]: print("  FRAG", b)
print(f"sitemap/feed URLs not found: {len(extra)}")
for b in extra[:20]: print("  ", b)
print(f"<img> without alt attribute: {sum(p.imgs_no_alt for _, p in pages.values())}")
print(f"pages missing og:title/description: {len(no_og)}")
print(f"pages without robots noindex: {len(noindex_missing)} (expected 0 while NOINDEX=true; all if false)")
for s in stubs: print("  redirect", s)
sys.exit(1 if broken or frag_missing or extra else 0)
