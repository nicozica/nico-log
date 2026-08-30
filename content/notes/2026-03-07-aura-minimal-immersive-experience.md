---
note_id: 2026-03-07-aura-production-deploy
lang: en
title: 'Aura: a Minimal, Immersive Experience'
date: 2026-03-07
tags:
- blurfm
- astro
- github-actions
- apache
- pwa
- radio
- automation
slug: aura-minimal-immersive-experience
summary: A new standalone player for Blur FM, with its own repo, automatic deploy
  to Apache, and a base ready to grow into a real app.
---

Today **Aura** went to production, the new standalone player for Blur FM, available at [play.blurfm.com](https://play.blurfm.com/).

The idea is to stop thinking of the player as “that thing kind of hanging off the site” and start treating it as its own **experience**, closer to a music app than to a traditional page.

### What got built

- A new project in its own repo
- Built on **Astro**
- Designed as an installable **PWA**
- Automatic deploy with **GitHub Actions**

### The good part about splitting it out

Blur FM's main site stays the “institutional” website, for lack of a better word.
Aura, on the other hand, starts as a 100% listening-focused experience.

I like that because it keeps the picture much clearer:

- [www.blurfm.com](https://www.blurfm.com/) as the site
- [play.blurfm.com](https://play.blurfm.com/) as the player app

Later on it will be possible to bring something lighter into the main site, but starting separately feels a lot healthier.

### What it borrowed from the old project

Aura did not come out of nowhere. It borrows visual references from Blur FM's main repo:

- Colors
- Logo
- Typography
- Overall look

All that without carrying over the old structure. It was important not to mix architectures.

### The deploy

The nice part was setting it up with the same overall approach I had already been using in Blur FM:

- Push to GitHub
- Automatic build
- Deploy via **SSH + rsync**
- Debian server configured with Apache

### MVP with minimum effort

The project started as a low-fi mockup in Excalidraw and quickly became a real URL. It turned into a product fairly fast.

It is not fully done, not even close, but it already has the important part: its own base, a clear identity, and deploy sorted out.

### Next step

Polish the player calmly:

- More robust real metadata
- A better-resolved dynamic background
- Recently played panel
- Fine-tuning for mobile and TV

But the most important thing already happened: **Aura exists.**
