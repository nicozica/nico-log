---
title: "Pacer: de las capturas eternas a un brief limpio para Coachat"
date: 2026-03-09
tags: ["pacer", "strava", "running", "raspberry-pi", "nodejs", "automation", "argensonix-labs"]
summary: "Armé Pacer, una app local que trae mis actividades desde Strava, resume la carga reciente y me deja generar un brief simple para pasarle a ChatGPT sin depender de capturas ni textos larguísimos."
---

Hoy nació **Pacer**, una mini app local pensada para algo bastante concreto: **dejar de pasarle al ChatGPT capturas y empezar a pasarle contexto útil**.

La idea salió de una necesidad muy simple. Cuando quiero revisar cómo vengo entrenando y decidir qué hacer al día siguiente, no necesito nueve screenshots, ni una novela explicando todo, ni depender de recordar de memoria qué hice hace tres días.

Necesito esto:

- qué hice últimamente
- cuánto corrí
- si metí bici
- si hice fuerza
- cómo me siento hoy

Y listo.

### El problema de fondo

Durante bastante tiempo el flujo fue más artesanal que otra cosa.

Mirar Garmin.  
Mirar Strava.  
Sacar capturas.  
Mandarlas.  
Explicar sensaciones.  
Volver a resumir a mano.

Funcionaba, sí. Pero tenía demasiada fricción.

Lo interesante fue que al intentar automatizarlo aparecieron varias verdades bastante rápido:

- **Strava** sirve mucho mejor como fuente de datos que como web para scrapear
- **Garmin** sigue siendo mejor como reloj y ecosistema de entrenamiento que como plataforma abierta para integrar cosas personales
- **Playwright** está bueno, pero no tenía sentido hacerlo protagonista de algo que Strava ya resolvía mejor con API

### Qué terminó siendo Pacer

Pacer quedó como una herramienta local, simple y bastante más sensata:

- trae mis últimas actividades desde **Strava API**
- guarda todo en JSON
- levanta una mini web local
- resume automáticamente la carga reciente
- me deja completar solo unos pocos campos humanos
- genera un texto listo para copiar o descargar

Ese texto después se lo paso a ChatGPT y el ida y vuelta queda mucho más limpio.

### Qué muestra la app

Por ahora Pacer ya resume varias cosas útiles:

- última actividad
- último run
- último ride
- resumen de los últimos 7 días
- volumen de running
- volumen de bici
- sesiones de fuerza y workout

Y además tiene un bloque manual bien corto para completar:

- sensación general
- piernas
- molestias
- sueño
- tiempo disponible mañana
- objetivo
- nota extra

Eso solo ya baja muchísimo la fricción.

### Lo más importante

El punto no era hacer una app “fitness” más.

El punto era armar **un puente entre mis datos y una conversación útil**.

No me interesa llenar dashboards por llenarlos.  
Me interesa que el sistema me ayude a responder algo concreto:

**qué conviene hacer mañana.**

En ese sentido, Pacer ya cumple.

### Dónde corre

Por ahora quedó corriendo en una **Raspberry Pi 5**, dentro de mi red local, con una mini web accesible desde otros dispositivos.

La idea de llevarlo más adelante a una máquina todavía más chica sigue viva, pero primero quería validarlo sin agregar limitaciones innecesarias.

### Lo que salió bien

Varias cosas terminaron acomodándose mejor de lo esperado:

- el fetch a Strava funciona
- el JSON quedó útil
- la web local nació rápido
- el copy to clipboard / download txt tienen mucho más sentido del que parecía
- ya no dependo de un caos de screenshots

También quedó repo nuevo en GitHub, con un nombre bastante lógico para la idea: **pacer**.

### Lo que quedó afuera

Hubo una tentación fuerte de meter browser automation por todos lados, sobre todo para Garmin.

Pero por ahora quedó afuera del corazón del proyecto.

Y estuvo bien.

A veces el mejor avance no es sumar más piezas, sino **recortar el alcance a tiempo**.

### Próximo paso

Pulirlo sin volverlo barroco:

- brief más compacto
- persistencia local de los campos manuales
- favicon mejor resuelto
- service prolijo en la Raspberry
- quizá acceso privado por Tailscale

Pero lo importante ya pasó.

**Pacer dejó de ser una idea y empezó a servir.**