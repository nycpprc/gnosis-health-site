#!/usr/bin/env python3
"""One-off importer: turns the Squarespace backup (gnosis-backup/) into content/.

Usage:  python scripts/import_backup.py /path/to/gnosis-backup

* Writes content/posts/<date-slug>/index.md (+ optimized images, audio)
* Writes content/pages/*.md (+ images)
* Cleans Squarespace leftovers (duplicate featured image, newsletter block,
  indented paragraphs that Markdown would treat as code, filename alt text).
* KNOWN SOURCE DEFECT (fixed by hand in content/, now guarded by the "possible lost spaces" warning in
  build.py): the backup's HTML->Markdown step (markdownify in gnosis-backup/scripts/build_backup.py) drops
  whitespace-only inline elements such as `<strong> </strong>` and strips a trailing space/&nbsp; inside
  `<a>` text, gluing words together ("influences.Parents", "from“Situated"). If you ever re-import, run
  build.py and check its stderr for lost-space warnings.
Originals are NOT copied: images are resized to max 1600px wide WebP.
"""
import csv, hashlib, re, shutil, sys
from pathlib import Path
import yaml
from PIL import Image

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/gnosis-backup")
ROOT = Path(__file__).resolve().parent.parent
OUT_POSTS = ROOT / "content" / "posts"
OUT_PAGES = ROOT / "content" / "pages"
MAXW = 1600

# old (random) Squarespace slugs -> new slug (redirect stubs are generated from `aliases`)
# NOTE: four further slugs (velocipastor, care-vs-justice, connecting-your-mind, human-development-case-study)
# were renamed by hand in content/ after import; this importer predates those renames.
ALIASES = {
    "emotion-focused-therapy": ["q6cjbp9wii8jwxa9oac4n2pnwo5i9a"],
    "relationship-distress-anxiety-bowen": ["tegkds41h3nn3ah0hgnychdyosghen"],
    "general-systems-theory-domestic-violence": ["43ltzo9i2k031x2ydhcsq9evgghinw"],
    "cognitive-behavioral-theory-reflections": ["s5kuny58jlfzigwpkxagw4jjmbdgzz"],
    "confronting-suicide": ["xdmbjeminlumpuqsxwkut0gug8anm5"],
    "nycpprc2025": ["-nyc-philosophy-amp-psychology-readers-conference-2025-nycpprc2025"],
}

def md5(p): return hashlib.md5(Path(p).read_bytes()).hexdigest()

def safe_name(name):
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    stem = re.sub(r"^[0-9a-f]{8}-", "", stem)          # Squarespace hash prefix
    stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower() or "image"
    return stem[:60]

def optimize(src, dst):
    im = Image.open(src)
    im.load()
    if im.width > MAXW:
        h = round(im.height * MAXW / im.width)
        im = im.resize((MAXW, h), Image.LANCZOS)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if "A" in im.mode or im.mode == "P" else "RGB")
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "WEBP", quality=74, method=6)

FILENAME_ALT = re.compile(r"(\.(jpe?g|png|gif|webp|heic)$)|^(IMG|PXL|WhatsApp|image|Screenshot|DSC)[ _\-0-9]", re.I)

def clean_alt(alt):
    alt = alt.strip()
    if not alt or alt.lower() == "featured image" or FILENAME_ALT.search(alt):
        return ""
    return alt

def dedent_paragraphs(text):
    out, prev_blank = [], True
    in_fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        if (not in_fence and prev_blank and line[:1] == " "
                and not re.match(r"^\s+([-*+]|\d+[.)])\s", line)):
            line = line.strip()
        prev_blank = not line.strip()
        out.append(line)
    return "\n".join(out)

def split_front(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return yaml.safe_load(m.group(1)), m.group(2)

def process_body(body, srcdir, outdir, featured_rel):
    """Rewrite images, strip duplicates; returns (new_body, featured_out, media_copied)."""
    body = body.replace("\u200d", "").replace("\ufffc", "").replace("\u200b", "")
    body = re.sub(r"^# .*\n", "", body.lstrip("\n"), count=1)           # drop duplicate H1
    featured_hash, featured_out = None, None
    if featured_rel and (srcdir / featured_rel).exists():
        featured_hash = md5(srcdir / featured_rel)
    body = re.sub(r"^!\[featured image\]\([^)]*\)\n+", "", body, flags=re.M)
    written = {}   # md5 -> out filename
    used = set()

    def handle(rel):
        nonlocal featured_out
        rel = rel.replace("%20", " ")
        f = srcdir / rel
        if not f.exists():
            print("  MISSING", srcdir.name, rel); return rel
        h = md5(f)
        if h in written: return "images/" + written[h]
        stem = safe_name(f.name); name = stem + ".webp"; i = 2
        while name in used: name = f"{stem}-{i}.webp"; i += 1
        used.add(name); written[h] = name
        optimize(f, outdir / "images" / name)
        return "images/" + name

    if featured_rel and featured_hash:
        featured_out = handle(featured_rel)
    # remove first body image identical to featured image
    dup_done = False
    def img_sub(m):
        nonlocal dup_done
        alt, rel = m.group(1), m.group(2)
        f = srcdir / rel.replace("%20", " ")
        if (not dup_done and featured_hash and f.exists() and md5(f) == featured_hash):
            dup_done = True
            return "\x00DUP\x00"
        return f"![{clean_alt(alt)}]({handle(rel)})"
    body = re.sub(r"!\[([^\]]*)\]\((images/[^)]+)\)", img_sub, body)
    # linked images that point to the same file
    body = re.sub(r"\]\((images/[^)]+)\)", lambda m: f"]({handle(m.group(1))})" if (srcdir / m.group(1).replace('%20',' ')).exists() else m.group(0), body)
    body = re.sub(r"^\x00DUP\x00\n+", "", body, flags=re.M)
    body = body.replace("\x00DUP\x00", "")
    # media (audio)
    media = srcdir / "media"
    if media.exists():
        (outdir / "media").mkdir(exist_ok=True)
        for f in media.iterdir():
            shutil.copy2(f, outdir / "media" / f.name)
    body = dedent_paragraphs(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body, featured_out

def write_md(path, front, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body}", encoding="utf-8")

def import_posts():
    if OUT_POSTS.exists(): shutil.rmtree(OUT_POSTS)
    rows = list(csv.DictReader(open(SRC / "posts-index.csv", encoding="utf-8")))
    for r in rows:
        d = SRC / "posts" / f"{r['date']}-{r['slug']}"
        text = (d / "index.md").read_text(encoding="utf-8")
        fm, body = split_front(text)
        out = OUT_POSTS / d.name
        body, feat = process_body(body, d, out, fm.get("featured_image"))
        front = {"title": fm["title"], "date": r["date"], "slug": r["slug"]}
        if fm.get("tags"): front["tags"] = fm["tags"]
        if feat: front["image"] = feat
        if r["slug"] in ALIASES: front["aliases"] = ALIASES[r["slug"]]
        write_md(out / "index.md", front, body)
    print("posts:", len(rows))

NEWSLETTER = re.compile(r"\n*Newsletter Block\n.*$", re.S)

def resume_markup(body):
    """Turn flat resume paragraphs into  #### Role / meta lines / description."""
    date_re = re.compile(r"^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) )?\d{4}( – ((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) )?(\d{4}|Present))?( · .*)?$")
    parts = re.split(r"(?m)^(### .*)$", body)
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        head, sect = parts[i], parts[i + 1]
        paras = [p.strip() for p in re.split(r"\n\s*\n", sect.strip()) if p.strip() and p.strip() != "---"]
        if head.strip() == "### Interests":
            out.append(f"{head}\n\n" + "\n\n".join(paras) + "\n\n"); continue
        dates = [k for k, p in enumerate(paras) if date_re.match(p)]
        entries, starts = [], []
        for k in dates:
            s = k - 2
            while s >= 0 and paras[s + 2 - 1 + 1 - 1].startswith("See:") and False: pass
            # walk back over "See:" lines sitting between org and date
            j = k - 1
            while j >= 0 and paras[j].startswith("See:"): j -= 1
            starts.append(max(j - 1, 0))
        md = [f"{head}\n"]
        for n, k in enumerate(dates):
            end = starts[n + 1] if n + 1 < len(dates) else len(paras)
            role, org = paras[starts[n]], paras[starts[n] + 1]
            see = [p for p in paras[starts[n] + 2:k]]
            desc = paras[k + 1:end]
            md.append(f"#### {role}\n\n{org}  \n*{paras[k]}*" + "".join(f"  \n{s}" for s in see) + "\n")
            for p in desc: md.append(p + "\n")
        out.append("\n".join(md) + "\n")
    return "".join(out)

def import_pages():
    if OUT_PAGES.exists(): shutil.rmtree(OUT_PAGES)
    for slug in ["home", "about", "contact", "doing-business"]:
        d = SRC / "pages" / slug
        fm, body = split_front((d / "index.md").read_text(encoding="utf-8"))
        body = NEWSLETTER.sub("", body.replace("\u200d", "").replace("\u200b", ""))
        body = re.sub(r"^# .*\n", "", body.lstrip("\n"), count=1).strip() + "\n"
        outdir = OUT_PAGES
        front = {"title": fm["title"], "slug": slug}
        # copy page images (not favicons) with safe names
        for m in ([] if slug == "home" else re.finditer(r"!\[([^\]]*)\]\((images/[^)]+)\)", body)):
            f = d / m.group(2)
            name = safe_name(f.name) + ".webp"
            optimize(f, OUT_PAGES / "images" / name)
            body = body.replace(m.group(0), f"![{m.group(1)}](images/{name})")
        if slug == "home":
            body = re.sub(r"!\[[^\]]*\]\(images/[^)]+\)\n*", "", body)          # image placed by template
            body = re.sub(r"^## Welcome\n+", "", body)
            front["heading"] = "Welcome"
        if slug == "about":
            body = re.sub(r"^## About\n+", "", body)
            body = body.replace("![](images/me.webp)", "![Ryan Bohman standing and smiling in a lecture room](images/me.webp)")
            body = body.replace("(/doing-business)", "(/doing-business/)")
        if slug == "contact":
            body = re.sub(r"^## Contact me\.\n+", "", body)
            front["heading"] = "Contact me."
            body = body.replace("ryan@gnosis.health", "<ryan@gnosis.health>")
            lines = body.strip().split("\n")
            email = lines[0]
            addr = [l for l in lines[1:] if l.strip()]
            body = email + "\n\n" + "  \n".join(addr) + "\n"
        if slug == "doing-business":
            body = resume_markup(body)
            body = body.replace("\n---\n", "\n")
        write_md(OUT_PAGES / f"{slug}.md", front, body)
    print("pages: 4")

if __name__ == "__main__":
    import_posts(); import_pages()
