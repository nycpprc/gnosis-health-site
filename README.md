# Gnosis Health — static site

A small, dependency-light static site generator and the content for **gnosis.health**
(replacement for the Squarespace site). Python 3.11+, no JavaScript framework.

* Design: warm cream + deep indigo + golden sun; EB Garamond (headings), Source Serif 4 (text), Inter (UI) — all self-hosted (SIL OFL) in `assets/fonts/`.
* Output: `site/` (plain HTML/CSS, one tiny JS file for blog search/filter).
* **Temporary address:** https://nycpprc.github.io/gnosis-health-site/ (marked `noindex`).
  The live `gnosis.health` DNS is untouched; Squarespace stays live until you cut over.

## Layout

```
config.json            site name, author, meetups, base_path / site_origin / noindex
content/posts/         one folder per post:  YYYY-MM-DD-slug/index.md  (+ images/, media/)
                       or a single file:      YYYY-MM-DD-slug.md
content/pages/         home.md, about.md, contact.md, doing-business.md (+ images/)
templates/             Jinja2 templates
assets/                css, js, fonts, icons, og-default.jpg
scripts/build.py       the generator  ->  site/
scripts/check_links.py internal link / image / fragment checker
scripts/screenshots.py QA screenshots (Playwright + Chromium)
scripts/import_backup.py  one-off importer used to create content/ from the Squarespace backup
.github/workflows/deploy.yml  build + deploy to GitHub Pages on every push to main
```

## Build locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scripts/build.py            # -> site/   (uses config.json)
python scripts/check_links.py      # must report 0 broken references
python -m http.server -d /tmp/preview   # see below for serving under the base path
```

Configuration comes from `config.json`; environment variables override it:

| Variable      | Meaning                                              | Temporary address                | After cutover              |
|---------------|------------------------------------------------------|----------------------------------|----------------------------|
| `BASE_PATH`   | URL prefix the site is served under                  | `/gnosis-health-site`            | *(empty)*                  |
| `SITE_ORIGIN` | scheme + host used for canonical/og/sitemap     | `https://nycpprc.github.io`      | `https://www.gnosis.health`|
| `NOINDEX`     | `true` adds `<meta name="robots" content="noindex">` and a `Disallow: /` robots.txt | `true` | `false` |

Quick local preview at the right path:

```bash
mkdir -p /tmp/preview && ln -sfn "$PWD/site" /tmp/preview/gnosis-health-site
python -m http.server 8000 -d /tmp/preview   # http://localhost:8000/gnosis-health-site/
# or for a root-level preview:  BASE_PATH= python scripts/build.py && python -m http.server -d site
```

## Add a post

1. Create `content/posts/2026-11-03-my-new-post/index.md` (folder) — or just `content/posts/2026-11-03-my-new-post.md`.
   The part after the date is the URL slug → `/blog/my-new-post/`.
2. Front matter, then Markdown:

   ```markdown
   ---
   title: My new post
   date: 2026-11-03          # optional if the file name starts with the date
   image: images/cover.jpg   # optional hero/thumbnail (any jpg/png/webp; resized to max 1600px, converted to WebP)
   excerpt: One-sentence summary shown on the blog index.   # optional; otherwise auto-generated
   tags: [philosophy, counseling]                            # optional; if any post has tags, tag filters appear
   ---

   Your text. Images: `![Alt text](images/figure.jpg)` (put the files next to index.md).
   ```
3. Special lines (a paragraph containing only a link):
   * `[▶ Video: Title](https://www.youtube.com/watch?v=VIDEOID)` → responsive, lazy-loaded `youtube-nocookie.com` embed.
   * `[🎧 Audio: Title](media/recording.m4a)` → `<audio>` player (put the file in `media/` next to index.md).
   * A bold **References** paragraph turns the following paragraphs into a hanging-indent reference list.
4. `python scripts/build.py && python scripts/check_links.py`, then commit and push to `main`.
5. Set `draft: true` in the front matter to keep a post out of the build.

Reading time, previous/next links, `sitemap.xml` and the blog index are generated automatically.
Add **`aliases: [old-slug]`** to a post to generate a redirect stub from an old URL.

## Deploy

Pushing to `main` runs `.github/workflows/deploy.yml` (build → link-check → GitHub Pages).
Pages is configured with *Source: GitHub Actions* (Settings → Pages). Re-run manually from the Actions tab if needed.

## Cutover checklist (when you are ready to replace Squarespace)

1. Final content check on the temporary site; compare against Squarespace (new posts since the backup?).
2. Edit `config.json`: `"base_path": ""`, `"site_origin": "https://www.gnosis.health"`, `"noindex": false`.
3. Create a file named `CNAME` in the repo root containing `www.gnosis.health` (the build copies it into `site/`).
   Also enter the custom domain in Settings → Pages.
4. DNS at the registrar (keep Squarespace live until verified; lower the TTL a day before):
   * `www` → `CNAME` → `nycpprc.github.io`
   * apex `gnosis.health` → `A` records `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
     (optional `AAAA`: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`)
   * Remove the old Squarespace `A`/`CNAME` records for those names. Email (MX/TXT) records for `ryan@gnosis.health` must stay as they are.
5. In Settings → Pages: enter the custom domain, wait for the DNS check, tick **Enforce HTTPS**.
6. Verify: `/`, `/blog/`, a few posts, `/about/`, `/contact/`, `/doing-business/`, `/sitemap.xml`, the six old random-slug redirects, `/home/`.
7. Submit `https://www.gnosis.health/sitemap.xml` in Google Search Console (and re-verify the property).
   Add Google Analytics only now, if wanted (a snippet in `templates/base.html`).
8. Keep the Squarespace subscription until everything above is verified (and the domain is no longer pointed at it), then cancel.

Note: GitHub Pages serves `/blog/slug/` and 301-redirects `/blog/slug` to it, so every old Squarespace URL keeps working.
GitHub Pages cannot do server-side redirects; the renamed posts use meta-refresh + canonical stubs.

## Analytics (Google Analytics 4, optional, consent-gated)

Set `"ga_measurement_id": "G-XXXXXXXXXX"` in `config.json` (or env `GA_MEASUREMENT_ID`). Empty (the default) emits **no** analytics code, no consent notice, no `/privacy/` page and no footer link.
When set: Consent Mode defaults to *denied*; a small Accept/Decline notice is shown; `gtag.js` is requested **only after Accept** (choice kept in `localStorage["gh-analytics"]`, Global Privacy Control counts as Decline). Config uses `allow_google_signals: false` and `allow_ad_personalization_signals: false`.
`/privacy/` (`content/pages/privacy.md`) explains it and has a "Change my choice" button. Code: `assets/js/consent.js`, `templates/base.html`, consent styles at the end of `assets/css/site.css`.

## Credits / licences

Fonts: EB Garamond, Source Serif 4, Inter — SIL Open Font License 1.1 (self-hosted copies from Google Fonts).
Content © Ryan Bohman.

## Slug redirects

Old Squarespace URLs keep working through redirect stubs generated from each post's `aliases:` front matter
(meta refresh + canonical to the new URL). Internal links, sitemap and canonicals always use the new slug.
Current renames: j4wzh0eq8l58tr4cvi7x4d930gfwlg -> review-the-velocipastor, connecting-you -> connecting-your-mind-to-a-computer,
care-vs-justice-gilligan-vs-kohlberg-amp-piaget -> care-vs-justice-gilligan-kohlberg-piaget,
human-development-case-study-piaget-...-vygotsky -> human-development-case-study, plus six older random-slug stubs and /home/ -> /.
