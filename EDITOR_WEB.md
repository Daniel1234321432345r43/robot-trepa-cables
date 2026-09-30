# Editor web local (`editor_web.html`)

Herramienta de **un solo archivo** para abrir el ensamblaje y **borrar, aislar,
ocultar, duplicar y recolocar sus piezas** desde el navegador. No instala nada,
no necesita servidor y **funciona sin conexión**: three.js y las 49 piezas van
incrustadas dentro del HTML.

## Cómo abrirlo

- En este proyecto ya está en la pestaña **Preview**.
- Servido sin caché: `python3 servir_editor.py` → http://127.0.0.1:8123/editor_web.html
- O directamente en Chrome: `file:///home/danelllealdaguilar10/3d-models/editor_web.html`
  (aquí, si no ves los cambios, **Ctrl+Mayús+R**: Chrome guarda una copia de los
  archivos locales).

### Cómo saber si estás viendo el archivo nuevo

Cada compilación estampa **fecha y hora** en el título de la pestaña y en una  pastilla de la cabecera (`25/09 17:04`). Si la pastilla no coincide con la última
compilación que se hizo, lo que tienes delante es una **copia vieja del
navegador**, no un archivo mal generado: recarga con Ctrl+Mayús+R.

Este problema es real y tiene causa concreta: `python3 -m http.server` no manda
`Cache-Control`, y el navegador aplica su heurística de frescura (10 % del
tiempo desde el `Last-Modified`), así que puede seguir mostrando la copia vieja
del HTML después de reconstruirlo. Por eso `servir_editor.py` manda
`no-store, no-cache, must-revalidate`, ignora los `If-Modified-Since` (para no
contestar 304) y reescribe siempre el archivo entero.

## Aspecto por defecto de los materiales

Dos reglas, y la segunda salió de una petición explícita ("que la estructura sea
un poco más gris y con más reflejos"):

- **Plástico y todo lo demás**: blanco puro `#ffffff`, `roughness 0.65`,
  `metalness 0.1`. Se ve la luz reflejada y un brillo tenue, nada de espejo ni
  cromo.
- **Metal**: las 25 piezas cuyos datos de origen dicen que son metal
  (`metal >= 0,5`: la estructura abierta, los soportes de rodamiento de las
  ruedas y de los engranajes medianos, los ejes de rueda y de engranaje, los
  piñones, las cuatro cadenas, los dos engranajes medianos, la abrazadera, los
  dos motores y los pines) van en gris `#adb3bd`,
  `roughness 0.26`, `metalness 0.72`. La metalidad
  es 0,72 y no 0,9 a propósito: un metal puro solo devuelve entorno, y en tema
  oscuro el entorno es oscuro, así que la estructura se quedaba casi negra.

Cada pieza **recuerda su color de material original** y hay un botón para
recuperarlo. Pintar cambia solo el color base: la rugosidad y el metalizado se
mantienen, que es lo que se pidió al añadir el selector de color.

Tres decisiones que hacen falta para que el blanco se vea bien, no solo sea
blanco:

- **Mapeo tonal ACES** (`toneMappingExposure 1.05`). Con albedo blanco y cuatro
  luces, sin mapeo tonal las caras iluminadas se recortan a blanco plano y el
  objeto pierde el volumen.
- **Luces a la mitad** (hemisferio + 3 direccionales, `0.42 / 0.70 / 0.42 / 0.26`).
  El motivo no es el blanco sino el color: con las intensidades anteriores una cara
  a plena luz recibía ~2,5 de luz y el mapeo tonal se llevaba el color por delante,
  así que una pieza pintada de rojo `#e0534a` se veía **rosa**. Ahora recibe ~1,2:
  el blanco sigue leyéndose blanco y los colores conservan su saturación.
- **Entorno de estudio con PMREM**. Los reflejos no salen de las lámparas: una
  superficie pulida devuelve su entorno. Se fabrica un entorno mínimo (esfera con
  degradado cielo→suelo y dos paneles claros a modo de softbox), se pasa por
  `PMREMGenerator.fromScene` y se cuelga de `escena.environment`. Es una textura,
  así que **no añade ni una llamada de dibujo** por fotograma. Se calcula una vez
  por tema (156 ms en claro, 172 ms en oscuro, medido aquí) y se cachea.

## Tema claro y oscuro: ahora también el lienzo

El botón de tema (o la tecla `C`) cambia el panel **y el lienzo 3D**, como se
pidió:

| | Tema oscuro | Tema claro |
|---|---|---|
| Fondo del render | `#14171b` | **`#ffffff`** (blanco puro) |
| Losa (la "estructura") | `#1b202a`, rug 0,70 | `#a9b0ba`, rug 0,30, un poco más gris que el fondo y con más reflejos |
| Suelo | `#0d0f13`, rug 1,00 | `#dfe3e9`, rug 0,50 |
| Rejilla | gris azulada | gris clara |
| Reflejos | entorno tenue (0,35 en la losa, 0,70 en las piezas) | entorno claro (0,55 en la losa, 0,55 en las piezas) |

Los colores de las piezas **no** cambian con el tema: el tema cambia la luz y el
entorno que reciben, no su pintura.

## La losa: el montaje se apoya encima

Antes la base era una lámina de 1 mm y el montaje la atravesaba (el 43 % del
robot, unos 90 mm, quedaba por debajo, colgando en el aire). Ahora es una **losa
sólida** de 12 mm de canto y 20 mm de vuelo alrededor del montaje, y su cara
superior está exactamente en el punto más bajo de la pieza (`z = −90`), así que
el robot **apoya encima entero**, sin hundirse. El suelo queda 12 mm más abajo y
la rejilla se dibuja sobre el suelo, 0,2 mm por encima del plano para no pelear
con él.

## Color por objeto

El bloque **Color** trabaja sobre la pieza seleccionada:

- selector de color nativo (`<input type=color>`) y campo de código `#RRGGBB`
  (acepta con o sin `#`; si escribes algo inválido, se revierte);
- 10 muestras rápidas con marca en la que coincide con la pieza elegida;
- **Blanco** (`W`) y **Original** para volver al `#ffffff` o al color del
  material de origen;
- **Aplicar a todas**: reparte el color actual por todo el conjunto.

Cambiar el color **solo toca el color base**: la iluminación, el reflejo tenue y
la transparencia no se alteran. La exportación usa el color que se ve (el 3MF
agrupa los materiales **por color**, no por material original).

## Selección y feedback visual

La pieza elegida se marca de dos formas: un **recuadro azul** ajustado a su
volumen real (con 3 mm de aire) que sigue sus giros, y un tinte emisivo muy
suave. Al pasar el ratón por encima, un tinte aún más leve.

El tinte se calcula **sobre el color propio de la pieza**, no con un azul fijo:
con azul, una pieza pintada de rojo se ve morada justo mientras está
seleccionada. La señal principal sigue siendo el recuadro.

Los rótulos de los módulos se apartan verticalmente cuando se solapan, y además
se **retienen dentro del lienzo**: con un encuadre ajustado el ancla puede caer
fuera y esta capa recorta lo que se sale.

## Encuadre automático

Encuadrar (botón o tecla `F`, y también al abrir) se calcula así:

- por los **vértices reales**, no por las 8 esquinas de la caja envolvente. Esta
  pieza tiene forma de L (un cable largo y fino que sale por un lado) y su caja
  contiene mucho aire: encuadrar por la caja dejaba el modelo al **66 %** del
  ancho y descentrado;
- **midiendo y corrigiendo varias veces en NDC**, porque la proyección no es
  lineal: un vértice más cerca de la cámara cae más lejos en pantalla, así que
  repartir la distancia con medidas tomadas en el plano del objetivo dejaba el
  modelo descuadrado (se salía por la derecha). Converge en 4 pasadas y da un
  relleno de `1,65 × 1,79` sobre un objetivo de `1,79`, con el centro a 0,025 NDC
  del centro exacto;
- con un **12 % de aire**, y un tope que aleja la cámara si algún vértice quedara a
  menos de 15 mm del plano cercano (pasa al mirar el conjunto casi de canto).

El encuadre inicial además es **determinista**. Salía distinto en cada recarga
porque el lienzo no tiene su tamaño definitivo cuando arranca el script (el panel
todavía reserva el hueco de su barra de scroll y la fuente puede cambiar el
layout), y un cambio de tamaño recalculaba la medida pero **no** el encuadre. Ahora
se reajusta cuando el layout se asienta y, mientras el usuario no haya tocado la
cámara, redimensionar reencuadra en vez de dejar el modelo descentrado. Si ya la
moviste, tu punto de vista se respeta.

## Qué se puede hacer

| Acción | Cómo |
|---|---|
| Seleccionar | clic en la pieza en la vista 3D **o** clic en su fila de la lista |
| Aislar | botón *Aislar* o tecla `I` |
| Ocultar / mostrar | botón *Ocultar* (`H`) o el ojo de cada fila |
| Borrar | botón *Borrar* o tecla `Supr` — se quita de la escena **y** de la exportación |
| Recuperar | *Restaurar* devuelve todas las borradas |
| Añadir una pieza | *Duplicar* crea una copia, desplazada y seleccionada, lista para mover |
| Mover | campos **Pos** X/Y/Z en mm, o `flechas` (1 mm, con `Mayús` 10 mm) |
| Girar | campos **Giro** X/Y/Z en grados; el pivote es el centro de cada pieza |
| Pintar | bloque **Color**: selector, código hex o muestras |
| Deshacer posición/giro | *Origen* y *Sin giro* |
| Empezar de cero | *Reiniciar todo* (restaura visibilidad, colores y transformaciones) |
| Encuadrar | *Encuadrar* o `F` — calcula la distancia justa proyectando las esquinas del bbox |
| Etiquetas | botón *Etiquetas* o tecla `T` |
| Tema claro / oscuro | botón de la cabecera o tecla `C` (se recuerda entre sesiones) |
| Vista | arrastrar = girar · rueda = zoom · botón derecho o `Mayús`+arrastrar = desplazar |

## Exportar "lo que ves"

Solo se exportan las piezas **visibles y no borradas**, con sus posiciones y
giros aplicados.

| Formato | Qué conserva | Para qué |
|---|---|---|
| **3MF** | las piezas como **objetos separados**, con nombre y color | el bueno: se puede seguir editando pieza a pieza en cualquier slicer |
| **OBJ + MTL** | grupos `o` + `usemtl` por pieza, y el MTL que describe cada color | Blender, MeshLab. Van juntos en un **ZIP**: un OBJ solo lleva el color a través de su MTL, y el `.mtl` del generador usa los materiales originales, no los colores del editor |
| **STL** | una sola malla | imprimir. Ojo: el STL **no puede** guardar piezas sueltas, es una limitación del formato |
| **Info** | JSON con el estado (posiciones, giros, visibilidad) | registrar o reproducir un montaje |

## Rendimiento en este equipo (medido)

Este Chromebook no tiene GPU, así que el visor lo dibuja la CPU. La primera
versión redibujaba sin parar a densidad 2 y con antialias: **290 ms por
fotograma (3 FPS)**. Con densidad 1, sin antialias y **dibujo bajo demanda**
(solo se repinta cuando algo cambia) queda en **4,5 ms por fotograma** — 65
veces más rápido — y **0 fotogramas en reposo**, o sea, consumo nulo mientras
no tocas nada.

## Verificación (medida, no supuesta)

- La geometría del navegador se comparó con la del generador de Python: suma de
  todas las coordenadas **42025.01 / 196474.85 / 206545.20** en ambos, 12.324
  triángulos, rango X ±180. El viaje JSON → GPU → exportación es idéntico.
- **STL**: 616.284 bytes = 84 + 12324 × 50, exacto.
- **OBJ**: 38 objetos, 6.948 vértices, 12.324 caras.
- **3MF**: el archivo generado *dentro del navegador* se extrajo y lo validó
  Python: `zipfile` abre el contenedor, **CRC correcto en las tres entradas**,
  XML válido, `unit="millimeter"`, objetos e items bien referenciados, índices
  de triángulo dentro de rango, y el color de la pieza translúcida con alfa
  (`plastic_clear` → `#C7E0F738`). En el ensamblaje de 38 piezas salía en 884.002
  bytes; el 3MF equivalente que escribe el generador con las 49 actuales son 194 KB.
- **Interacción** (comprobado otra vez con el rediseño de los dos engranajes
  medianos): duplicar 49 → 50 objetos, borrar la copia → 49 activos de 50,
  aislar → 1 de 49, mostrar todo → 49 de 49, y *Reiniciar todo* → vuelve a las 49
  originales, en la escena y en la lista. El clic real sobre el lienzo selecciona la pieza correcta
  (`SOPORTES_RODAMIENTO_RUEDA_IZQ`, 36,0 × 117,0 × 30,0 mm, pos `-48, 0, 91.5`),
  sin que un clic cuente como movimiento de cámara.
- **Materiales por defecto**: las piezas de plástico en `#ffffff` (rug 0,65 /
  met 0,1) y las 23 metálicas en `#adb3bd` (rug 0,26 / met 0,72) — contadas sobre
  los datos de origen, no a ojo — conservando cada una su color original y su
  transparencia para el botón *Original*.
- **Losa**: `baseArriba = −90,00` coincide con el mínimo del montaje (`−90`), así
  que no hay nada por debajo; el suelo queda en `−102` y la rejilla en `−101,8`.
  Comprobado además con `readPixels` sobre el fotograma: las líneas de la rejilla
  **no** se dibujan sobre la losa (con la losa oculta aparecen valores 219 donde
  con la losa hay un degradado 183–195): el orden de profundidad es correcto.
- **Tema claro**: `escena.background = #ffffff`, losa `#a9b0ba` con rug 0,30 y 1
  material por color en la exportación; al cambiar de tema se recalcula el color
  del suelo, de la losa y los dos colores de la rejilla (se reescriben los
  vértices de la rejilla, que lleva el color en el buffer).
- **Encuadre**: incluye la losa además de las piezas; rellenado medido `1,484 ×
  1,795` (objetivo 1,786). Al cambiar el tamaño del lienzo se reencuadra solo
  mientras no se haya tocado la cámara (`1,484 → 1,688` al pasar a 1200×760).
- **Color**: al pintar cambian el color base y el hexadecimal, pero **no** la
  rugosidad, el metalizado ni el alfa; 3MF y OBJ agrupan los materiales por color
  y admiten colores distintos en piezas opacas y translúcidas.
- **OBJ + MTL**: el ZIP se extrajo y lo validó Python: `zipfile` abre el
  contenedor, **CRC correcto**, `mtllib` apunta al MTL que viaja dentro, todos los
  `usemtl` tienen su `newmtl`, el `Kd` coincide con el color pintado
  (`0.255 0.690 0.431` → `#41b06e`) y el translúcido conserva `d 0.220`.
- **Etiquetas**: las 8 quedan dentro del lienzo y sin solaparse entre ellas.

## Dos fallos que aparecieron al hacer esto (y se corrigieron)

1. **Etiquetas colocadas con la cámara del fotograma anterior.** `pintarEtiquetas()`
   proyecta con `camara.matrixWorldInverse`, y esa matriz solo la refresca
   `render.render()`, que va después. Con el dibujo bajo demanda bastaba con que el
   último fotograma siguiera a un cambio de cámara para que las 8 etiquetas
   acabaran **apiladas en una esquina** hasta el siguiente repintado. Ahora la
   cámara se actualiza dentro de `dibujar()`, antes de proyectar los rótulos.
2. **El arranque lanzaba una excepción.** Al meter la losa en el encuadre,
   `act.forEach(sumar)` pasaba a la función el *registro* de la pieza en vez de su
   malla, así que `encuadrar()` reventaba en el arranque con
   `malla.updateMatrix is not a function`. El error quedaba fuera del `try` del
   dibujo: la página seguía pintándose con el **encuadre por defecto** y no se
   registraban ni el reencuadre al redimensionar ni el ajuste al cargar la fuente.
   Corregido y verificado: el rellenado es 1,795 (objetivo 1,786) y responde al
   cambio de tamaño.

## Regenerarlo

```bash
python3 editor_web.py              # reconstruye editor_web.html (y actualiza el sello)
python3 servir_editor.py           # lo sirve sin caché en el puerto 8123
```

El script reutiliza `generar_robot_modular.py` —las piezas son las mismas que
las del `.obj` y el `.3mf`, hay una sola fuente de verdad— e incrusta
`vendor/three-0.149.0.min.js` (build UMD, define el global `THREE`).
Se edita la plantilla `editor_web_template.html`, no el HTML final.

## Límites honestos

- Las piezas **no se fusionan**: borrar o mover una nunca altera a las demás.
  Si lo que quieres es una pieza nueva de verdad, esto no es CAD: usa
  MeshLab (instalado, ver `HERRAMIENTAS_ESTE_EQUIPO.md`) o Blender.
- **Tinkercad sigue sin poder** leer el 3MF ni separar una malla importada; eso
  no lo arregla esta herramienta, es un límite de Tinkercad.
- Rotación en orden XYZ alrededor del centro de la pieza, sin escala.
- Guardo solo el estado en memoria: si recargas, vuelve al montaje original
  (usa *Info* para guardar el JSON antes de recargar).
