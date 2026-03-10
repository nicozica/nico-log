---
title: "Aura: una experiencia minimalista, inmersiva y atmosférica"
date: 2026-03-07
tags: ["blurfm", "astro", "github-actions", "apache", "pwa", "radio", "automation"]
summary: "Nuevo player standalone para Blur FM, repo separado, deploy automático a Apache y base lista para crecer como app real."
---

Hoy salió a producción **Aura**, el nuevo player standalone de Blur FM, disponible en [play.blurfm.com](https://play.blurfm.com/).

La idea es dejar de pensar el player como “una parte medio colgada de la web” y empezar a tratarlo como una **experiencia propia**, más cercana a una app musical que a una página tradicional.

### Qué quedó armado

- Proyecto nuevo y separado en su propio repo
- Base en **Astro**
- Pensado como **PWA instalable**
- Deploy automático con **GitHub Actions**

### Lo bueno de haberlo separado

El sitio principal de Blur FM sigue siendo la web “institucional”, por decirlo de alguna manera.  
Aura, en cambio, arranca como una experiencia enfocada 100% en escuchar.

Eso me gusta porque ordena bastante el panorama:

- [www.blurfm.com](https://www.blurfm.com/) como sitio
- [play.blurfm.com](https://play.blurfm.com/) como player app

Más adelante se podrá integrar algo más liviano en la web principal, pero arrancar separado me parece muchísimo más sano.

### Qué tomó del proyecto viejo

Aura no salió de la nada. Toma referencias visuales del repo principal de Blur FM:

- Colores
- Logo
- Tipografía
- Look general

Todo esto sin arrastrar la estructura anterior. Era importante no mezclar arquitecturas.

### El deploy

La parte linda fue dejarlo con el mismo enfoque general que ya venía usando en Blur FM:

- Push a GitHub
- Build automático
- Deploy por **SSH + rsync**
- Debian server configurado con Apache

### MVP con mínimo esfuerzo

El proyecto nació en un mockup low fi hecho en Excalidraw y pasó rápidamente a una URL real. Se transformó bastante rápido en un producto.

No está terminadísimo ni cerca, pero ya tiene lo más importante: base propia, identidad clara y deploy resuelto.

### Próximo paso

Pulir el player con calma:

- Metadata real más robusta
- Fondo dinámico mejor resuelto
- Panel de recently played
- Ajustes finos para mobile y TV

Pero lo más importante ya sucedió: **Aura existe**.