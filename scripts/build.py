#!/usr/bin/env python3
"""Static site generator for Gnosis Health.

    python scripts/build.py                 # uses config.json
    BASE_PATH=/gnosis-health-site NOINDEX=true python scripts/build.py
    BASE_PATH= SITE_ORIGIN=https://www.gnosis.health NOINDEX=false python scripts/build.py

Environment overrides: BASE_PATH, SITE_ORIGIN, NOINDEX.
Output goes to site/.
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xesc

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "site"
MAX_IMG_W = 1600
THUMB_W = 640
OG_W = 1200

# ----------------------------------------------------------------------------
# config
# ----------------------------------------------------------------------------
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
if "BASE_PATH" in os.environ:
    CFG["base_path"] = os.environ["BASE_PATH"]
if "SITE_ORIGIN" in os.environ:
    CFG["site_origin"] = os.environ["SITE_ORIGIN"]
if "NOINDEX" in os.environ:
    CFG["noindex"] = os.environ["NOINDEX"].strip().lower() in ("1", "true", "yes", "on")
BASE = "/" + CFG["base_path"].strip("/") if CFG["base_path"].strip("/") else ""
ORIGIN = CFG["site_origin"].rstrip("/")


def U(path="/"):
    """Site-relative URL (with base path)."""
    return BASE + path


def ABS(path="/"):
    """Absolute URL."""
    return ORIGIN + BASE + path


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def fmt_date(d):
    return d.strftime("%B %-d, %Y")


def split_front(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


def strip_tags(h):
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


INTRO_RE = re.compile(r"^(I wrote this|I created this|I have included|I included)", re.I)


def make_excerpt(h, title="", n=190):
    skipped = []
    for p in re.findall(r"<p>(.*?)</p>", h, re.S):
        if "<img" in p or "embed" in p:
            continue
        t = collapse(strip_tags(p))
        if len(t) < 40 or re.fullmatch(r"\s*<strong>.*</strong>\s*", p, re.S):
            continue
        if title and t.lower().strip(" .:") == title.lower().strip(" .:"):
            continue
        # skip the usual "I wrote this for my class…" context line when there is more to quote
        if not skipped and INTRO_RE.match(t) and h.count("<p>") > 2:
            skipped.append(p)
            continue
        if len(t) <= n:
            return t
        cut = t[:n].rsplit(" ", 1)[0].rstrip(",;:—-– ")
        return cut + "…"
    return ""


IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
IMG_INFO = {}        # output path -> (w, h)
BROKEN = []          # (page, ref)


def save_webp(im, dst, q=76):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if "A" in im.mode or im.mode == "P" else "RGB")
    im.save(dst, "WEBP", quality=q, method=4)


def process_image(src: Path, out_dir: Path, rel: str):
    """Optimize `src` into out_dir/<rel with .webp>; return new rel path or None."""
    if not src.exists():
        return None
    ext = src.suffix.lower()
    new_rel = rel if ext == ".webp" else str(Path(rel).with_suffix(".webp"))
    dst = out_dir / new_rel
    if dst in IMG_INFO:
        return new_rel
    im = Image.open(src)
    im.load()
    if im.width > MAX_IMG_W or ext != ".webp":
        if im.width > MAX_IMG_W:
            im = im.resize((MAX_IMG_W, round(im.height * MAX_IMG_W / im.width)), Image.LANCZOS)
        save_webp(im, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    IMG_INFO[dst] = (im.width, im.height)
    return new_rel


# ----------------------------------------------------------------------------
# markdown -> html
# ----------------------------------------------------------------------------
def new_md():
    return markdown.Markdown(
        extensions=["extra", "sane_lists", "nl2br", "smarty", "toc"],
        extension_configs={"smarty": {"smart_dashes": False}},
        output_format="html",
    )


YT_RE = re.compile(r"(?:youtube\.com/(?:watch\?(?:[^\"#]*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})")
SOLE_LINK = re.compile(r'<p>\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</p>', re.S)


def embed_blocks(h):
    def sub(m):
        href, label = html.unescape(m.group(1)), m.group(2)
        yt = YT_RE.search(href)
        plain = collapse(strip_tags(label))
        if yt:
            vid = yt.group(1)
            title = re.sub(r"^[▶►\s]*(Video:)?\s*", "", plain) or "YouTube video"
            return (
                '<figure class="embed"><div class="embed__frame">'
                f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="Video: {html.escape(title)}" '
                'loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>'
                f'<figcaption><a href="https://www.youtube.com/watch?v={vid}" rel="noopener">{html.escape(title)} · watch on YouTube</a></figcaption></figure>'
            )
        if re.search(r"\.(m4a|mp3|ogg|wav)$", href, re.I):
            title = re.sub(r"^[^\w]*(Audio:)?\s*", "", plain) or "Audio"
            mime = "audio/mp4" if href.lower().endswith("m4a") else "audio/mpeg"
            return (
                f'<figure class="audio"><figcaption><span class="audio__label">Listen</span> {html.escape(title)}</figcaption>'
                f'<audio controls preload="none"><source src="{html.escape(href)}" type="{mime}">'
                f'<a href="{html.escape(href)}">Download the audio</a></audio></figure>'
            )
        return m.group(0)
    return SOLE_LINK.sub(sub, h)


def shift_headings(h):
    levels = [int(x) for x in re.findall(r"<h([1-6])[ >]", h)]
    if not levels:
        return h
    shift = min(levels) - 2
    if shift <= 0:
        return h
    return re.sub(r"<(/?)h([1-6])([ >])", lambda m: f"<{m.group(1)}h{max(2, int(m.group(2)) - shift)}{m.group(3)}", h)


REF_MARK = re.compile(r"<(p|h[2-6])[^>]*>\s*(?:<strong>)?\s*(References?|Works Cited|Bibliography|Sources)\s*:?\s*(?:</strong>)?\s*</\1>", re.I)


def mark_references(h):
    out, pos, m = [], 0, REF_MARK.search(h)
    if not m:
        return h
    head = h[: m.end()]
    tail = h[m.end():]
    # paragraphs after the marker, up to the next heading, are reference entries
    parts = re.split(r"(?=<h[2-6][ >])", tail, maxsplit=1)
    refs = parts[0].replace("<p>", '<p class="ref">')
    return head.replace(m.group(0), m.group(0).replace("<p>", '<p class="ref-title">', 1)) + '<div class="references">' + refs + "</div>" + (parts[1] if len(parts) > 1 else "")


IMG_P = re.compile(r"<p>\s*((?:(?:<a [^>]*>\s*)?<img [^>]*>(?:\s*</a>)?\s*(?:<br\s*/?>)?\s*)+)</p>", re.S)
IMG_ITEM = re.compile(r"(?:<a [^>]*>\s*)?<img [^>]*>(?:\s*</a>)?", re.S)


def group_images(h):
    """Sole-image paragraphs -> <figure>; runs of 3+ -> gallery grid."""
    blocks = []
    pos = 0
    pieces = []
    for m in IMG_P.finditer(h):
        pieces.append((m.start(), m.end(), IMG_ITEM.findall(m.group(1))))
    out, i, last = [], 0, 0
    while i < len(pieces):
        j = i
        while j + 1 < len(pieces) and h[pieces[j][1]: pieces[j + 1][0]].strip() == "":
            j += 1
        run = pieces[i: j + 1]
        items = [it for p in run for it in p[2]]
        out.append(h[last: run[0][0]])
        if len(items) >= 3:
            out.append('<div class="gallery">' + "".join(f"<figure>{it}</figure>" for it in items) + "</div>")
        else:
            out.append("".join(f'<figure class="figure">{it}</figure>' for it in items))
        last = run[-1][1]
        i = j + 1
    out.append(h[last:])
    return "".join(out)


EXT_LINK = re.compile(r'<a href="(https?://[^"]+)"')
GNOSIS_ABS = re.compile(r"^https?://(?:www\.)?gnosis\.health(/[^\"#?]*)?([?#].*)?$")


def fix_links(h, known_paths, alias_map=None):
    alias_map = alias_map or {}
    # 1) root-relative links written in markdown ("/doing-business") -> base-relative, trailing slash
    def root_rel(m):
        p = m.group(1)
        if p.startswith("//"):
            return m.group(0)
        q = p.split("#")[0].split("?")[0]
        if q != "/" and not q.endswith("/") and "." not in q.rsplit("/", 1)[-1]:
            p = p.replace(q, q + "/", 1)
        return f'<a href="{U(p)}"'
    h = re.sub(r'<a href="(/[^"]*)"', root_rel, h)

    # 2) absolute links to the old domain -> internal links; other external links get rel=noopener
    def ext(m):
        href = m.group(1)
        g = GNOSIS_ABS.match(href)
        if g:
            p = (g.group(1) or "/").rstrip("/") or "/"
            if p == "/home":
                p = "/"
            new = p if p == "/" else p + "/"
            new = alias_map.get(new, new)
            if new == "/" or new in known_paths:
                return f'<a href="{U(new)}{g.group(2) or ""}"'
            return m.group(0)
        return f'<a rel="noopener" href="{href}"'
    return EXT_LINK.sub(ext, h)


def finish_images(h, src_dir: Path, out_dir: Path, page_label: str):
    """Optimize local images, add dimensions/lazy loading, copy other local assets."""
    def sub_img(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        if re.match(r"^(https?:|data:|/)", src):
            return tag
        rel = html.unescape(src)
        new_rel = process_image(src_dir / rel, out_dir, rel)
        if new_rel is None:
            BROKEN.append((page_label, src))
            return tag
        w, hh = IMG_INFO[out_dir / new_rel]
        tag = tag.replace(f'src="{src}"', f'src="{html.escape(new_rel)}" width="{w}" height="{hh}" loading="lazy" decoding="async"')
        if "alt=" not in tag:
            tag = tag.replace("<img ", '<img alt="" ', 1)
        return tag
    h = re.sub(r"<img [^>]*>", sub_img, h)
    # linked images pointing at original file -> optimized file
    def sub_a(m):
        href = html.unescape(m.group(1))
        if re.match(r"^(https?:|mailto:|#|/)", href):
            return m.group(0)
        ref = href.split("#")[0]
        f = src_dir / ref
        if Path(ref).suffix.lower() in IMG_EXT:
            new_rel = process_image(f, out_dir, ref)
            if new_rel is None:
                BROKEN.append((page_label, href))
                return m.group(0)
            return f'<a href="{html.escape(new_rel)}"'
        if f.is_file():
            dst = out_dir / ref
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
        return m.group(0)
    h = re.sub(r'<a (?:rel="noopener" )?href="([^"]+)"', sub_a, h)
    # audio sources / other local media
    def sub_src(m):
        src = html.unescape(m.group(1))
        if re.match(r"^(https?:|data:|/)", src):
            return m.group(0)
        f = src_dir / src
        if f.is_file():
            dst = out_dir / src
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
        else:
            BROKEN.append((page_label, src))
        return m.group(0)
    re.sub(r'<source src="([^"]+)"', sub_src, h)
    return h


def render_md(body, src_dir, out_dir, label, known_paths, alias_map=None):
    md = new_md()
    h = md.convert(body)
    h = embed_blocks(h)
    h = shift_headings(h)
    h = mark_references(h)
    h = group_images(h)
    h = fix_links(h, known_paths, alias_map)
    h = finish_images(h, src_dir, out_dir, label)
    return h


# ----------------------------------------------------------------------------
# content loading
# ----------------------------------------------------------------------------
def load_posts():
    posts = []
    pdir = CONTENT / "posts"
    entries = []
    for p in sorted(pdir.iterdir()):
        if p.is_dir() and (p / "index.md").exists():
            entries.append((p.name, p / "index.md", p))
        elif p.suffix == ".md":
            entries.append((p.stem, p, p.parent))
    for stem, md_path, src_dir in entries:
        fm, body = split_front(md_path.read_text(encoding="utf-8"))
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", stem)
        date = fm.get("date") or (m.group(1) if m else None)
        if isinstance(date, dt.datetime):
            date = date.date()
        elif isinstance(date, str):
            date = dt.date.fromisoformat(date[:10])
        if not date:
            raise SystemExit(f"{md_path}: missing date (name the file YYYY-MM-DD-slug.md or add `date:`)")
        slug = fm.get("slug") or (m.group(2) if m else stem)
        if fm.get("draft"):
            continue
        posts.append(dict(fm=fm, body=body, date=date, slug=slug, stem=stem, src_dir=src_dir,
                          title=str(fm.get("title") or slug), tags=list(fm.get("tags") or []),
                          aliases=list(fm.get("aliases") or [])))
    posts.sort(key=lambda p: (p["date"], p["stem"]), reverse=True)
    slugs = [p["slug"] for p in posts]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    if dupes:
        raise SystemExit(f"duplicate slugs: {dupes}")
    return posts


def load_pages():
    pages = {}
    for f in sorted((CONTENT / "pages").glob("*.md")):
        fm, body = split_front(f.read_text(encoding="utf-8"))
        pages[f.stem] = dict(fm=fm, body=body, slug=f.stem)
    return pages


# ----------------------------------------------------------------------------
# writing
# ----------------------------------------------------------------------------
def write(path, text):
    p = OUT / path.lstrip("/")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    for f in ("favicon.ico", "favicon.svg", "apple-touch-icon.png"):
        if (ROOT / "assets" / "icons" / f).exists():
            shutil.copy2(ROOT / "assets" / "icons" / f, OUT / f)

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.globals.update(U=U, ABS=ABS, cfg=CFG, noindex=CFG["noindex"], year=dt.date.today().year,
                       fmt_date=fmt_date)
    env.filters["tojson_safe"] = lambda v: json.dumps(v, ensure_ascii=False).replace("</", "<\\/")

    posts = load_posts()
    pages = load_pages()
    alias_map = {f"/blog/{a}/": f"/blog/{p['slug']}/" for p in posts for a in p["aliases"]}
    known_paths = {"/about/", "/contact/", "/doing-business/", "/blog/"} | {f"/blog/{p['slug']}/" for p in posts}

    # ---- posts
    for p in posts:
        out_dir = OUT / "blog" / p["slug"]
        label = f"post:{p['slug']}"
        p["html"] = render_md(p["body"], p["src_dir"], out_dir, label, known_paths, alias_map)
        text = collapse(strip_tags(p["html"]))
        p["words"] = len(text.split())
        p["minutes"] = max(1, round(p["words"] / 230))
        p["excerpt"] = p["fm"].get("excerpt") or make_excerpt(p["html"], p["title"])
        p["text"] = text
        p["url"] = f"/blog/{p['slug']}/"
        p["year"] = p["date"].year
        p["image"] = p["thumb"] = p["og"] = None
        img = p["fm"].get("image")
        if img:
            rel = process_image(p["src_dir"] / img, out_dir, img)
            if rel is None:
                BROKEN.append((label, img))
            else:
                p["image"] = rel
                p["image_wh"] = IMG_INFO[out_dir / rel]
                im = Image.open(out_dir / rel)
                im.load()
                t = im.copy()
                t.thumbnail((THUMB_W, THUMB_W * 2), Image.LANCZOS)
                save_webp(t, out_dir / "thumb.webp", 72)
                p["thumb"] = "thumb.webp"
                o = im.convert("RGB")
                o.thumbnail((OG_W, OG_W), Image.LANCZOS)
                o.save(out_dir / "og.jpg", "JPEG", quality=82, optimize=True)
                p["og"] = "og.jpg"
        p["alt_missing"] = len(re.findall(r'<img alt=""', p["html"]))

    # ---- post pages
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        desc = p["excerpt"] or CFG["description"]
        og_img = ABS(f"{p['url']}{p['og']}") if p["og"] else ABS("/assets/og-default.jpg")
        page = env.get_template("post.html").render(
            post=p, newer=newer, older=older, title=f"{p['title']} — {CFG['site_name']}", page_title=p["title"],
            description=desc, canonical=ABS(p["url"]), og_type="article", og_image=og_img,
            nav="blog", published=p["date"].isoformat(), path=p["url"])
        write(p["url"] + "index.html", page)
        for old in p["aliases"]:
            write(f"/blog/{old}/index.html", env.get_template("redirect.html").render(target=ABS(p["url"]), target_rel=U(p["url"]), title="Redirecting…", description="", canonical=ABS(p["url"]), og_image=None, og_type="website", nav=None))

    # ---- pages
    def page_ctx(slug):
        pg = pages[slug]
        out_dir = OUT / ("" if slug == "home" else slug)
        pg["html"] = render_md(pg["body"], CONTENT / "pages", out_dir, f"page:{slug}", known_paths, alias_map)
        return pg, out_dir

    for slug in ("about", "contact", "doing-business"):
        pg, out_dir = page_ctx(slug)
        h1 = pg["fm"].get("heading") or pg["fm"]["title"]
        desc = {
            "about": "About Ryan Bohman and Gnosis Health: counseling, research, and philosophy book clubs.",
            "contact": "Contact Ryan Bohman at Gnosis Health in Rochester, NY.",
            "doing-business": "Working together: Ryan Bohman's interests in mental health and technology ventures, plus his resume.",
        }[slug]
        nav = {"about": "about", "contact": "contact", "doing-business": "work"}[slug]
        write(f"/{slug}/index.html", env.get_template("page.html").render(
            pg=pg, h1=h1, title=f"{pg['fm']['title']} — {CFG['site_name']}", description=desc,
            canonical=ABS(f"/{slug}/"), og_type="website", og_image=ABS("/assets/og-default.jpg"), nav=nav, path=f"/{slug}/",
            eyebrow={"about": "About", "contact": "Get in touch", "doing-business": "Working together"}[slug]))

    # home
    hp, hdir = page_ctx("home")
    latest = posts[:6]
    home_html = env.get_template("home.html").render(
        pg=hp, latest=latest, total=len(posts),
        title=f"{CFG['site_name']} — {CFG['tagline']}", description=CFG["description"], canonical=ABS("/"),
        og_type="website", og_image=ABS("/assets/og-default.jpg"), nav="home", path="/")
    write("/index.html", home_html)
    write("/home/index.html", env.get_template("redirect.html").render(target=ABS("/"), target_rel=U("/"), title="Redirecting…", description="", canonical=ABS("/"), og_image=None, og_type="website", nav=None))

    # blog index
    years = sorted({p["year"] for p in posts}, reverse=True)
    all_tags = sorted({t for p in posts for t in p["tags"]})
    write("/blog/index.html", env.get_template("blog.html").render(
        posts=posts, years=years, year_counts={y: sum(1 for p in posts if p["year"] == y) for y in years},
        all_tags=all_tags, title=f"Blog — {CFG['site_name']}",
        description=f"All {len(posts)} essays and reflections on psychology, counseling, and philosophy by Ryan Bohman.",
        canonical=ABS("/blog/"), og_type="website", og_image=ABS("/assets/og-default.jpg"), nav="blog", path="/blog/"))
    write("/blog/search.json", json.dumps([{"s": p["slug"], "t": p["title"].lower() + " " + p["text"].lower()} for p in posts], ensure_ascii=False, separators=(",", ":")))

    # 404
    write("/404.html", env.get_template("404.html").render(title=f"Page not found — {CFG['site_name']}", description="Page not found.",
                                                           canonical=ABS("/"), og_type="website", og_image=ABS("/assets/og-default.jpg"), nav=None, path="/404.html"))

    # ---- feed
    def absolutize(h, base_url):
        def sub(m):
            attr, val = m.group(1), m.group(2)
            if re.match(r"^(https?:|mailto:|#|data:)", val):
                return m.group(0)
            if val.startswith("/"):
                return f'{attr}="{ORIGIN}{val}"'
            return f'{attr}="{base_url}{val}"'
        return re.sub(r'\b(href|src)="([^"]*)"', sub, h)

    items = []
    for p in posts[: CFG["feed_items"]]:
        content = absolutize(p["html"], ABS(p["url"]))
        pub = email.utils.format_datetime(dt.datetime.combine(p["date"], dt.time(12, 0), tzinfo=dt.timezone.utc))
        enc = f'<img src="{ABS(p["url"] + p["og"])}" alt="" />' if p["og"] else ""
        items.append(f"""<item><title>{xesc(p['title'])}</title><link>{ABS(p['url'])}</link><guid isPermaLink="true">{ABS(p['url'])}</guid>
<pubDate>{pub}</pubDate><dc:creator>{xesc(CFG['author'])}</dc:creator><description>{xesc(p['excerpt'])}</description>
<content:encoded><![CDATA[{content.replace(']]>', ']]&gt;')}]]></content:encoded></item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>{xesc(CFG['site_name'])}</title><link>{ABS('/')}</link><description>{xesc(CFG['description'])}</description>
<language>{CFG['language']}</language><atom:link href="{ABS('/feed.xml')}" rel="self" type="application/rss+xml"/>
<lastBuildDate>{email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))}</lastBuildDate>
{chr(10).join(items)}
</channel></rss>
"""
    write("/feed.xml", feed)

    # ---- sitemap / robots
    urls = [("/", posts[0]["date"]), ("/blog/", posts[0]["date"]), ("/about/", None), ("/doing-business/", None), ("/contact/", None)]
    urls += [(p["url"], p["date"]) for p in posts]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d in urls:
        sm.append(f"<url><loc>{ABS(u)}</loc>" + (f"<lastmod>{d.isoformat()}</lastmod>" if d else "") + "</url>")
    sm.append("</urlset>")
    write("/sitemap.xml", "\n".join(sm) + "\n")
    if CFG["noindex"]:
        write("/robots.txt", "User-agent: *\nDisallow: /\n")
    else:
        write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {ABS('/sitemap.xml')}\n")
    (OUT / ".nojekyll").write_text("")
    if (ROOT / "CNAME").exists():           # custom domain (add at cutover)
        shutil.copy2(ROOT / "CNAME", OUT / "CNAME")

    # ---- report
    summary = dict(posts=len(posts), pages=len(pages), images=len(IMG_INFO), redirects=sum(len(p["aliases"]) for p in posts) + 1,
                   base_path=BASE, origin=ORIGIN, noindex=CFG["noindex"], broken_refs=BROKEN,
                   posts_missing_alt=sum(p["alt_missing"] for p in posts))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if BROKEN:
        print("WARNING: broken local references (see above)", file=sys.stderr)


if __name__ == "__main__":
    main()
