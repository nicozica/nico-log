---
note_id: 2026-04-15-este-website-se-mudo-a-alpine
lang: es
title: Este website se mudó a Alpine
date: 2026-04-15
slug: este-website-se-mudo-a-alpine
tags:
- alpine-linux
- raspberry-pi-zero-2w
- nginx
- cloudflare-tunnel
- low-tech
summary: Después de ver lo bien que se portó Pipeta con Alpine Linux, terminé migrando
  también a Pipita, la Raspberry Pi Zero 2 W que sirve nico.com.ar, run.nico.ar y
  zero.nico.ar. La sorpresa fue que lo más trabajoso no fue restaurar NGINX ni el
  túnel, sino dejar resuelto el WiFi headless.
---

Hace unos días escribí sobre **Pipeta**, una Raspberry Pi Zero 2 W con Alpine Linux pensada como sandbox puro. La idea era experimentar sin presión, sin producción y sin convertir cada prueba en infraestructura.

Lo que no esperaba era que esa misma experiencia terminara empujando otra decisión más concreta: migrar también la otra Zero 2 W. Ahí viven `nico.com.ar`, `run.nico.ar` y `zero.nico.ar`, todo servido con NGINX detrás de Cloudflare Tunnel.

La razón del cambio fue la solidez demostrada por Alpine Linux. Mientras Pipeta, con Alpine, se venía comportando de forma impecable, Pipita seguía en Raspberry Pi OS Lite de 32 bits y cada tanto entraba en estados raros donde parecía seguir conectada al WiFi, pero en la práctica quedaba medio zombie. No siempre pasaba, pero lo suficiente como para que dejara de sentirse confiable.

Entonces tocó hacer lo que había que hacer: backup de los sitios, relevamiento de la configuración, limpieza de todo lo que ya había offloadeado a otras máquinas y reinstalación desde cero.

Curiosamente, lo más difícil no fue volver a levantar **NGINX**, ni restaurar **Cloudflare Tunnel**, ni dejar andando otra vez el flujo de deploy por `rsync`. Lo más trabajoso fue algo mucho más básico: el bendito **WiFi headless**, que permitiría luego ganar acceso por SSH y realizar la configuración.

Recién cuando eso quedó arreglado, el resto empezó a resolverse super rápido: usuario nuevo, SSH, sitios restaurados, túnel activo, deploys funcionando otra vez y todo sirviendo como antes.

Al final, el resultado fue muy bueno. No tanto por haber “migrado infraestructura”, sino por haber dejado esta máquina en una base bastante más coherente con su función: Alpine Linux 64 bits, 512 MB de RAM, NGINX y túnel Cloudflare saliente.

También hubo algo interesante en ver cómo una simple experiencia en una máquina de laboratorio terminó mejorando otra que sí tenía trabajo real. A veces un sandbox no solo sirve para aprender: también sirve para despejar el camino de lo que viene después.

En este caso, al menos por ahora, parece que valió la pena.