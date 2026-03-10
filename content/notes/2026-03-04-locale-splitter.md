---
title: "Splitter tool hosteada en Heroku en 30 min"
date: 2026-03-04
tags: ["ipsos", "tools", "i18n", "locales", "automation", "heroku"]
summary: "Una mini web app que corta el TXT master usando marcadores por locale y devuelve un ZIP con los HTML listos, con naming consistente."
---

En dos iteraciones (media hora como mucho) armé **locale-splitter**: una mini herramienta web para recortar el TXT master de traducciones y bajarlo como **ZIP**, ya **corriendo en Heroku**.

El TXT trae HTML concatenado y el splitter corta cuando encuentra separadores tipo: `|- (EN-PH) faq-contact-us`. Sin ese formato exacto, no hay corte ni renombre.

### Qué hace el MVP

- Subís un `.txt`
- Detecta marcadores `|- (LOCALE) slug`
- Corta el contenido entre marcadores (sin incluir la línea del marcador)
- Genera un ZIP con todos los HTML en una sola carpeta, con naming:
  - `(EN-US) faq-common-concerns.html`

### Lo loco

Codex no solo generó la app (Node/Express), también la empujó a GitHub y la publicó en Heroku. Se embaló creando un repo nuevo al principio aunque yo ya tenía uno definido, pero con un redeploy apuntando al repo correcto quedó listo.

### Próximo paso

Sumar un `report.txt` en caso de que hubiera warnings detectados (por ejemplo marcadores sin contenido).