---
note_id: 2026-08-19-fallback-4g-a-lo-croto
lang: es
title: Internet redundante con bajo presupuesto
date: '2026-08-19'
slug: internet-redundante-bajo-presupuesto
tags:
- linux
- proxmox
- 4g
- homelab
- tailscale
- cloudflare
---

El otro día me puse a pensar qué pasaba con mi infraestructura casera si se cortaba la fibra. Si el ISP de casa desaparecía durante unas horas, quería seguir pudiendo entrar remotamente a los servidores, mantener algunos túneles de Cloudflare funcionando y tener una salida de emergencia.

Así nació KernelPanic-Rescue, un fallback 4G muy artesanal, armado con hardware que ya tenía dando vueltas y un pequeño router LTE que parece un pendrive USB.

La regla principal era que la fibra siguiera siendo siempre la conexión normal. Los servidores hacen comprobaciones independientes contra Internet y, si la mayoría falla, esperan otros 15 segundos antes de tomar ninguna decisión.

Si Internet vuelve durante esa ventana, no pasa nada.

Si sigue caído, levantan la conexión de emergencia, cambian las rutas necesarias y algunos servicios empiezan a salir por 4G. Cuando la fibra se recupera de forma estable, todo vuelve automáticamente a su estado original.

Los 15 segundos terminaron siendo más importantes de lo que parecía. Una madrugada el ISP renovó la IP pública y produjo un pequeño corte. Uno de los servidores lo detectó, esperó la ventana de confirmación y registró:

`Fiber ISP health-check failed; confirming in 15 seconds.`
`Fiber ISP recovered during confirmation window.`

Nunca llegó a activar el 4G. Era justo lo que quería evitar: que cualquier pestañeo del proveedor provocara una conmutación completa.

## El zoológico de placas Wi-Fi

La parte menos elegante fue encontrar cómo conectar cada máquina al router de emergencia.

Probé varias placas USB que tenía guardadas: una TP-Link diminuta con chipset Realtek, una vieja D-Link con Ralink RT3070 y el Wi-Fi integrado de una Raspberry Pi.

La teoría decía que cualquiera debía alcanzar. La práctica fue bastante distinta. La TP-Link tenía una señal aparentemente razonable, pero podía tardar segundos enteros en responder un ping. La vieja Ralink, en cambio, terminó funcionando mucho mejor. Después de probar distintos puertos USB, posiciones y distancias, quedó dedicada exclusivamente a Bernarda, uno de mis hosts Proxmox.

La TP-Link sobrante terminó pasada por USB a una VM con Kali Linux, donde encontró una segunda vida bastante más apropiada.

El router LTE también resultó tener una algo interesante: conectado directamente por USB al servidor aparece en Linux como una placa Ethernet normal. Eso permitió que uno de los hosts evitara completamente el Wi-Fi y tuviera su propia conexión cableada al router 4G. No es precisamente una arquitectura de datacenter, pero funciona.

## Lo que quedó


El sistema sigue siendo chico. No quiero pasar streaming, ni servicios pesados por el 4G. Si se cae la fibra, el objetivo es conservar administración remota, Tailscale, Cloudflare y algunas cosas importantes hasta que vuelva la conexión normal.

El experimento terminó siendo mucho más entretenido de lo que esperaba. Empezó como “poner una antenita Wi-Fi por si se corta Internet” y terminó involucrando policy routing, namespaces, systemd, dongles reciclados y bastante tiempo moviendo adaptadores USB de un puerto a otro.

Cuando era chico jugaba con antenas de alambre en la terraza de casa tratando de pescar señales. Unas décadas después sigo haciendo básicamente lo mismo. Sólo que ahora hay Proxmox en el medio.
