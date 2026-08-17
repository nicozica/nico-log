---
title: "La migración que parecía difícil y terminó saliendo en una tarde"
date: 2026-07-16
tags: ["heroku", "docker", "proxmox", "nodejs", "postgresql", "cloudflare", "linux", "self-hosting"]
summary: "Dos herramientas internas, una base PostgreSQL, un worker corriendo en otra VM y varios dominios parecían anticipar una migración complicada. Al final, dividir el trabajo en pasos chicos hizo que todo saliera mucho más fácil de lo esperado."
---

En Heroku tenía dos herramientas internas montadas para resolver cosas bastante puntuales. Andaban bien, no me daban dolores de cabeza y ya formaban parte del día a día del laburo, pero el costo mensual era difícil de justificar para lo chicas que eran.

El tema es que una de las dos había crecido mucho más de lo que planeé en su momento. Ya no era una simple interfaz Node en un dyno: tenía base PostgreSQL, procesos de importación y exportación, una cola de entregas y un worker corriendo aparte, en otra VM, chequeando cada tanto si había trabajo pendiente.

La segunda era mucho más simple. Recibía un archivo de texto, separaba el contenido por locale y devolvía un ZIP con varios HTML. Sin base de datos, sin almacenamiento persistente, pero curiosamente una de las que más horas consumía en toda la cuenta.

Decidí migrar las dos a una VM Debian nueva dentro de mi Proxmox. La idea era usar Docker para que cada aplicación quedara aislada, con sus propias dependencias y su propio contenedor, todo bien ordenado. No buscaba armar una plataforma gigante, sino dejar un host prolijo donde pudieran convivir varias herramientas sin que actualizar Node o meter una dependencia nueva rompiera algo de otra app.

Antes de tocar nada confirmé lo más básico: que el código que tenía en local fuera exactamente el mismo que estaba corriendo en producción. Comparé los commits locales contra los repos remotos de Heroku en las dos apps. Suena obvio, pero te salva de migrar una versión vieja pensando que es la actual.

La primera app pedía más cuidado porque tenía datos reales en PostgreSQL. Saqué un backup lógico de la base, copié el proyecto y las variables a la VM nueva, levanté PostgreSQL 17 en Docker y restauré el dump entero. Después validé tablas, conté registros y chequeé que las migraciones de Prisma estuvieran al día antes de levantar la app.

Cuando el portal arrancó por primera vez me encontré con uno de esos problemas que al principio asustan más de lo que son. La interfaz cargaba, tomaba la contraseña, pero volvía enseguida a la pantalla de login. Resulta que la app corría en modo producción y mandaba la cookie marcada como segura, mientras yo entraba por IP local con HTTP.

Para probarla adentro de la red la dejé un rato en modo desarrollo. Después armé Cloudflare Tunnel, le puse un dominio con HTTPS y volví a producción. La misma cookie que no funcionaba sobre la IP local empezó a portarse bien sin que tocara nada de la lógica de la app.

El worker también necesitaba enterarse de dónde estaba el portal nuevo. Hasta ese momento seguía apuntando a la URL de Heroku, así que le paré el timer un rato, actualicé la variable de entorno y confirmé que se conectara bien al dominio nuevo. Cuando lo reactivé, volvió a consultar la cola con normalidad desde su VM.

La segunda herramienta fue mucho más directa. Sin base de datos, sin secretos, sin procesos externos. Copié el repo, armé la imagen Node, levanté el contenedor y probé todo el flujo desde la terminal: subir un archivo de prueba, recibir el ZIP y chequear que los HTML salieran bien.

Después pasé su dominio existente al mismo Cloudflare Tunnel. Para quien la usa no cambió nada: la URL siguió siendo la misma y la app siguió funcionando igual, solo que ahora corría en un contenedor en la VM nueva en vez de en Heroku.

Una vez que confirmé que las dos respondían bien por HTTPS y que los flujos principales andaban, borré las apps y sus recursos de Heroku. La parte que más respeto me daba terminó siendo la más mecánica: confirmar versiones, copiar, levantar en paralelo, probar y recién ahí hacer el corte.

Creo que salió fácil porque en ningún momento traté de resolver todo junto. En vez de pensarlo como una mudanza gigante de infraestructura, lo fui partiendo en checkpoints chicos donde podía verificar cada paso antes de seguir.

También ayudó que Docker dejara clarísimo qué necesitaba cada app. Una usa Node y PostgreSQL, la otra solo Node. Cloudflare Tunnel publica las dos sin abrir puertos en el router, y la VM quedó como un host general para herramientas chicas, no como una instalación artesanal imposible de mantener.

Lo que arrancó como una forma de bajar un gasto terminó ordenando bastante la arquitectura. Las apps siguen separadas, los dominios no cambiaron, el worker sigue haciendo lo suyo y la infraestructura quedó lista para sumar otras herramientas más adelante.

Lo más curioso es que durante bastante tiempo me imaginé esta migración como algo complicado y delicado. Cuando finalmente me senté a hacerla, las dos apps ya estaban funcionando en la VM nueva la misma tarde.