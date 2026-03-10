# nico.com.ar low-tech portal

Static indie portal generated with Python, designed for a Raspberry Pi workflow:
- Build/dev on Raspberry Pi 5 (`Pipa`)
- Serve in production on Raspberry Pi Zero 2 W (`Pizero`) via NGINX + Cloudflare Tunnel

## Architecture

- `content/`: notes + config + feeds + tiny text + webring
- `templates/`: Jinja templates for homepage and sections
- `static/`: CSS and minimal JS assets
- `generator/`: Python static generator + data adapters
- `cache/`: runtime cache for dynamic fetches (ignored in git)
- `dist/`: generated static output (ignored in git)
- `scripts/`: helper scripts (build, new note, deploy)
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

Python deps are in `requirements.txt`:
`requests`, `pyyaml`, `feedparser`, `markdown`, `jinja2`, `python-dateutil`.

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

## Deploy to Pizero

```bash
./scripts/deploy-pizero.sh pizero
```

What it does:
1. Runs local build on Pipa.
2. Ensures `/srv/data/www/nico.com.ar` exists on Pizero.
3. Disables legacy `pizero-portal-generate.timer` if present.
4. Rsyncs `dist/` to `/srv/data/www/nico.com.ar/`.

Scheduler model:
- Build timer runs only on Pipa (`nico-log-build.timer`).
- Pizero only serves static files via NGINX.

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

## Troubleshooting

- Build fails with missing venv module:
  - install system package: `python3-venv`
- Build renders only fallback feed/weather:
  - expected when network is unavailable; check `cache/*.json` after successful run
- Status shows `unknown` services:
  - expected on systems without `systemctl` or where service names differ
- Timer not running on Pipa:
  - `sudo systemctl status nico-log-build.timer`
  - `sudo journalctl -u nico-log-build.service -n 100 --no-pager`
