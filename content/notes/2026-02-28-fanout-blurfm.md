---
title: "Fanout de Blur FM: origen en Argentina, relays en Europa (sin perder metadata)"
date: 2026-02-28
tags: ["blurfm", "icecast", "streaming", "infra"]
summary: "Cómo armé un fanout simple con Icecast para servir Blur FM en Europa con menor latencia y manteniendo el now playing."
---

Con intención de optimizar el funcionamiento de Blur FM, la idea fue: **cuatro calidades desde SAM** (320, 128, 64 y 32 kbps), **Icecast en Argentina como base**, **un relay en Europa** para balancear la demanda, y **Cloudflare** para que las URLs públicas deriven al endpoint más conveniente (AR o EU).

En la práctica esto termina siendo un *fanout*: el Icecast “madre” publica los streams, y uno (o más) Icecast en Europa **se enganchan como relay** y vuelven a servir esas mismas calidades localmente.

### Qué problema resuelve

- **Menos latencia** para oyentes en Europa (arranca más rápido y se corta menos).
- **Más estabilidad**: si el tráfico europeo cae al relay, el origen en Argentina respira.
- **Consistencia**: el now playing sale de un solo lugar y se ve igual en ambos lados.

### La parte mágica: el “RDS” del streaming

Lo mejor es que no solo viaja el audio: también viaja la **metadata** (título, artista, etc.).  
Entonces el relay europeo termina mostrando el mismo “Now Playing” que el origen.

Esto sirve porque:
- El web player muestra el tema actual sin inventar nada.
- Muchas apps leen esa info directo del stream.
- Cloudflare puede redirigir al usuario al endpoint más conveniente (AR o EU).
- Todo queda consistente y no hace falta mantener sistemas paralelos.

### Resultado

Los streams se replican en Europa, se reparte la carga y la experiencia mejora, manteniendo todo consistente. Y encima quedan URLs públicas listas para crecer a futuro (routing más fino, stats separadas, lo que pinte) sin convertir la infra en un Frankenstein.