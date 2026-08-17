# WYSIWYG compatibility audit

Audit date: 2026-08-17  
Editor: TOAST UI Editor 3.2.2, WYSIWYG import followed by `getMarkdown()`  
Scope: every `content/notes/*.md` and `content/drafts/*.md` present at audit time

The comparison normalizes line endings and outer whitespace only. The browser repeats
this check whenever an editor opens. Exact round-trips use visual mode by default;
any difference destroys the visual instance and keeps the original plain Markdown
textarea before editing begins. This also avoids rendering incompatible raw HTML
inside the editor application's document.

## Exact round-trip

- `2026-02-26-bienvenidos-a-nico-log.md`
- `2026-03-16-nico-run-training-interpreted.md`
- `2026-04-15-este-website-se-mudo-a-alpine.md`
- `2026-05-04-aires-pulse-transaccion-pi-zeros.md`
- `2026-05-27-pc-segunda-vida-proxmox.md`
- `2026-07-16-migracion-heroku-docker.md`
- `2026-07-21-la-odisea-de-comprar-una-hamburguesa.md`
- `2026-07-24-blur-fm-15-cumple-15.md` (published)
- `2026-07-24-blur-fm-15-cumple-15.md` (draft)
- `2026-08-16-esta-es-una-nota-draft.md` (draft)

## Markdown fallback

- `2026-02-28-fanout-blurfm.md`: list markers are normalized and a Markdown hard break is lost.
- `2026-03-04-locale-splitter.md`: list markers and nested-list indentation are normalized.
- `2026-03-07-aura-production-deploy.md`: list markers are normalized and a Markdown hard break is lost.
- `2026-03-09-pacer-strava-brief-builder.md`: list markers/blank lines are normalized and several Markdown hard breaks are lost.
- `2026-04-05-alpine-linux-pipeta.md`: raw `<figure>` markup is destructively flattened; its class, lazy-loading attribute, self-closing image syntax, and `<figcaption>` structure are not preserved.

Links and headings in the audited exact-round-trip notes remain unchanged. Current
content contains no fenced code blocks or Markdown tables. TOAST UI supports their
CommonMark/GFM forms, but the per-document runtime comparison remains authoritative.
