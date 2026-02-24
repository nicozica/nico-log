# nico.com.ar low-tech portal

Static indie portal generated with Python, designed for a Raspberry Pi workflow:
- Build/dev on Raspberry Pi 5 (`Pipa`)
- Serve in production on Raspberry Pi Zero 2W (`Pipita`) via NGINX + Cloudflare Tunnel

## Architecture

- `content/`: notes + config + feeds + tiny text + webring
- `templates/`: Jinja templates for homepage and sections
- `static/`: CSS and minimal JS assets
- `generator/`: Python static generator + data adapters
- `cache/`: runtime cache for dynamic fetches (ignored in git)
- `dist/`: generated static output (ignored in git)
- `scripts/`: helper scripts (build, new note, deploy)
- `systemd/`: service + timer units for Pipita
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

## Deploy to Pipita

```bash
./scripts/deploy-pipita.sh pipita
```

What it does:
1. Runs local build on Pipa.
2. Rsyncs repo to `/srv/repos/personal/nico.com.ar` on Pipita.
3. Creates/updates remote venv and installs requirements.
4. Ensures runtime folders:
   - `/srv/data/www/nico.com.ar`
   - `/srv/data/nico-portal-cache`
   - `/srv/logs/nico-portal`
5. Installs systemd unit/timer under `/etc/systemd/system/`.
6. Enables timer and runs initial build + sync to web root.

## Systemd runtime

Unit: `systemd/pipita-portal-generate.service`
- oneshot build
- sync `dist/ -> /srv/data/www/nico.com.ar`

Timer: `systemd/pipita-portal-generate.timer`
- runs every 30 minutes
- persistent across reboots

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
- `dist/status/index.html`
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
- Timer not running on Pipita:
  - `sudo systemctl status pipita-portal-generate.timer`
  - `sudo journalctl -u pipita-portal-generate.service -n 100 --no-pager`
