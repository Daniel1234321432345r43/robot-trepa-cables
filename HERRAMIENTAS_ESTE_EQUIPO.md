# Qué herramientas 3D funcionan en este equipo

Todo lo de este documento está **medido en la máquina**, no estimado.

## El equipo

| Dato | Valor medido |
|---|---|
| Tipo | Chromebook con contenedor Linux (Crostini) — pista: existe `/mnt/chromeos`, host `penguin` |
| SO | Debian GNU/Linux 13 (trixie) |
| Arquitectura | **aarch64 / arm64** (`dpkg --print-architecture` → `arm64`) |
| CPU | 8 núcleos, implementador **0x51 = Qualcomm** |
| RAM | 6,5 GB, **sin swap** |
| GPU | **no hay** `/dev/dri` → OpenGL por software. MeshLab reporta `Using OpenGL 4.5` |
| Disco | 31 GB (quedó al 69 % tras liberar 8,5 GB de cachés) |

Consecuencia directa: **sirve para editar mallas y para render por CPU**, no para
animar ni para render por GPU.

## MeshLab — instalado y funcionando (sin root)

Instalado **sin permisos de administrador**: se descargaron los 12 `.deb`
(8,5 MB comprimidos) y se extrajeron aislados en `~/.local/opt/meshlab/rootfs`
(40 MB). Nada del sistema se tocó.

Comprobado: abre `robot_modular.obj` — el ensamblaje completo, **38 piezas y
12.324 triángulos** en aquel momento (ahora son 31 y 9.308) — en 104 ms, con
OpenGL 4.5 por software.

- Lanzador: `meshlab` (está en el PATH, vía `~/.local/bin/meshlab`).
  Para abrirlo con el proyecto: `meshlab ~/3d-models/robot_modular.obj`
- También aparece en el menú de aplicaciones de ChromeOS
  (`~/.local/share/applications/meshlab.desktop`)
- Cerrarlo: `pkill -f meshlab`

Comprobación de que está completo: el proceso tiene **69 plugins cargados**
(276 mapeos en `/proc/<pid>/maps`), así que no es un MeshLab capado. MeshLab
resuelve la carpeta `plugins/` respecto al ejecutable, por eso funciona desde la
extracción local aunque la ruta del sistema no exista.

### Flujo para borrar o cambiar una pieza

Nombres de filtro **verificados en los propios plugins** de esta instalación
(`grep` sobre `libedit_select.so`, `libfilter_select.so` y `libfilter_layer.so`):

1. Olvida el archivo único: importa `stl_grupos/*.stl` (los 4 conjuntos). Cada
   archivo entra como **una capa propia**. Si MeshLab pregunta si quieres
   fusionarlas, responde que **no**.
2. Para aislar dentro de una capa, en el menú **Filters > Selection**:
   `Select Connected Components in a region`.
3. Para borrar lo seleccionado, también en **Filters > Selection**:
   `Delete Selected Faces` o `Delete Selected Vertices`.
   Para tirar una capa entera, en **Filters > Mesh Layer**: `Delete Current Mesh`.
4. `File > Export Mesh As` para volver a sacar el modelo en STL u OBJ.

Nota: MeshLab **no** trae `meshlabserver` ni `pymeshlab` en esta versión, así
que el trabajo por lotes habría que hacerlo con los scripts Python del repo.

## Blender — viable, pero necesita root

**Blender no publica builds oficiales de Linux ARM64.** Comprobado en
`download.blender.org` para 4.3, 4.5 (LTS) y 5.2: solo existe `linux-x64`;
ARM64 solo hay para macOS y Windows. Por tanto la única vía en este equipo es el
paquete de Debian (`blender 4.3.2+dfsg-2`, **arm64 nativo**, 650 MB con 182
paquetes), y ese paquete necesita permisos de administrador.

Yo no puedo instalarlo: esta sesión no tiene vía de elevación (`pkexec` no
está instalado). Tú sí, porque tu usuario está en el grupo `sudo`. En una
terminal de Linux:

```bash
sudo apt-get install -y blender
```

### ¿Va a ir bien con este procesador?

- **Render: sí, por CPU.** El script `render_robot_blender.py` usa **Cycles**,
  que solo necesita CPU. Lanza en modo sin interfaz:
  `blender -b -P render_robot_blender.py`. La escena es pequeña (12.324
  triángulos, 3 luces de área), así que cuenta con minutos, no horas.
- **EEVEE: no.** Necesita GPU real y aquí no hay.
- **Interfaz gráfica: lenta.** OpenGL 4.5 va por software (llvmpipe); el
  visor 3D de Blender se moverá con dificultad. Para renderizar, usa el modo
  sin interfaz y evita el problema.
- **Límite real: la RAM** (6,5 GB sin swap). Suficiente para esta escena, no
  para escenas grandes ni simulaciones.

## Disco: qué se liberó

Se borraron **8,51 GB** de cachés 100 % regenerables (disco 97 % → 69 %):

| Carpeta | Liberado |
|---|---|
| `~/.npm/_cacache` | 3.843 MB |
| `~/.bun/install/cache` | 2.582 MB |
| `~/.local/share/pnpm/store` | 1.675 MB |
| `~/.npm/_npx` | 588 MB |
| `~/.cache/pip` | 144 MB |
| `~/.cache/node-gyp` | 63 MB |

Se vuelven a crear solas cuando vuelvas a usar npm, bun, pnpm o pip; el único
efecto es que la próxima instalación tarda un poco más. **No se tocó**
`~/.local/share/claude` (1,5 GB) porque son datos de aplicación, no caché.
