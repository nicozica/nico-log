---
title: Un comando para hacer backup de todo el homelab
date: '2026-09-18'
tags:
- homelab
- backups
- linux
- automation
summary: Cómo convertí varios procedimientos manuales de backup en una única operación
  coordinada, validada localmente y verificada también en el almacenamiento offsite.
slug: un-comando-para-hacer-backup-de-todo-el-homelab
---

Durante mucho tiempo, hacer un backup completo de mi homelab significaba seguir varios procedimientos por separado.

Hay hosts, máquinas virtuales, contenedores y algunos servicios que necesitan pasos particulares. En ciertos casos hay que sincronizar primero una instancia secundaria, en otros detener temporalmente un servicio, generar el backup, comprobarlo y después subirlo al almacenamiento offsite.

Todo funcionaba, pero había un problema muy evidente: demasiado del proceso dependía de recordar qué había que hacer, en qué orden y qué estado tenía cada cosa antes de empezar.

La idea terminó resultando que eso sea muy sencillo: convertir todo eso en una única comando.

```bash
datacenter-backup.sh run
```

La operación inicia un servicio de systemd que se encarga de coordinar el proceso completo. De esta forma, el backup no depende de que mi sesión SSH siga abierta y puede continuar aunque cierre la terminal.

## Distintos sistemas, un mismo proceso

No todos los backups se pueden tratar de la misma manera.

Algunas máquinas pueden copiarse mientras están funcionando. Otras necesitan detenerse durante unos minutos. También hay servicios en los que primero conviene sincronizar una instancia secundaria antes de generar la copia.

En lugar de intentar imponer un único método para todo, el orquestador delega cada parte en pequeños scripts especializados.

A grandes rasgos, el proceso queda así:

```text
orchestrator
    |
    +-- host configuration
    +-- remote Linux host
    +-- virtual machines
    +-- containers
    |
    +-- local validation
    |
    +-- offsite upload
    |
    +-- remote verification
```

El script principal se ocupa de coordinar esas etapas y detener el proceso si alguna falla.

## Verificar antes y después

Una de las cosas que quería evitar era considerar que un backup estaba terminado simplemente porque un comando había finalizado sin errores.

Los archivos se validan localmente después de generarse. Se comprueba que los archivos comprimidos sean legibles y se calculan checksums para las copias correspondientes.

Después viene la segunda parte: el almacenamiento offsite.

Los backups se suben a Dropbox mediante un contenedor dedicado exclusivamente a esa tarea. Una vez terminada cada transferencia, el archivo local y el remoto se vuelven a comparar usando su tamaño y el content hash de Dropbox.

Por lo tanto, el proceso no termina en:

```text
upload successful
```

sino en algo más parecido a:

```text
backup created
backup validated locally
backup uploaded
remote copy verified
```

## Volver al estado inicial

También quería que ejecutar un backup no modificara permanentemente el estado del homelab.

Antes de actuar sobre una máquina o servicio, el proceso registra si estaba encendido o apagado.

Si necesita arrancar temporalmente algo para realizar una copia, después vuelve a detenerlo. Si necesita parar una máquina que estaba funcionando, al terminar vuelve a iniciarla.

Esto también se aplica a algunos servicios auxiliares que sólo son necesarios durante una parte del proceso.

El resultado es que el backup puede realizar cambios temporales en la infraestructura, pero al finalizar todo debería quedar en el mismo estado operativo en el que estaba antes de comenzar.

## Un manifest por ejecución

Cada ejecución genera también un manifest con los archivos que forman parte de esa generación.

Eso sirve para tener una referencia concreta de qué se produjo y qué se envió al almacenamiento remoto durante una ejecución determinada.

No reemplaza a los checksums ni a la verificación de los archivos, pero ayuda a tratar cada ejecución como una unidad completa en lugar de como una colección de archivos sin relación entre sí.

## La primera ejecución completa

La primera prueba real del proceso completo tardó algo más de cinco horas.

Durante ese tiempo se generaron las distintas copias locales, se validaron, se enviaron al almacenamiento offsite y se verificaron nuevamente del otro lado.

Al finalizar, el orquestador reportó éxito y las máquinas, contenedores y servicios involucrados habían vuelto al estado esperado.

La diferencia más importante no es que ahora los backups sean más rápidos. Siguen llevando varias horas y moviendo una cantidad considerable de datos.

La diferencia es que ahora el procedimiento está definido, es reproducible y tiene un punto claro de inicio y de finalización.

Antes tenía varios procedimientos de backup.

Ahora tengo uno.
