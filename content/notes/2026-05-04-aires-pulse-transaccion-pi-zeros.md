---
note_id: 2026-05-04-aires-pulse-transaccion-pi-zeros
lang: es
title: Aires Pulse y una transacción entre Pi Zeros
date: 2026-05-04
slug: aires-pulse-transaccion-pi-zeros
tags:
- raspberry-pi-zero-2w
- aires-pulse
- run-nico-ar
- nginx
- json
- home-lab
- low-tech
summary: 'Lo que empezó como una idea medio absurda —hacer que una Pi Zero genere
  señales y otra las publique— terminó convirtiéndose en Aires Pulse: un pequeño radar
  casero de Buenos Aires que además empezó a alimentar run.nico.ar con condiciones
  reales para correr.'
---

El otro día tenía una idea dando vueltas y era conectar dos mundos que ya existían: las Raspberry Pi Zero 2 W y mis pequeños sitios personales. La idea era que una Pi Zero generara información y otra la publicara. Una especie de transacción entre Pi Zeros.

La máquina que genera los datos es **Pipeta**, más laboratorio que servidor. La que publica es **Pipita**, la Zero que ya sirve [nico.com.ar](https://www.nico.com.ar "nico.com.ar"), [run.nico.ar](https://run.nico.ar "run.nico.ar") y [zero.nico.ar](https://zero.nico.ar "zero.nico.ar") con NGINX. En el medio, apenas `rsync`, JSONs estáticos y un poco de paciencia.

Así empezó **[Aires Pulse](https://aires.nico.ar "Aires Pulse")**.

Al principio era apenas una página oscura con un nombre lindo y una promesa: mostrar señales de Buenos Aires en el aire, el río y el clima. Pipeta ya tenía un experimento previo para mirar aviones cerca de Buenos Aires, así que lo más natural fue convertir esa información en un `aircraft.json` y mostrarlo en el sitio. Primero como números: cuántos aviones, países, velocidad, altitud. Después apareció el mapa.

Con Leaflet, el sitio pasó de ser una tarjeta con datos a un pequeño radar visual. Los puntos sobre Buenos Aires, el Río de la Plata, los aviones entrando y saliendo. De repente, esa idea medio de laboratorio parecía una mini consola casera de monitoreo.

La segunda capa fue el clima. Pipeta empezó a generar un `weather.json` con condiciones actuales y una recomendación de ventana para correr. No era solo mostrar temperatura: la gracia estaba en transformar esos datos en algo útil para decidir cuándo salir.

Al principio esa información vivía en [Aires Pulse](https://aires.nico.ar "Aires Pulse"). Pero después apareció una pregunta bastante obvia: si la recomendación es sobre correr, ¿por qué no usarla también en [run.nico.ar](https://run.nico.ar "run.nico.ar")?

Ahí el experimento se volvió más interesante.

[run.nico.ar](https://run.nico.ar "run.nico.ar") se genera desde **Pipa**, la Raspberry Pi 5. Es un sitio estático que se actualiza cuando publico una actividad o cuando corre su rutina diaria. Pero la información de clima venía de Pipeta y el sitio estaba alojado en Pipita. O sea: tres máquinas distintas, cada una con su rol, y los datos tenían que viajar entre ellas de forma coherente.

La solución fue separar el build estático de los datos vivos. [run.nico.ar](https://run.nico.ar "run.nico.ar") sigue viviendo en `/srv/data/www/run.nico.ar`, pero el JSON de condiciones para correr se publica por fuera, en una carpeta `live`, y NGINX lo sirve como si fuera `/data/running-conditions.json`. De esa forma, Pipa puede hacer deploys con `rsync --delete` sin pisar los datos que Pipeta actualiza cada pocos minutos.

Curiosamente, lo más trabajoso no fue la parte técnica, sino la de producto.

Había que decidir qué mostrar, cómo mostrarlo y dónde. El bloque de condiciones para correr pasó por varias formas hasta que la tarjeta empezó a responder una pregunta concreta: **¿cuál es el mejor momento para correr?** Cuando la respuesta se volvió obvia de leer, el diseño dejó de molestar.

En paralelo, [run.nico.ar](https://run.nico.ar "run.nico.ar") también ganó una separación entre el "Next run" editorial y el "Workout" práctico: uno explica qué conviene hacer y por qué, el otro lo traduce a bloques cargables a mano en Garmin Connect. No es una integración real. Es algo más simple y más honesto: una guía clara.

Al final, lo interesante no fue solo que [Aires Pulse](https://aires.nico.ar "Aires Pulse") quedara online, ni que [run.nico.ar](https://run.nico.ar "run.nico.ar") pudiera consumir datos vivos. Lo interesante fue ver cómo varias máquinas muy chicas terminaron cumpliendo roles bastante definidos.

Pipeta observa. Pipita publica. Pipa interpreta.

Todo con herramientas bastante básicas: NGINX, JSON, cron, `rsync` y un poco de Python. Me gusta esa escala. No es infraestructura grande, ni falta que hace. Es apenas un ecosistema personal donde cada pieza hace algo simple y lo hace bastante bien.

Y eso, por ahora, alcanza.
