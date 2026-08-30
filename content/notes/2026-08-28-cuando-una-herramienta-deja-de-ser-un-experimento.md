---
title: Cuando una herramienta deja de ser un experimento
date: '2026-08-28'
tags:
- automation
- drupal
- devops
- ai
summary: Cómo una automatización nacida para programar la visibilidad de un banner
  terminó convirtiéndose en un pequeño sistema de campañas capaz de coordinar contenido,
  mercados, horarios y contingencias.
---

Hace unas semanas apareció un problema concreto en el trabajo: había que publicar y retirar un banner en decenas de mercados, en un horario determinado, dentro de Drupal.
Hacerlo manualmente era posible. También era exactamente el tipo de tarea que invita a preguntarse: **¿por qué estamos haciendo esto a mano?** Así nació el Banner Scheduler.
La primera versión tenía un objetivo bastante acotado: programar cambios de visibilidad. Elegir mercados, definir una fecha y dejar que la herramienta hiciera el trabajo cuando correspondiera. Pero rápidamente apareció un problema más interesante: la visibilidad era solamente una parte del asunto.
¿Qué pasa cuando además cambia el contenido del banner? ¿Qué hacemos con distintas traducciones? ¿Cómo programamos varios cambios durante una campaña? ¿Cómo evitamos que Drupal termine siendo nuevamente el lugar donde vive el contenido? ¿Qué ocurre si el sitio está temporalmente en mantenimiento cuando llega el momento de ejecutar un cambio?

Ahí el proyecto empezó a transformarse. Hoy el Scheduler trabaja junto a **Atlas**, otra herramienta interna que usamos como fuente de verdad para contenido y traducciones. La separación quedó bastante clara:

* Atlas sabe **qué contenido debería existir**.
* El Scheduler sabe **cuándo tiene que cambiar y cuándo debe estar visible**.
* Drupal queda como destino final, no como lugar desde donde administrar todo el proceso.

Una campaña puede cargarse a partir de una planilla, validar sus mercados y horarios, preparar los distintos cambios de contenido y generar los jobs que se ejecutarán posteriormente. También hay una pequeña secuencia que me pareció genial: **check, apply, arm**. Primero comprobar que lo que queremos hacer tiene sentido. Después crear la campaña. Y recién entonces dejar armados los jobs que podrán modificar producción.

Los horarios de los distintos mercados se normalizan, las acciones quedan registradas y el worker se ocupa de ejecutar lo programado. Si determinadas condiciones temporales impiden realizar el cambio, existen reintentos en lugar de asumir inmediatamente que todo salió mal. Todo esto terminó acompañado además por una interfaz donde se pueden ver campañas, próximos cambios, actividad reciente y el estado de cada operación.

Esta semana ocurrió el pequeño milestone que justificaba escribir todo esto: **armamos la primera campaña real.**
Ya no era un test, un dry run ni datos preparados especialmente para desarrollar la herramienta. Había contenido real, horarios reales y cambios que efectivamente tenían que ocurrir.

Y funcionó. Quizás lo que más me gusta de este proyecto es que no nació de una especificación enorme ni de la idea de crear una “plataforma”.
Nació de mirar una tarea bastante tediosa y pensar: **esto debería poder hacerse mejor.** El resto fue apareciendo pregunta por pregunta. Y probablemente todavía queden unas cuantas.
