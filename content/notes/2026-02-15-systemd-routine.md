---
title: Let systemd do the boring part
date: 2026-02-15T08:50:00-03:00
tags:
  - systemd
  - automation
---

A timer runs the generator every 30 minutes.

The service builds, syncs dist into NGINX root, and exits cleanly.

No long-running process, no node runtime, no drama.
