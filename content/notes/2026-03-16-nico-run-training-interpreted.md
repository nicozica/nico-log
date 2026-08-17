---
title: "nico://run: una herramienta para leer mis entrenamientos"
date: 2026-03-16
tags: ["nico-run", "pacer", "running", "astro", "raspberry-pi", "argensonix-labs"]
summary: "Después de armar Pacer, di un paso más y lancé nico://run: un portal liviano que toma esos datos, los ordena mejor y los convierte en una lectura más clara sobre la última sesión, la semana y lo que podría venir después."
---

Después de **Pacer** apareció bastante rápido la siguiente necesidad. No solo quería pasarle mejores datos a ChatGPT, sino también tener un lugar mío para leer mejor lo que vengo haciendo. No estaba buscando una app de running, ni otro dashboard lleno de widgets, ni una copia casera de Strava. Lo que quería era algo más simple: poder ver la última sesión, entender cómo viene la semana, tener una idea de lo que sigue y leer todo eso con un poco más de claridad. Así nació **nico://run**.

### Lo que faltaba

Pacer resolvió bastante bien la parte de preparar datos. Trae actividades desde Strava, las resume, arma un brief más limpio y me deja conversar mejor con ChatGPT. Pero faltaba una capa intermedia, porque una cosa es tener el dato y otra bastante distinta es verlo acomodado con criterio. Ahí fue donde empezó a tomar forma la idea de un portal personal de running: uno que no intentara registrar todo, sino ayudarme a interpretar un poco mejor lo importante.

### Qué es nico://run

**nico://run** es, básicamente, una capa de lectura arriba de Pacer. Se puede ver en [run.nico.ar](https://run.nico.ar/), y lo que hace es tomar el snapshot que ya preparo del lado de Pacer para convertirlo en algo más legible: la última salida como bloque principal, el próximo entrenamiento como sugerencia breve, un resumen semanal y algunos links para seguir leyendo cosas interesantes de running y bienestar. La lógica, en el fondo, es bastante sencilla: **Pacer prepara, nico://run ordena y ChatGPT interpreta**. Cada pieza hace una cosa distinta, y eso por ahora viene funcionando mejor que intentar meter todo en un solo lugar.

### Cómo corre

La idea sigue siendo mantenerlo liviano. Está armado como build estático, trabaja con datos locales y evita complejidad innecesaria. También está pensado para servir cómodo incluso en hardware chico, que es parte importante de la gracia del proyecto. Me interesa bastante esa idea de poder mostrar algo útil sin depender de una infraestructura exagerada para resolver un problema bastante simple.

### Lo que ya cumple

Hoy **nico://run** ya me sirve para algo concreto. Me permite mirar la última sesión sin entrar a mil pantallas, ubicar rápido el contexto de la semana y tener una capa más amable entre el entrenamiento bruto y la decisión del día siguiente. No reemplaza a Garmin ni a Strava, y tampoco intenta hacerlo. Más bien se mete en ese hueco raro que queda después del reloj, pero antes del próximo entrenamiento.

### Lo que podría venir

Todavía hay margen para seguir puliéndolo. Me gustaría mejorar el archivo histórico, darle más personalidad a algunas vistas, armar una capa más prolija para el calendario de carreras y encontrar mejores formas de conectar el plan base con lo que realmente termino haciendo. Pero lo importante ya está: **nico://run dejó de ser una idea linda y empezó a convertirse en una herramienta propia.**