---
title: First light on Pipita
date: 2026-02-22T09:30:00-03:00
tags:
  - infra
  - raspberry
---

Today I rebuilt the portal pipeline so it can survive bad network days.

The rule is simple: static first, cache always, dependencies minimal.

Pipita keeps serving even if weather or feed endpoints time out.
