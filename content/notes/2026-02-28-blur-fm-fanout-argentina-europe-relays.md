---
note_id: 2026-02-28-fanout-blurfm
lang: en
title: 'Blur FM Fanout: Argentina Origin, Europe Relays'
date: 2026-02-28
tags:
- blurfm
- icecast
- streaming
- infra
slug: blur-fm-fanout-argentina-europe-relays
summary: How I set up a simple Icecast fanout to serve Blur FM in Europe with lower
  latency while keeping now playing intact.
---

To make Blur FM work better, the idea was: **four qualities from SAM** (320, 128, 64 and 32 kbps), **Icecast in Argentina as the base**, **a relay in Europe** to spread the demand, and **Cloudflare** so the public URLs point to the most convenient endpoint (AR or EU).

In practice this ends up as a *fanout*: the “mother” Icecast publishes the streams, and one (or more) Icecast instances in Europe **join as a relay** and serve those same qualities locally.

### What problem it solves

- **Less latency** for listeners in Europe (it starts faster and drops less).
- **More stability**: if European traffic falls onto the relay, the source in Argentina gets some breathing room.
- **Consistency**: now playing comes from one place and looks the same on both sides.

### The magic part: streaming “RDS”

The best part is that not only the audio travels, but also the **metadata** (title, artist, etc.).
So the European relay ends up showing the same “Now Playing” as the source.

That helps because:

- The web player shows the current track without inventing anything.
- Many apps read that info directly from the stream.
- Cloudflare can send the user to the most convenient endpoint (AR or EU).
- Everything stays consistent and there is no need to maintain parallel systems.

### Result

The streams replicate in Europe, the load is distributed, and the experience improves, while keeping everything consistent. And on top of that, the public URLs are ready to grow in the future (finer routing, separate stats, whatever) without turning the infra into a Frankenstein.
