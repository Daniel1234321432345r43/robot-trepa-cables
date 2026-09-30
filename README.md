# Robot modular trepador de cable

Robot de 4 módulos para trepar por un cable, con ruedas de tracción por
goma, transmisión por cadenas y dos motores. Todo es **imprimible en 3D** y
encaja con tornillería M3/M4 y varillas de acero de 5 mm.

![49 piezas · 23.476 triángulos](https://img.shields.io/badge/piezas-49-blue)
![malla estanca](https://img.shields.io/badge/aristas_mal_emparejadas-0-green)

## Estructura

| Grupo | Contenido | Altura (Z) |
|-------|-----------|-----------|
| **T** | Conjunto superior: cable, 2 ruedas, ejes, engranajes medianos, 4 cadenas | +0 … +122 |
| **A** | Módulo de engranajes (sin tapa, reforzado con marco y costillas) | 0 … +45 |
| **B** | Electrónica: breadboard, jumpers, postes de dirección, guías de estructura | −35 … 0 |
| **C** | Motores, ejes y batería de litio | −90 … −35 |

## Comandos

```bash
# Regenerar el modelo y todas las exportaciones (STL, 3MF, OBJ, MTL, previews)
python3 generar_robot_modular.py --stl --3mf

# Regenerar el editor web (autocontenido: incrusta three.js y los datos)
python3 editor_web.py            # escribe editor_web.html y web/index.html

# Verlo en local (puerto 8123, sin caché)
python3 servir_editor.py         # -> http://127.0.0.1:8123/editor_web.html
```

## El editor 3D

`editor_web.html` es un único archivo de ~1,2 MB: lleva **three.js y los datos
del modelo incrustados**, sin CDN ni peticiones de red. Se abre haciendo doble
clic, sin servidor. Permite girar, hacer zoom, seleccionar y ocultar piezas por
grupo, cambiar colores y exportar **justo lo que se ve** a 3MF, OBJ o STL
(el 3MF se genera en el navegador, con ZIP y CRC32 implementados a mano).

> Nota: por diseño el editor pinta el plástico de blanco y el metal de gris. El
> color real de cada material está en el `.mtl` / `.3MF` y se recupera con el
> botón **Original**.

## Publicar en Vercel

El sitio que se publica es `web/index.html`, una copia idéntica del editor.
No hay build: Vercel sirve el archivo tal cual.

1. Importa el repositorio en Vercel (o `npx vercel`).
2. Como `vercel.json` ya está en la raíz, no hay nada que configurar:
   - **Framework Preset:** Other
   - **Output Directory:** `web`
   - **Build Command:** dejar vacío
3. Cada vez que cambies el modelo, sube el `web/index.html` regenerado y Vercel
   despliega la versión nueva.

Alternativa sin dashboard: `npx vercel --prod` desde la raíz del repositorio.

## Documentación

- [`COMO_EDITAR_PIEZAS.md`](COMO_EDITAR_PIEZAS.md) — cambiar dimensiones sin romper la malla.
- [`HERRAMIENTAS_ESTE_EQUIPO.md`](HERRAMIENTAS_ESTE_EQUIPO.md) — qué se usa en este equipo (Chromebook sin GPU).
- [`EDITOR_WEB.md`](EDITOR_WEB.md) — atajos y API interna del editor.
