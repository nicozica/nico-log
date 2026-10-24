---
title: Mi balanza china ahora habla con Garmin
date: '2026-10-15'
tags:
- homelab
- raspberry-pi
- garmin
- bluetooth
- running
summary: Me cansé de la publicidad de OKOK y terminé conectando una balanza china
  a Garmin Connect usando una Raspberry Pi 5. Otro pequeño experimento de homelab
  que salió mejor de lo esperado.
---

Hace un tiempo compré una de esas balanzas inteligentes chinas que funcionan con la aplicación OKOK. La balanza anda bárbaro, pero la app es insoportable. Cada vez que quería pesarme me encontraba con una publicidad de casi 20 segundos. Una locura para algo que debería llevar cinco segundos.

Primero descubrí [OpenScale](https://github.com/oliexdev/openScale), una alternativa open source para Android que reconoce la balanza sin problemas. Pero me quedó dando vueltas otra idea: ¿y si pudiera mandar el peso directamente a Garmin Connect, sin depender de ninguna aplicación?

Ahí apareció [BLE Scale Sync](https://github.com/KristianP26/ble-scale-sync), un proyecto que permite leer balanzas Bluetooth y sincronizar sus datos con distintos servicios, incluido Garmin.

Como ya tengo una Raspberry Pi 5 funcionando las 24 horas, decidí aprovecharla. Instalé el proyecto, configuré la balanza, la autenticación de Garmin y un servicio systemd para dejarlo funcionando automáticamente.

Obviamente no salió todo a la primera. Hubo un rato de pelearse con Bluetooth, algunos errores bastante crípticos y varias pesadas de prueba. Pero finalmente funcionó.

Ahora simplemente me subo a la balanza y, un par de segundos después de que la Raspberry Pi recibe la medición, el peso aparece en Garmin Connect. También se guarda un historial local que más adelante podría integrar con mi pequeño proyecto de running.

Incluso se sincronizan las métricas de composición corporal, aunque en este caso son estimaciones del software y no mediciones reales de la balanza.

No necesitaba otra balanza, ni mucho menos una Garmin Index. Solo necesitaba que la que ya tenía hiciera lo que yo quería.

Una pequeña victoria del homelab. 😁
