---
title: Primera luz en Pipita
date: 2026-02-22T09:30:00-03:00
tags:
  - infra
  - raspberry
---

Hoy rehice el pipeline del portal para que aguante incluso en días de mala red.

La regla es simple: estático primero, caché siempre, dependencias mínimas.

Pipita sigue sirviendo aunque fallen por timeout los endpoints del clima o de los feeds.
