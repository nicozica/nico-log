---
title: "Una segunda vida para una PC vieja con Proxmox"
date: 2026-05-27
tags: ["proxmox", "home-lab", "linux", "virtualization", "fedora", "tailscale", "kubernetes", "low-tech"]
summary: "Lo que empezó como una PC vieja juntando polvo terminó convirtiéndose en una excusa perfecta para armar un laboratorio Proxmox: probar distros, entender mejor virtualización, jugar con discos viejos y separar producción de experimentos."
---

Tenía una PC vieja juntando polvo en una caja, en un rincón de mi habitación. Durante años fue mi máquina principal: un AMD FX 8300, una mother ASUS, 16 GB de RAM, una placa de video Gigabyte de 2 GB y una fuente bastante decente. En su momento corrió Windows 10, la usé fuerte durante años y siempre respondió bien.

Después armé mi PC actual, instalé Fedora, me acostumbré a trabajar todos los días en Linux y la máquina vieja quedó afuera del mapa. No estaba rota, no estaba inútil, simplemente había perdido su lugar.

El otro día la saqué de la caja, la limpié, le cambié la pasta térmica, la prendí y arrancó perfecto. Tomó memoria, dio video y quedó esperando lo único que todavía no tenía: un disco para bootear.

Ahí apareció la idea de darle una segunda vida, pero no como PC principal ni como reemplazo de ningún servidor actual. La idea es mucho más simple: convertirla en un laboratorio Proxmox para prender cuando tenga ganas de probar algo, romper una VM, instalar una distro nueva o practicar infraestructura sin tocar nada importante.

Esa separación me gusta. Mi servidor de producción tiene que ser aburrido y estable. No quiero usarlo para experimentos raros ni para probar cosas que pueden romperse. Para eso tiene mucho más sentido una máquina aparte, vieja pero todavía capaz, donde equivocarse no sea un problema.

El hardware no es moderno, pero para laboratorio tiene bastante gracia. Un SSD SATA de 960 GB para Proxmox y las VMs principales, un disco WD Blue de 1 TB para backups de prueba o almacenamiento secundario, y un disco mecánico viejo de laptop para hacer experimentos sin miedo. Incluso tiene grabadora de DVD, algo completamente innecesario en 2026, pero justamente por eso bastante simpático para un laboratorio casero.

El único punto menos prolijo es la red. En esa habitación no tengo Ethernet directo, así que la solución va a ser usar un repetidor WiFi con puerto Gigabit Ethernet. El repetidor se conecta al WiFi de casa y la PC lo ve como una conexión cableada normal. Para Proxmox eso es bastante más limpio que depender de una placa WiFi directa dentro del host.

También me interesa probar Wake on LAN. La máquina ya había funcionado antes con magic packet, así que la idea es poder encenderla remotamente desde una Raspberry Pi que queda siempre prendida con Tailscale. En la práctica sería algo bastante simple: entro desde afuera a la red de casa, mando el magic packet, la PC prende, entro al panel de Proxmox y levanto la VM que necesite.

Lo que más me entusiasma no es la potencia bruta, sino el tipo de cosas que puedo aprender ahí. Quiero probar Fedora Server, openSUSE, Arch Linux, Omarchy, Debian limpio y algunas distros que quedaron afuera de otras máquinas más chicas. También me gustaría jugar con Proxmox Backup Server, practicar snapshots, hacer restores reales y entender mejor cómo ordenar templates de VMs.

Otra idea que me interesa es probar K3s, una versión liviana de Kubernetes. No porque quiera convertir mi casa en un datacenter, sino porque como diseñador y UX engineer me sirve entender mejor qué pasa después de que una interfaz deja de ser un diseño o un prototipo.

Hay un camino que muchas veces queda medio invisible desde diseño: frontend, build, container, deploy, service, ingress, logs, rollback. Poder recorrer ese flujo en una escala chica, con una app simple o un dashboard interno, me parece una forma muy concreta de aprender. No necesito una infraestructura enorme. Necesito un lugar donde pueda probar, mirar qué pasa y volver atrás sin miedo.

La máquina también puede servir para ordenar mejor mi ecosistema casero. Hoy tengo una PC principal para trabajar, un servidor que sostiene servicios reales, una Raspberry Pi para staging y acceso remoto, otra para sitios estáticos livianos, y algunas máquinas más chicas para pruebas. Lo que faltaba era un lugar claro para romper cosas sin mezclarlo con producción.

Ese sería el rol de esta PC: laboratorio bajo demanda. Después vendrán las distros, Kubernetes, los discos viejos, los templates y todas las demás ideas.

Me gusta porque no estoy comprando una PC nueva ni complicando algo que ya funciona. Estoy recuperando hardware que ya tenía y dándole un rol mucho más claro que antes. La PC vieja no vuelve como máquina principal, sino como un laboratorio linuxero todo terreno.