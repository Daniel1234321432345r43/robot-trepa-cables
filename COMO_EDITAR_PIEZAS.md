# Editar las piezas: por qué Tinkercad no puede y qué sí usa la gente

Respuesta corta: **no existe ninguna página que meta piezas sueltas con sus
posiciones dentro de Tinkercad**, porque el problema no es de la página sino de
Tinkercad. Lo que sí existe es un **formato** que hace exactamente lo que pides
(3MF) y varios programas gratuitos que lo abren con las piezas ya separadas y
colocadas.

---

## 1. Por qué Tinkercad no es la herramienta adecuada

Tres límites reales de Tinkercad, no opiniones:

| Límite | Consecuencia |
|---|---|
| Solo importa **STL, OBJ y SVG**. No admite 3MF, AMF ni STEP. | Aunque generáramos el archivo perfecto con piezas separadas, Tinkercad no lo lee. |
| Sube **un archivo por vez** y **centra cada importación en el origen**. | 31 piezas = 31 subidas + recolocar a mano. |
| Una malla importada entra como **un único objeto y no se puede desagrupar** (no hay *Ungroup* para mallas importadas). | No puedes borrar ni mover una pieza dentro del STL. La única salida es la técnica de la forma "hueco" (*hole*) para restar material. |

Si además exportas desde Tinkercad en STL, los objetos separados se fusionan;
para conservarlos hay que exportar en **OBJ**. Es el mismo formato de entrada
que ya tienes (`robot_modular.obj`): Tinkercad no lo aprovecha al importar.

## 2. Lo que sí funciona: un archivo, muchas piezas colocadas

El formato que resuelve el problema es **3MF**: es un ZIP con XML que guarda
**N objetos**, cada uno con su **nombre**, su **posición** y su **color**.
Con `--3mf` se genera `robot_modular.3mf`: 31 objetos, 5 materiales, en un
solo archivo de ~72 KB.

Programas gratuitos que lo abren mostrando las piezas por separado y en su
sitio:

- **Bambu Studio / Orca Slicer / PrusaSlicer** — arrastra el `.3mf` a la ventana.
  Aparecen como objetos independientes: clic y `Supr` en uno solo.
- **Blender** — `File > Import > 3MF` (importador incluido en versiones
  recientes). Ya venían igual por OBJ.
- **Visores 3MF online gratuitos** (solo mirar): printnexus.io, stlviewer.online,
  grandpacad.com, a23d.co. Subes el archivo y seleccionas objetos en una lista.
  Nada se instala.

## 3. No hace falta "IA" para separar piezas: es un botón

Separar una malla en sus piezas sueltas (*shells*) es un algoritmo clásico, sin
IA, que ya está en todas las herramientas de 3D:

| Herramienta | Acción | ¿Conserva posiciones? |
|---|---|---|
| **Bambu Studio / Orca** | botón **Split to Parts** | **Sí**, mantiene cada pieza donde estaba |
| Bambu Studio / Orca | **Split to Objects** | No: reacomoda cada pieza sobre la cama de impresión |
| **Blender** | *Separate > By loose parts* | **Sí** (separar no mueve nada) |
| PrusaSlicer | clic derecho > *Split to objects / parts* | mismo criterio que Bambu |
| Meshmixer | *Edit > Separate Shells* | Sí |
| Descomponedor online | stl-splitter.com, split.actionbox.ca | Suele recortar por volumen, no separar por piezas |

Aviso medido en este modelo: `robot_modular.stl` no tiene 33 cascaras sino
**541**, porque cada pieza se construye uniendo primitivas (las cuatro cadenas
son ~130 rodillos y placas). Sale de un clic — *Split to parts* te las da todas
en su sitio —, pero es más granularidad de la que necesitas. Para editar "el
módulo C" o "los dos engranajes medianos", el 3MF (31 objetos) es mucho más
cómodo.

## 4. Si insistes en Tinkercad

Tienes dos caminos:

1. **`stl_grupos/` + `POSICIONES.txt`** — 4 conjuntos con la posición exacta a
   teclear tras cada importación. Cuatro subidas, no 33.
2. **Diseñar en otra herramienta y subir a Tinkercad solo lo que ya esté
   resuelto** — para rediseñar de verdad hay opciones gratuitas mejores:
   Fusion 360 (personal), FreeCAD, Onshape (web, gratis para proyectos
   públicos), Blender. Tinkercad brilla para piezas simples, no para
   ensamblajes mecánicos de 31 piezas.

## 5. Utilidad incluida: una carpeta de STLs -> un 3MF

`carpeta_a_3mf.py` es el programa que preguntabas, aplicable a cualquier
proyecto: recibe una carpeta de `.stl` y devuelve **un único `.3mf` con cada
archivo como objeto independiente**, respetando las coordenadas originales.

```bash
python3 carpeta_a_3mf.py stl_grupos robot_grupos.3mf      # 4 objetos
python3 carpeta_a_3mf.py stl_piezas robot_piezas.3mf      # 31 objetos
python3 carpeta_a_3mf.py --comprobar robot_modular.3mf    # validar un .3mf
```

Genera además una tabla con el centro de cada pieza en X/Y/Z y el tamaño del
ensamblaje, útil para comprobar que nada quedó flotando. Lee STL binario y
ASCII y sobrevive a un archivo corrupto sin abortar el resto.
