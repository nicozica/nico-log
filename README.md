# nico.com.ar low-tech portal

Static indie portal generated with Python, designed for a Raspberry Pi workflow:
- Build/dev on Raspberry Pi 5 (`Pipa`)
- Serve in production on Raspberry Pi Zero 2 W (`Pizero`) via NGINX + Cloudflare Tunnel

## Architecture

- `content/notes/`: published Markdown source
- `content/drafts/`: private working copies, ignored by the public generator
- `content/`: config + feeds + tiny text + webring
- `templates/`: Jinja templates for homepage and sections
- `static/`: CSS and minimal JS assets
- `generator/`: Python static generator + data adapters
- `cache/`: runtime cache for dynamic fetches (ignored in git)
- `dist/`: generated static output (ignored in git)
- `scripts/`: helper scripts (build, new note, deploy)
- `systemd/`: reviewable service + timer definitions for Pipa
- `nginx/`: server block snippet

## Resilience model

Every data source uses cache + TTL:
- If API/feed fetch succeeds, cache is refreshed.
- If fetch fails, stale cache is reused.
- If no cache exists yet, fallback mock/default data is rendered.

This keeps the portal available even during upstream failures.

## Requirements

- Python 3.11+ recommended
- `python3-venv` package available
- Optional for deploy: `rsync`, `ssh`, `sudo` on target host

Python dependencies and their transitive versions are pinned in `requirements.txt`.

Bootstrap or refresh the virtualenv explicitly:

```bash
./scripts/bootstrap.sh
```

Builds do not install or upgrade dependencies automatically.

## Local editor

The local editor lists published notes and manages private working copies under `content/drafts/`. Saving remains private. Preview uses the public generator's Markdown renderer inside a sandboxed iframe. Publishing strictly validates the draft, atomically writes `content/notes/`, removes the draft only after that write, and then starts the canonical `nico-log-build.service`.

Run it on Pipa only:

```bash
.venv/bin/python -m editor.app
```

Open `http://127.0.0.1:5001/`. To test explicitly from the trusted LAN, use Flask's `--host 0.0.0.0` option; do not expose this unauthenticated development server through a tunnel.

```bash
.venv/bin/flask --app editor.app run --host 0.0.0.0 --port 5001
```

For a stable session/CSRF signing key, set `NICO_EDITOR_SECRET_KEY` in the editor process environment. Do not commit that value.

The editor never runs build or rsync commands itself. It may start only the existing publication unit using the exact command below:

```text
/usr/bin/sudo -n /usr/bin/systemctl start nico-log-build.service
```

The reviewed least-privilege sudoers rule is in `sudoers/nico-log-editor`. It is not installed automatically. Validate and install it manually:

```bash
cd /srv/repos/personal/argensonix/nico.com.ar
sudo /usr/sbin/visudo -cf sudoers/nico-log-editor
sudo install -o root -g root -m 0440 sudoers/nico-log-editor /etc/sudoers.d/nico-log-editor
sudo /usr/sbin/visudo -cf /etc/sudoers.d/nico-log-editor
```

The future production editor service should run as `nico`, matching current repository ownership. The rule grants that account only the exact `systemctl start nico-log-build.service` invocation; it does not grant arbitrary units, arguments, commands, shells, journal access, or environment access.

### Visual Markdown editor

The note body uses the plain-JavaScript TOAST UI Editor `3.2.2`, vendored under `editor/static/vendor/toastui-editor-3.2.2/`. Its version, upstream source, checksums context, and MIT license are kept with the vendored assets. There is no runtime CDN dependency or frontend build step.

Visual mode is the default only when loading and immediately exporting the body produces the same normalized Markdown. If TOAST UI would rewrite the source, the editor automatically stays in Markdown mode and explains why. The original textarea remains the form source and the existing draft, CSRF, preview, validation, and publication paths are unchanged.

## Local build (Pipa)

```bash
cd /srv/repos/personal/argensonix/nico.com.ar
./scripts/dev-build.sh
```

Output:
- Site: `dist/`
- Dynamic cache: `cache/`

## Publish a new note

```bash
./scripts/new-note.sh "My new note title"
```

This creates `content/notes/YYYY-MM-DD-slug.md` with front matter:
- `title`
- `date` (ISO)
- `tags[]`

Rebuild after editing.

## Drafts

`content/notes/*.md` is published source. `content/drafts/*.md` contains private working copies and is not read by the public generator.

The local editor uses the same filename for a published note and its draft. Publishing checks both draft and published-source revisions to prevent overwriting concurrent manual changes. If build/deploy fails after the atomic source write, the published Markdown is retained and the editor offers a deploy-only retry.

## Deploy to Pizero

```bash
./scripts/publish.sh
```

This is the canonical publication command. One lock covers the complete operation:

```text
Markdown source -> generator -> dist -> rsync -> Pizero
```

Concurrent publication attempts fail without starting a second build. `scripts/deploy-pizero.sh` remains as a compatibility wrapper.

Scheduler model:
- Build timer runs only on Pipa (`nico-log-build.timer`).
- The timer invokes `scripts/publish.sh` through `nico-log-build.service`.
- Pizero only serves static files via NGINX.

Repository unit files live under `systemd/`. The service reads runtime secrets from `/etc/nico-log/nico-log.env`; that file must remain outside Git and be owned by `root:root` with mode `0600`.

## NGINX

Use `nginx/nico.com.ar.conf` as a base snippet:
- listens on `127.0.0.1:8080`
- serves from `/srv/data/www/nico.com.ar`
- long cache for `/assets/`
- short/no-cache for HTML
- basic security headers

## Dynamic data providers

- Notes: local markdown in `content/notes/`
- Links: RSS feeds from `content/feeds.yaml`
- Weather: Open-Meteo (`lat/lon` from `content/config.yaml`)
- Weather provider can be switched to `WeatherAPI` via `content/config.yaml`
- `WeatherAPI` key is read from env var `WEATHERAPI_KEY`
- Status:
  - local systemd checks (services in `config.yaml`)
  - optional HTTP checks in `config.yaml`
- Now Playing:
  - if `now_playing_url` is set, fetch JSON with cache
  - else read `cache/now_playing.json`
  - fallback to `content/now_playing_mock.json`

## Build output map

`generator/build.py` produces:
- `dist/index.html`
- `dist/notes/index.html`
- `dist/notes/<slug>/index.html`
- `dist/links/index.html`
- `dist/now/index.html`
- `dist/about/index.html`
- `dist/notes/rss.xml`
- `dist/notes/atom.xml`
- `dist/notes/feed.json`
- `dist/assets/...`

## Image policy

Keep image handling simple and consistent:

- `SVG` for icons, logos, and simple illustrations.
- `WEBP` for photos and note images.
- `PNG` only when transparency/compatibility matters, such as social preview cards.
- `ICO` only for legacy favicon support.

Current examples in this repo:
- `static/img/about/*.webp` and `static/img/notes/*.webp`: photos/content images
- `static/img/*.svg` and `static/favicon.svg`: vector assets
- `static/img/logo_nicolog.png`: social preview image
- `static/favicon.ico`: fallback favicon

Convert a source image for the site with:

```bash
convert input.jpg -auto-orient -strip -resize '1600x1600>' -quality 82 output.webp
```

Then reference it from templates/notes as `/assets/...` and rebuild.

If you replace an existing image under `/assets/`, prefer a new filename instead of overwriting the old one.
Those files are served with long-lived immutable caching, so changing contents without changing the URL can leave browsers/CDNs showing the previous version.

## Troubleshooting

- Build fails with missing venv module:
  - install `python3-venv` if necessary, then run `./scripts/bootstrap.sh`
- Build renders only fallback feed/weather:
  - expected when network is unavailable; check `cache/*.json` after successful run
- Status shows `unknown` services:
  - expected on systems without `systemctl` or where service names differ
- Timer not running on Pipa:
  - `sudo systemctl status nico-log-build.timer`
  - `sudo journalctl -u nico-log-build.service -n 100 --no-pager`
