---
note_id: 2026-04-15-este-website-se-mudo-a-alpine
lang: en
title: This Website Moved to Alpine
date: 2026-04-15
tags:
- alpine-linux
- raspberry-pi-zero-2w
- nginx
- cloudflare-tunnel
- low-tech
slug: this-website-moved-to-alpine
summary: After seeing how well Pipeta behaved with Alpine Linux, I ended up migrating
  Pipita too, the Raspberry Pi Zero 2 W that serves nico.com.ar, run.nico.ar, and
  zero.nico.ar. The surprise was that the hardest part was not restoring NGINX or
  the tunnel, but sorting out headless WiFi.
---

A few days ago I wrote about **Pipeta**, a Raspberry Pi Zero 2 W with Alpine Linux meant to be a pure sandbox. The idea was to experiment without pressure, without production, and without turning every test into infrastructure.

What I did not expect was that the same experience would end up pushing another, more concrete decision: migrating the other Zero 2 W as well. That is where `nico.com.ar`, `run.nico.ar`, and `zero.nico.ar` live, all served with NGINX behind Cloudflare Tunnel.

The reason for the change was the solid behavior Alpine Linux had already shown. While Pipeta, on Alpine, was behaving impeccably, Pipita was still on 32-bit Raspberry Pi OS Lite and would sometimes drift into weird states where it looked connected to WiFi but in practice had gone half zombie. It did not happen all the time, but enough to stop feeling reliable.

So I did what had to be done: backed up the sites, inventoried the config, cleaned up everything I had already offloaded to other machines, and reinstalled from scratch.

Curiously, the hardest part was not bringing **NGINX** back up, or restoring **Cloudflare Tunnel**, or getting the deploy flow via `rsync` working again. The most annoying bit was something much more basic: the damn **headless WiFi**, which would later let me get SSH access and do the setup.

Once that was fixed, the rest came together very quickly: new user, SSH, restored sites, active tunnel, deploys working again, and everything serving as before.

In the end, the result was very good. Not so much because I had “migrated infrastructure,” but because I had put this machine on a much more coherent base for what it does: 64-bit Alpine Linux, 512 MB of RAM, NGINX, and an outbound Cloudflare tunnel.

There was also something interesting about seeing how a simple lab-machine experiment ended up improving another one that actually does real work. Sometimes a sandbox does not just help you learn: it also clears the path for what comes next.

In this case, at least for now, it seems like it was worth it.
