---
title: Construyendo mi propio Running Coach
date: '2026-10-22'
tags:
- running
- garmin
- garmin-connect
- smartwatch
- automatización
summary: Después de varios meses trabajando en Pacer, conseguí que los entrenamientos
  que planifico conversando con ChatGPT lleguen directamente a mi Garmin. El camino
  tuvo bastantes pruebas, problemas con los ritmos y algunas sorpresas.
slug: construyendo-mi-propio-running-coach
---

En marzo escribí por acá sobre [Pacer](https://www.nico.com.ar/es/pacer-strava-brief-builder/), una pequeña herramienta que había armado para dejar de pasarle capturas de pantalla a ChatGPT cada vez que quería revisar mis entrenamientos. Poco después apareció [nico://run](https://www.nico.com.ar/es/nico-run-training-interpreted/), un sitio para analizar mis sesiones de running, algunos datos y las recomendaciones a futuro.

En ese momento el sistema terminaba ahí. Pacer preparaba la información, yo conversaba sobre cómo venía entrenando y, cuando tenía una propuesta para la próxima salida, me tocaba cargarla manualmente en Garmin Connect. Funcionaba, pero había una parte muy repetitiva que seguía dependiendo de mí.

El 20 de septiembre terminé mi segunda Maratón de Buenos Aires. Después de varios meses siguiendo un plan bastante estructurado, quería continuar entrenando con cierta organización, aunque sin la exigencia de preparar otra maratón inmediatamente. Y, de paso, aprovechar para mejorar estas herramientas que ya venía usando.

La idea era la siguiente: después de correr, Pacer reúne los datos de la actividad y genera un resumen que puedo compartir en ChatGPT. Incluye ritmos, frecuencia cardíaca, vueltas registradas por Garmin, información de recuperación y algunas observaciones que completo yo mismo.

También empecé a incorporar información de bienestar que proporciona [Intervals.icu](https://www.intervals.icu/): horas y calidad del sueño, frecuencia cardíaca en reposo, carga de entrenamiento y evolución del peso. Incluso terminé metiendo en el mix una balanza china que envía los valores a Garmin Connect automáticamente por Bluetooth, sin tener que abrir su aplicación llena de publicidad cada vez que me peso.

Todo eso aporta contexto, aunque los números por sí solos no siempre cuentan demasiado. No es lo mismo ver que corrí siete kilómetros a determinado ritmo que explicar, por ejemplo, que las piernas estaban bien pero me resultó insoportablemente aburrido correr tan despacio.

Con esa información puedo conversar sobre la sesión, discutir si cumplí el objetivo y decidir qué conviene hacer después. El análisis no siempre tiene que coincidir con lo que dice Garmin. De hecho, parte de la gracia es poder cuestionar las recomendaciones y ajustar el entrenamiento según cómo me sentí realmente.

Cuando todo cierra, ChatGPT devuelve un JSON con dos partes: el análisis de la actividad que terminé y la propuesta del próximo entrenamiento. Pacer interpreta ese archivo, valida su contenido y me muestra una vista previa antes de aprobarlo.

Hasta ahí, todo bien. El problema apareció cuando me propuse buscar la forma de que esos entrenamientos llegaran al reloj automáticamente.

Garmin permite crear sesiones con precalentamientos, bloques de carrera, objetivos de ritmo, recuperaciones y repeticiones. Son muy útiles cuando uno sale a correr y quiere que el reloj vaya indicando qué hacer, en lugar de estar mirando constantemente cuánto tiempo pasó o calculando cuándo empieza la siguiente serie.

Por supuesto, no estoy inventando nada nuevo. Existe Runna, que ofrece planes de entrenamiento y los sincroniza con Garmin. También están los *Daily Suggested Workouts* de algunos relojes Garmin, una función que mi Venu 2 Plus no tiene.

Pero lo que me interesaba iba un poco más allá de recibir una sesión recomendada. Quería poder conversar sobre mis entrenamientos, incorporar mis propias sensaciones, discutir una propuesta y terminar con algo ejecutable en el reloj. Y, sobre todo, aprovechar lo que ya había construido en lugar de sumar otra aplicación a la lista.

Para resolverlo incorporé Intervals.icu como intermediario. Las actividades completadas llegan desde Garmin, pasan por Intervals.icu y terminan en Pacer. Para los entrenamientos planificados, el recorrido funciona al revés: Pacer genera la estructura, Intervals.icu la recibe y Garmin la sincroniza con el reloj.

En teoría parecía sencillo, pero en la práctica, no tanto.

Los primeros entrenamientos llegaban al reloj con las duraciones correctas, pero todos los bloques figuraban como *Run*, incluso el precalentamiento y el enfriamiento. Los objetivos de ritmo aparecían escritos en las descripciones, aunque no estaba claro si el reloj los interpretaba como objetivos reales o como simples notas.

Probamos varias formas de generar la estructura. Revisamos cómo Intervals.icu interpretaba los pasos, qué información exportaba y qué terminaba mostrando Garmin. Hubo bastantes pruebas y algunos momentos en los que pensé que iba a tener que seguir configurando todo manualmente.

Una de las piezas que faltaba era configurar correctamente el *Threshold Pace* en Intervals.icu. Después de revisar algunas carreras recientes, fijamos un valor estimado de 5:10 min/km. Con eso empezaron a aparecer los objetivos de ritmo en Garmin.

Después hubo que ajustar el adaptador de Pacer para que enviara los tipos de intensidad adecuados. No alcanzaba con escribir "Warm up" en una descripción: había que indicarle al sistema que ese paso era realmente un precalentamiento, que el siguiente era carrera activa y que el último correspondía al enfriamiento.

Y todavía quedaban las repeticiones.

Queríamos poder definir algo como dos aceleraciones de 20 segundos, con 1 minuto y 40 segundos de recuperación después de cada una, y que Garmin entendiera el conjunto como un bloque repetido. No dos instrucciones sueltas, ni una descripción para leer mientras corro.

El 22 de octubre finalmente pude comprobarlo con un entrenamiento real. Salí con una sesión progresiva de 45 minutos, dos aceleraciones cortas y sus respectivas recuperaciones. El Venu mostró los bloques correctamente, con sus objetivos de ritmo y las repeticiones agrupadas como *2 Sets*. Durante la sesión, los cambios de paso funcionaron como estaban programados.

Era exactamente lo que había estado intentando conseguir.

<figure class="note-photo">
  <img src="/assets/img/notes/garmin-venu-2-plus-training-calendar-b1cf1203a3.webp" alt="Garmin Venu 2 Plus Workout" width="1519" height="855" loading="lazy" />
  <figcaption>Entrenamiento planificado automáticamente por Pacer, visto en el reloj.</figcaption>
</figure>

Además, toda esa información quedó integrada con el resto del sistema. Pacer conserva los entrenamientos planificados, sus estados de sincronización y los análisis de las actividades. En [nico://run](https://run.nico.ar) puedo publicar las sesiones completadas y mostrar el próximo entrenamiento con su duración y distancia estimada.

Hay herramientas excelentes haciendo distintas partes del trabajo. Lo mío fue conectarlas, adaptar los datos, resolver las incompatibilidades y construir una interfaz donde todo ese recorrido tuviera sentido. La mayor parte del tiempo se fue en probar, encontrar errores y comprobar que una corrección no rompiera otra cosa.

Ahora falta lo más difícil: salir a correr y cumplir lo que planificamos. 😁
