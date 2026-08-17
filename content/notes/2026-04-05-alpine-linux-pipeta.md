---
title: "Pipeta, Alpine y el encanto de volver a las bases"
date: 2026-04-05
tags: ["alpine-linux", "raspberry-pi-zero-2w", "python", "sqlite", "rss", "weather", "argensonix-labs"]
summary: "Estos días empecé a usar Pipeta, una Raspberry Pi Zero 2 W pensada pura y exclusivamente como playground de experimentación. La idea fue aprovecharla para aprender sin presión, con scripts chicos, clima, RSS, SQLite y esa clase de pruebas mínimas que no cambian el mundo, pero enseñan bastante."
---

Estos días me encontré con una situación interesante: tener una Raspberry Pi Zero 2 W prendida en Buenos Aires, corriendo Alpine Linux, mientras yo estoy lejos de casa y sin necesitar nada urgente de esa máquina. En otras palabras, el contexto ideal para empezar a probar cosas sin culpa.

La máquina se llama **Pipeta** y el nombre le queda bien, porque la idea es usarla justamente como eso: un sandbox puro para experimentar, aprender y equivocarme sin convertir cada intento en un servicio, una obligación o una nueva pieza de infraestructura para mantener.

<figure class="note-photo">
  <img src="/assets/img/notes/pipeta-alpine-linux-20260407.webp" alt="Pipeta, una Raspberry Pi Zero 2 W encendida sobre una superficie oscura" loading="lazy" />
  <figcaption>Pipeta, lista para seguir haciendo pruebas chicas, manuales y bastante tranquilas.</figcaption>
</figure>

### La gracia de no hacer algo importante

Muchas veces uno aprende tecnología queriendo resolver algo grande demasiado rápido. Montar un servidor, exponer un subdominio, automatizar medio planeta o transformar un script en un sistema antes de tiempo. Esta vez quise hacer lo contrario.

La consigna fue bastante simple: nada de producción, nada de disponibilidad y nada de dejar cosas corriendo porque sí. Solo cosas chicas, manuales, locales y lo suficientemente inofensivas como para poder jugar sin presión.

### Las primeras pruebas

Empecé por dos scripts muy simples en Python. Uno para comparar el clima entre ciudades y otro para leer titulares desde feeds RSS. No eran herramientas especialmente sofisticadas, pero justamente ahí estuvo la gracia.

Lo interesante fue entender mejor qué hace cada capa: Python como lenguaje, `requests` para traer datos, `feedparser` para leer RSS, una API para el clima y después un poco de lógica propia para ordenar todo y mostrarlo de una forma más legible. No había ninguna magia rara detrás, solo datos, reglas simples y algo de criterio para presentarlos.

Dicho así parece bastante obvio, pero verlo funcionar en una terminal remota, en una maquinita tan chica, tuvo bastante encanto.

### De script a programita

Después vino el siguiente paso, que fue juntar esas piezas en una especie de mini laboratorio interactivo. Así apareció **Pipeta Lab**, un script con menú en terminal que permite comparar ciudades, leer titulares y combinar ambas cosas en una vista simple tipo observatorio.

Todo sigue siendo chico, manual y bastante liviano. Y eso es justamente lo que más me interesaba: no armar una app, ni un dashboard, ni una plataforma, sino un programita lo bastante vivo como para ayudarme a entender mejor cómo encajan las cosas.

### Cuando apareció SQLite

El salto más interesante por ahora fue sumar **SQLite**. No por una necesidad urgente, sino porque me pareció una buena forma de tocar una base de datos sin meter demasiada complejidad.

Hasta ese momento, los datos aparecían en pantalla y desaparecían ahí mismo. Con SQLite apareció algo distinto: persistencia. El programa ya no solo consultaba y mostraba, sino que además podía guardar una corrida y volver a leerla después. Ahí empezó a hacerse más clara una estructura que siempre está, aunque a veces uno no la vea tanto: entrada, procesamiento, persistencia y salida.

Dicho de otra manera, el script dejó de ser solo una consulta en vivo y empezó a parecerse un poco más a un sistema, aunque siguiera siendo un experimento muy chico.

### Lo que más me gustó

Creo que lo mejor de esta pequeña aventura no fue Alpine, ni Python, ni SQLite por separado. Lo mejor fue volver a algo bastante básico y bastante sano: aprender sin la presión de publicar, automatizar o convertir todo en “infraestructura” enseguida.

Abrir una terminal, escribir algo, romper una indentación, pelearse con una API caprichosa, entender por qué una ciudad no aparece y guardar tres filas en una base de datos puede sonar mínimo, pero justamente en esa escala es donde se vuelve más fácil entender qué está pasando.

### Lo que puede venir

Por ahora quiero mantener a Pipeta en ese lugar: sandbox puro, laboratorio y caja de pruebas. Capaz más adelante alguna de estas cositas migra a otra máquina o termina colgada en la web, pero prefiero que eso llegue después, si tiene sentido, y no como punto de partida.

Está bueno recordar que no todo proyecto tiene que nacer como infraestructura. A veces alcanza con una idea mínima, una terminal y un rato libre para aprender un poco más.
