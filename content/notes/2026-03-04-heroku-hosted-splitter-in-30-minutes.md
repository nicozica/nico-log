---
note_id: 2026-03-04-locale-splitter
lang: en
title: A Heroku-Hosted Splitter in 30 Minutes
date: 2026-03-04
tags:
- ipsos
- tools
- i18n
- locales
- automation
- heroku
slug: heroku-hosted-splitter-in-30-minutes
summary: A tiny web app that splits a master translation TXT by locale markers and
  downloads a ZIP with ready-to-use HTML, with consistent naming.
---

In two iterations (half an hour, at most) I put together **locale-splitter**: a tiny web tool to trim the master translation TXT and download it as a **ZIP**, already **running on Heroku**.

The TXT contains concatenated HTML and the splitter cuts it when it finds separators like `|- (EN-PH) faq-contact-us`. Without that exact format, nothing gets cut or renamed.

### What the MVP does

- You upload a `.txt`
- It detects `|- (LOCALE) slug` markers
- It cuts the content between markers (without including the marker line)
- It generates a ZIP with all the HTML in one folder, with naming:
  - `(EN-US) faq-common-concerns.html`

### The crazy part

Codex not only generated the app (Node/Express), it also pushed it to GitHub and published it on Heroku. It got carried away creating a new repo at first even though I already had one defined, but with a redeploy pointing to the right repo it was ready.

### Next step

Add a `report.txt` in case there were warnings detected (for example markers with no content).
