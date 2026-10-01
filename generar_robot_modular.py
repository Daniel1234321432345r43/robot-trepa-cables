#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador procedural (Python puro, sin dependencias) del modelo 3D:

    ROBOT MODULAR QUE RUEDA SOBRE CABLE   ("cable-riding modular robot")

Mecanica (dos ruedas arriba, un engranaje central y dos motores):
  * DOS RUEDAS blancas de traccion, SEPARADAS a lo largo del cable (+-48 mm),
    cada una en su EJE METALICO con DOS SOPORTES DE RODAMIENTO. Con dos
    puntos de apoyo ya no hace falta NADA debajo del cable: se elimina el
    tensor inferior (rodillo + resorte) y cualquier soporte por abajo.
  * GOMA TEXTURIZADA en la garganta de cada rueda.
  * ENGRANAJE CENTRAL a la altura de las ruedas: es el repartidor. Recibe la
    fuerza de los DOS MOTORES (uno a cada costado del chasis, cada uno con su
    cadena de rodillos hasta el pinon central) y saca DOS CADENAS, una a cada
    rueda. Cuatro cadenas en total.
  * Chasis = pila de 3 modulos imprimibles en 3D interconectados:
        MODULE A: CAJA HUECA (SIN TAPA)
        MODULE B: CAJA HUECA
        MODULE C: CAJA HUECA + LOS DOS MOTORES

Salidas:
    robot_modular.obj / robot_modular.mtl   mallas + materiales
    robot_modular_preview.html              previsualizacion interactiva
    robot_modular_parts.json                indice de piezas
    robot_modular.stl                       (con --stl) malla unica imprimible
    robot_modular.3mf                       (con --3mf) PIEZAS SEPARADAS Y COLOCADAS

Para editar las piezas sin instalar nada:  python3 editor_web.py  ->
editor_web.html, un editor en el navegador para borrar, aislar, duplicar y
recolocar cada pieza, con exportacion a 3MF / OBJ / STL.

Uso:
    python3 generar_robot_modular.py
    python3 generar_robot_modular.py --stl
    python3 generar_robot_modular.py --escala 0.5
"""

import argparse
import json
import math
import os
import struct
import sys
import zipfile

TAU = math.tau

# --------------------------------------------------------------------------
#  RESOLUCION GLOBAL  (misma estructura, muchos menos vertices)
# --------------------------------------------------------------------------
# Todas las primitivas redondean su numero de segmentos con _seg(). Bajando
# DETALLE baja el numero de triangulos de TODO el modelo sin cambiar ni una
# sola medida ni la posicion de ninguna pieza: los cilindros pasan a ser
# poligonos mas gruesos, las ruedas pierden suavidad y las cadenas llevan
# menos rodillos. DETALLE = 1.0 es el detalle original.
DETALLE = 0.45


def _seg(n, minimo=3):
    return max(minimo, int(round(n * DETALLE)))


# --------------------------------------------------------------------------
#  materiales  (nombre: color difuso, alfa, brillo, color especular)
# --------------------------------------------------------------------------
MATS = {
    "plastic_white":  ((0.93, 0.93, 0.91), 1.0,  70, (0.30, 0.30, 0.30)),
    "plastic_black":  ((0.07, 0.07, 0.08), 1.0,  40, (0.12, 0.12, 0.12)),
    "plastic_clear":  ((0.78, 0.88, 0.97), 0.22, 250, (0.90, 0.90, 0.90)),
    "wood_pla":       ((0.60, 0.40, 0.22), 1.0,  18, (0.14, 0.10, 0.06)),
    "metal_steel":    ((0.62, 0.64, 0.68), 1.0, 320, (0.95, 0.95, 0.95)),
    "metal_dark":     ((0.34, 0.35, 0.38), 1.0, 260, (0.70, 0.70, 0.70)),
    "rubber_black":   ((0.05, 0.05, 0.06), 1.0,   8, (0.04, 0.04, 0.04)),
    "pcb_blue":       ((0.05, 0.22, 0.45), 1.0,  50, (0.20, 0.20, 0.20)),
    "pcb_green":      ((0.05, 0.30, 0.18), 1.0,  50, (0.20, 0.20, 0.20)),
    "breadboard":     ((0.92, 0.92, 0.90), 1.0,  55, (0.25, 0.25, 0.25)),
    "component_dark": ((0.16, 0.16, 0.18), 1.0,  60, (0.20, 0.20, 0.20)),
    "battery_pack":   ((0.12, 0.14, 0.20), 1.0, 120, (0.45, 0.45, 0.50)),
    "battery_cell":   ((0.20, 0.22, 0.28), 1.0, 120, (0.45, 0.45, 0.50)),
    "wire_red":       ((0.78, 0.08, 0.06), 1.0,  60, (0.30, 0.30, 0.30)),
    "wire_yellow":    ((0.88, 0.70, 0.06), 1.0,  60, (0.30, 0.30, 0.30)),
    "wire_black":     ((0.08, 0.08, 0.09), 1.0,  60, (0.20, 0.20, 0.20)),
    "wire_blue":      ((0.10, 0.24, 0.72), 1.0,  60, (0.30, 0.30, 0.30)),
    "label_white":    ((0.97, 0.97, 0.96), 1.0,  50, (0.25, 0.25, 0.25)),
    "copper":         ((0.72, 0.45, 0.20), 1.0, 200, (0.80, 0.70, 0.50)),
}

# --------------------------------------------------------------------------
#  primitivas  (siempre centradas en el origen, devuelven verts + caras)
# --------------------------------------------------------------------------
def prim_box(sx, sy, sz):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    v = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
         (-hx, -hy,  hz), (hx, -hy,  hz), (hx, hy,  hz), (-hx, hy,  hz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
    return v, f


def _axis_map(verts, axis):
    if axis == 'z':
        return verts
    out = []
    for (u, v, w) in verts:          # w es el eje del cilindro
        if axis == 'x':
            out.append((w, v, -u))
        elif axis == 'y':
            out.append((u, w, -v))
        else:
            raise ValueError(axis)
    return out


def prim_cylinder(r, length, seg=24, axis='z'):
    seg = _seg(seg, 3)
    h = length / 2.0
    v, f = [], []
    for i in range(seg):
        a = TAU * i / seg
        v.append((r * math.cos(a), r * math.sin(a), -h))
    for i in range(seg):
        a = TAU * i / seg
        v.append((r * math.cos(a), r * math.sin(a), h))
    for i in range(seg):
        j = (i + 1) % seg
        f.append((i, j, seg + j, seg + i))
    v.append((0.0, 0.0, -h))
    v.append((0.0, 0.0, h))
    cb, ct = 2 * seg, 2 * seg + 1
    for i in range(seg):
        j = (i + 1) % seg
        f.append((cb, j, i))
        f.append((ct, seg + i, seg + j))
    return _axis_map(v, axis), f


def prim_annulus(r_out, r_in, length, seg=24, axis='z'):
    seg = _seg(seg, 3)
    h = length / 2.0
    v, f = [], []
    for r in (r_out, r_in):
        for z in (-h, h):
            for i in range(seg):
                a = TAU * i / seg
                v.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(seg):                      # pared exterior
        j = (i + 1) % seg
        f.append((i, j, seg + j, seg + i))
    for i in range(seg):                      # pared interior (invertida)
        j = (i + 1) % seg
        f.append((2 * seg + i, 3 * seg + i, 3 * seg + j, 2 * seg + j))
    for i in range(seg):                      # tapa superior
        j = (i + 1) % seg
        f.append((seg + i, seg + j, 3 * seg + j, 3 * seg + i))
        f.append((i, 2 * seg + i, 2 * seg + j, j))   # tapa inferior
    return _axis_map(v, axis), f


def prim_torus(major, minor, mseg=32, nseg=12, axis='z'):
    mseg = _seg(mseg, 6)
    nseg = _seg(nseg, 4)
    v, f = [], []
    for i in range(mseg):
        u = TAU * i / mseg
        cu, su = math.cos(u), math.sin(u)
        for k in range(nseg):
            t = TAU * k / nseg
            rr = major + minor * math.cos(t)
            v.append((rr * cu, rr * su, minor * math.sin(t)))
    for i in range(mseg):
        i2 = (i + 1) % mseg
        for k in range(nseg):
            k2 = (k + 1) % nseg
            f.append((i * nseg + k, i2 * nseg + k, i2 * nseg + k2, i * nseg + k2))
    return _axis_map(v, axis), f


def prim_tube_path(points, radius, seg=10):
    """Tubo cerrado a lo largo de una polilinea, con marcos estables."""
    seg = _seg(seg, 3)
    pts = [tuple(p) for p in points]
    n = len(pts)
    tans = []
    for i in range(n):
        a = pts[(i - 1) % n]
        b = pts[(i + 1) % n]
        t = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ln = math.sqrt(sum(c * c for c in t)) or 1.0
        tans.append((t[0] / ln, t[1] / ln, t[2] / ln))
    v, f = [], []
    for i in range(n):
        t = tans[i]
        ref = (0.0, 0.0, 1.0)
        if abs(t[0] * ref[0] + t[1] * ref[1] + t[2] * ref[2]) > 0.95:
            ref = (1.0, 0.0, 0.0)
        b = (t[1] * ref[2] - t[2] * ref[1],
             t[2] * ref[0] - t[0] * ref[2],
             t[0] * ref[1] - t[1] * ref[0])
        lb = math.sqrt(sum(c * c for c in b)) or 1.0
        b = (b[0] / lb, b[1] / lb, b[2] / lb)
        nn = (b[1] * t[2] - b[2] * t[1],
              b[2] * t[0] - b[0] * t[2],
              b[0] * t[1] - b[1] * t[0])
        for k in range(seg):
            a = TAU * k / seg
            ca, sa = math.cos(a), math.sin(a)
            v.append((pts[i][0] + radius * (ca * nn[0] + sa * b[0]),
                      pts[i][1] + radius * (ca * nn[1] + sa * b[1]),
                      pts[i][2] + radius * (ca * nn[2] + sa * b[2])))
    for i in range(n):
        i2 = (i + 1) % n
        for k in range(seg):
            k2 = (k + 1) % seg
            f.append((i * seg + k, i * seg + k2, i2 * seg + k2, i2 * seg + k))
    return v, f


def prim_spring(coil_r, height, turns, tube_r=1.2, per_turn=18, seg=8):
    n = max(2, int(turns * per_turn))
    pts = []
    for i in range(n):
        a = TAU * turns * i / n
        pts.append((coil_r * math.cos(a), coil_r * math.sin(a),
                    height * i / n - height / 2.0))
    return prim_tube_path(pts, tube_r, seg)


# --------------------------------------------------------------------------
#  contenedores
# --------------------------------------------------------------------------
def signed_volume(verts, faces):
    vol = 0.0
    for face in faces:
        for i in range(1, len(face) - 1):
            a, b, c = verts[face[0]], verts[face[i]], verts[face[i + 1]]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1])
                    - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return vol


class Part(object):
    def __init__(self, name, mat, group, label=""):
        self.name = name
        self.mat = mat
        self.group = group
        self.label = label
        self.verts = []
        self.faces = []

    def solid(self, prim, loc=(0.0, 0.0, 0.0), rot_y=0.0, pivot=(0.0, 0.0, 0.0)):
        verts, faces = prim
        ops = []
        for (x, y, z) in verts:
            x, y, z = x + loc[0], y + loc[1], z + loc[2]
            if rot_y:
                px, pz = pivot[0], pivot[2]
                x, z = x - px, z - pz
                ca, sa = math.cos(rot_y), math.sin(rot_y)
                x, z = x * ca + z * sa, -x * sa + z * ca
                x, z = x + px, z + pz
            ops.append((x, y, z))
        if signed_volume(ops, faces) < 0.0:
            faces = [tuple(reversed(f)) for f in faces]
        off = len(self.verts)
        self.verts.extend(ops)
        self.faces.extend([tuple(i + off for i in f) for f in faces])
        return self

    # --- utilidades de calidad -------------------------------------------
    def edges_ok(self):
        seen = {}
        for face in self.faces:
            n = len(face)
            for i in range(n):
                a, b = face[i], face[(i + 1) % n]
                key = (a, b) if a < b else (b, a)
                seen[key] = seen.get(key, 0) + 1
        return sum(1 for v in seen.values() if v != 2)

    def volume(self):
        return signed_volume(self.verts, self.faces)

    def tri_count(self):
        return sum(len(f) - 2 for f in self.faces)

    def shells(self):
        """Numero de cascaras sueltas (lo que separa 'Split to objects')."""
        n = len(self.faces)
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        vmap = {}
        for fi, face in enumerate(self.faces):
            for vi in face:
                if vi in vmap:
                    ra, rb = find(fi), find(vmap[vi])
                    if ra != rb:
                        parent[ra] = rb
                else:
                    vmap[vi] = fi
        return len({find(i) for i in range(n)})


PARTS = []


def part(name, mat, group, label=""):
    p = Part(name, mat, group, label)
    PARTS.append(p)
    return p


def fan_triangles(face):
    return [(face[0], face[i], face[i + 1]) for i in range(1, len(face) - 1)]


# --------------------------------------------------------------------------
#  CONSTANTES DE LA ESCENA  (mm)
# --------------------------------------------------------------------------
CABLE_Z, CABLE_R = 60.0, 3.0
WHEEL_Z, WHEEL_R = 91.5, 30.0
SHAFT_R = 5.0
# Los soportes de rodamiento van DENTRO de la caja (y=+-28, a ras de la cara
# de dentro): asi no asoma nada hacia fuera salvo un poco de eje.
BEAR_Y = 28.0

# --- DOS ruedas de traccion arriba, separadas a lo largo del cable ---------
VANO = 48.0                     # cada rueda va en x = +-VANO (96 mm entre ejes)
RUEDA_XS = (-VANO, VANO)

# --- DOS engranajes medianos, uno por cara, PEGADOS A LA CAJA --------------
# El engranaje va bajo, casi tocando la caja (a la altura del borde superior
# del modulo B). De cada uno salen DOS cadenas, una hacia cada rueda, de modo
# que cada rueda queda abrazada por dos cadenas, una de cada lado. Los
# motores, abajo, suben su cadena por la cara de FUERA (y=+-72) hasta ese eje.
CHAIN_R = 10.5                  # pinones de entrada y de rueda
ENGR_MEDIO_X, ENGR_MEDIO_Z = 0.0, 8.0    # eje de los engranajes medianos
ENGR_MEDIO_R = 8.5                       # el "chiquitito"
ENGR_MEDIO_DIENTES = 10
PLANO_RUEDAS_A = 17.0           # y de la cadena de ruedas de la cara +Y
PLANO_RUEDAS_B = -17.0          # y de la cadena de ruedas de la cara -Y
PLANO_MOTOR_A = 72.0            # y de la cadena del motor +Y
PLANO_MOTOR_B = -72.0           # y de la cadena del motor -Y
MOTOR_X, PINON_Z = 23.0, -70.0  # los DOS motores, abajo, uno por cara
CADENA_PASO = 12.0              # separacion entre rodillos (mm)

MOD_W, MOD_D = 100.0, 70.0      # caja un poco mas ancha que antes (era 90)
MOD_A_Z, MOD_B_Z, MOD_C_Z = (0.0, 45.0), (-35.0, 0.0), (-90.0, -35.0)


# --------------------------------------------------------------------------
#  CADENAS DE RODILLOS EN UN PLANO HORIZONTAL (y = constante)
# --------------------------------------------------------------------------
def _tramo_recto(p, q, fino):
    n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / fino))
    return [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)
            for k in range(n)]


def _arco_horario(c, r, a0, a1, fino):
    """Arco de a0 a a1 girando en sentido horario (angulo decreciente)."""
    barrido = (a0 - a1) % TAU
    if barrido < 1e-9:
        barrido = TAU
    n = max(3, int(r * barrido / fino))
    return [(c[0] + r * math.cos(a0 - barrido * k / n),
             c[1] + r * math.sin(a0 - barrido * k / n)) for k in range(n)]


def circuito_cadena(c1, r1, c2, r2, paso=None, fino=2.0):
    """Camino cerrado de una cadena entre dos pinones.

    c = (x, z) es el centro de cada pinon dentro del plano de la cadena (todos
    los ejes van en Y); los radios pueden ser distintos. Devuelve puntos
    equiespaciados cada `paso` mm: en cada uno va un rodillo y entre dos
    consecutivos, las placas. Las dos rectas son las tangentes EXTERIORES
    comunes, asi que la cadena abraza cada pinon por el lado que no mira al
    otro.
    """
    return circuito_cadena_varios([(c1[0], c1[1], r1), (c2[0], c2[1], r2)],
                                  paso, fino)


def _muestrear(denso, paso):
    """Reparte los rodillos cada `paso` mm a lo largo del camino cerrado."""
    largos = [0.0]
    for i in range(1, len(denso)):
        largos.append(largos[-1] + math.hypot(denso[i][0] - denso[i - 1][0],
                                              denso[i][1] - denso[i - 1][1]))
    total = largos[-1] + math.hypot(denso[0][0] - denso[-1][0],
                                    denso[0][1] - denso[-1][1])
    npts = max(12, int(round(total / paso)))
    out, j = [], 0
    for k in range(npts):
        objetivo = total * k / npts
        while j + 1 < len(denso) - 1 and largos[j + 1] < objetivo:
            j += 1
        salto = largos[j + 1] - largos[j]
        t = (objetivo - largos[j]) / salto if salto > 1e-9 else 0.0
        out.append((denso[j][0] + (denso[j + 1][0] - denso[j][0]) * t,
                    denso[j][1] + (denso[j + 1][1] - denso[j][1]) * t))
    return out


def circuito_cadena_varios(circs, paso=None, fino=2.0):
    """Camino cerrado de una cadena que abraza DOS O MAS pinones.

    circs = [(x, z, r), ...] dentro del plano de la cadena (los ejes van en Y).
    Los pinones se ordenan girando en sentido horario alrededor de su centro y
    la cadena va recta de uno al siguiente (tangente exterior comun) con un
    arco alrededor de cada uno. Con dos pinones da EXACTAMENTE lo mismo que
    circuito_cadena(), que ahora es solo un atajo de esta.
    """
    if paso is None:
        paso = CADENA_PASO
    cxo = sum(c[0] for c in circs) / len(circs)
    czo = sum(c[1] for c in circs) / len(circs)
    orden = sorted(circs, key=lambda c: -math.atan2(c[1] - czo, c[0] - cxo))
    n = len(orden)

    tang = []                       # tang[k] = (punto en k, punto en k+1)
    for k in range(n):
        x1, z1, r1 = orden[k]
        x2, z2, r2 = orden[(k + 1) % n]
        dx, dz = x2 - x1, z2 - z1
        largo = math.hypot(dx, dz)
        phi = math.atan2(dz, dx)
        psi = phi + math.acos(max(-1.0, min(1.0, (r1 - r2) / largo)))
        ux, uz = math.cos(psi), math.sin(psi)
        tang.append(((x1 + r1 * ux, z1 + r1 * uz),
                     (x2 + r2 * ux, z2 + r2 * uz)))

    denso = []
    for k in range(n):
        a, b = tang[k]
        denso += _tramo_recto(a, b, fino)
        c = orden[(k + 1) % n]
        salida = tang[(k + 1) % n][0]
        denso += _arco_horario((c[0], c[1]), c[2],
                               math.atan2(b[1] - c[1], b[0] - c[0]),
                               math.atan2(salida[1] - c[1], salida[0] - c[0]),
                               fino)
    return _muestrear(denso, paso)


def pinon(p, x, y, z, dientes=12, r=CHAIN_R):
    """Rueda dentada de la cadena: nucleo + dientes, eje siempre en Y."""
    p.solid(prim_cylinder(r - 2.0, 8.0, 24, 'y'), (x, y, z))
    for k in range(dientes):
        a = TAU * k / dientes
        p.solid(prim_box(3.0, 7.0, 5.0),
                (x + r * math.cos(a), y, z + r * math.sin(a)),
                rot_y=math.atan2(-math.sin(a), math.cos(a)), pivot=(x, y, z))


def _cuerpo_cadena(ch, pts, y):
    """Rodillos + placas de una cadena ya calculada, en el plano y=cte."""
    n = len(pts)
    for i in range(n):
        x, z = pts[i]
        nx, nz = pts[(i + 1) % n]
        ch.solid(prim_cylinder(2.5, 7.0, 10, 'y'), (x, y, z))
        dx, dz = nx - x, nz - z
        ln = math.hypot(dx, dz) or 1.0
        ang = math.atan2(-dz / ln, dx / ln)
        for dy in (4.5, -4.5):
            ch.solid(prim_box(ln * 1.15, 2.0, 4.0), (x, y + dy, z),
                     rot_y=ang, pivot=(x, y, z))
    return ch


def cadena(nombre, c1, c2, y, grupo, paso=None, r=CHAIN_R):
    """Cadena de rodillos entre dos pinones, en el plano horizontal y=cte."""
    ch = part(nombre, "metal_steel", grupo)
    return _cuerpo_cadena(ch, circuito_cadena(c1, r, c2, r, paso), y)


def cadena_varios(nombre, circs, y, grupo, paso=None):
    """Cadena que abraza varios pinones (p. ej. el mediano y las 2 ruedas)."""
    ch = part(nombre, "metal_steel", grupo)
    return _cuerpo_cadena(ch, circuito_cadena_varios(circs, paso), y)


def rueda_de_traccion(grupo, x):
    """Una de las DOS ruedas: polea blanca + goma texturizada, en x=+-VANO."""
    lado = "IZQ" if x < 0 else "DER"
    wheel = part("POLEA_BLANCA_RUEDA_%s" % lado, "plastic_white", grupo)
    for sy in (-1.0, 1.0):
        wheel.solid(prim_annulus(WHEEL_R, 20.0, 4.0, 28, 'y'),
                    (x, sy * 10.0, WHEEL_Z))
    wheel.solid(prim_cylinder(22.0, 16.0, 28, 'y'), (x, 0.0, WHEEL_Z))
    for k in range(6):                       # aligeramientos (radio interior 13)
        a = TAU * k / 6.0
        wheel.solid(prim_cylinder(5.0, 16.5, 16, 'y'),
                    (x + 13.0 * math.cos(a), 0.0, WHEEL_Z + 13.0 * math.sin(a)))

    rubber = part("POLEA_GOMA_TRACCION_%s" % lado, "rubber_black", grupo)
    rubber.solid(prim_annulus(26.0, 22.0, 16.0, 28, 'y'), (x, 0.0, WHEEL_Z))
    for k in range(16):                      # textura del grip
        a = TAU * k / 16.0
        rubber.solid(prim_box(4.0, 16.0, 3.0),
                     (x + 27.0 * math.cos(a), 0.0, WHEEL_Z + 27.0 * math.sin(a)),
                     rot_y=math.atan2(-math.sin(a), math.cos(a)),
                     pivot=(x, 0.0, WHEEL_Z))


TOP_GROUP = "SUPERIOR: 2 RUEDAS + 2 ENGRANAJES MEDIOS"


# --------------------------------------------------------------------------
#  CONJUNTO SUPERIOR: 2 ruedas + ejes + rodamientos + 2 engranajes medianos
#  EN MEDIO (a la altura del modulo A) y las 4 cadenas
# --------------------------------------------------------------------------
def build_top():
    g = TOP_GROUP

    cable = part("CABLE_METAL_TENSADO", "metal_steel", g)
    cable.solid(prim_cylinder(CABLE_R, 360.0, 20, 'x'), (0.0, 0.0, CABLE_Z))

    # --- las DOS ruedas de traccion, separadas ---------------------------
    for x in RUEDA_XS:
        rueda_de_traccion(g, x)

    # --- un eje por rueda: corto, de rodamiento a rodamiento; solo asoma un
    # poco hacia fuera, justo donde engancha la cadena --------------------
    for x in RUEDA_XS:
        eje = part("EJE_METALICO_RUEDA_%s" % ("IZQ" if x < 0 else "DER"),
                   "metal_steel", g)
        eje.solid(prim_cylinder(SHAFT_R, 70.0, 24, 'y'), (x, 0.0, WHEEL_Z))
        for sy in (-1.0, 1.0):
            eje.solid(prim_cylinder(SHAFT_R * 0.75, 6.0, 16, 'y'),
                      (x, sy * 38.0, WHEEL_Z))

    # --- eje por ENGRANAJE MEDIANO: del pinon de la cadena de las ruedas
    # (y=+-17) al pinon de entrada del motor (y=+-72), pasando por el
    # rodamiento, que ahora va DENTRO de la caja --------------------------
    for signo, lado in ((1.0, "A"), (-1.0, "B")):
        part("EJE_ENGRANAJE_MEDIO_%s" % lado, "metal_steel", g).solid(
            prim_cylinder(SHAFT_R, 68.0, 24, 'y'),
            (ENGR_MEDIO_X, signo * 42.0, ENGR_MEDIO_Z))

    # --- BARRA que UNE los dos ejes de los engranajes medianos: ahora corta,
    # porque los dos engranajes se han acercado al centro ----------------
    part("BARRA_UNE_EJES_MEDIANOS", "metal_steel", g).solid(
        prim_cylinder(6.0, 24.0, 20, 'y'), (ENGR_MEDIO_X, 0.0, ENGR_MEDIO_Z))

    # --- soportes de rodamiento (metal): 2 ejes de rueda + los 2 medianos -
    # Los cuatro van DENTRO de la caja (y=+-28, a ras de la cara de dentro):
    # no asoma nada hacia fuera salvo un poco de eje.
    for x, suf in ((RUEDA_XS[0], "RUEDA_IZQ"), (RUEDA_XS[1], "RUEDA_DER")):
        brg = part("SOPORTES_RODAMIENTO_%s" % suf, "metal_dark", g)
        for sy in (-1.0, 1.0):
            brg.solid(prim_box(36.0, 14.0, 30.0), (x, sy * BEAR_Y, WHEEL_Z))
            brg.solid(prim_annulus(9.0, SHAFT_R, 14.0, 24, 'y'),
                      (x, sy * BEAR_Y, WHEEL_Z))
            brg.solid(prim_torus(11.0, 2.5, 24, 10, 'y'),
                      (x, sy * BEAR_Y, WHEEL_Z))

    # El soporte del mediano entra por el AGUJERO de la pared de detras de la
    # caja de arriba: queda dentro, apoyado en su suelo, y solo el eje asoma
    # por fuera. Ya no hay ninguna estructura impresa por fuera de la caja.
    bmed = part("SOPORTES_RODAMIENTO_ENGRANAJES_MEDIOS", "metal_dark", g)
    for sy in (-1.0, 1.0):
        bmed.solid(prim_box(30.0, 14.0, 26.0),
                   (ENGR_MEDIO_X, sy * BEAR_Y, ENGR_MEDIO_Z))
        bmed.solid(prim_annulus(9.0, SHAFT_R, 14.0, 24, 'y'),
                   (ENGR_MEDIO_X, sy * BEAR_Y, ENGR_MEDIO_Z))
        bmed.solid(prim_torus(11.0, 2.5, 24, 10, 'y'),
                   (ENGR_MEDIO_X, sy * BEAR_Y, ENGR_MEDIO_Z))

    # --- DOS ENGRANAJES MEDIANOS, uno por cara: cada uno es un eje con el
    # pinon chiquitito (el que mueve las ruedas) y el pinon de entrada (el
    # que recibe la cadena del motor) ------------------------------------
    for signo, lado in ((1.0, "A"), (-1.0, "B")):
        engr = part("ENGRANAJE_MEDIO_%s" % lado, "metal_dark", g)
        pinon(engr, ENGR_MEDIO_X, signo * abs(PLANO_RUEDAS_A), ENGR_MEDIO_Z,
              ENGR_MEDIO_DIENTES, ENGR_MEDIO_R)
        pinon(engr, ENGR_MEDIO_X, signo * abs(PLANO_MOTOR_A), ENGR_MEDIO_Z)

    # --- un pinon de cadena en cada rueda y en CADA UNA de las dos caras --
    pinones_r = part("PINONES_RUEDAS", "metal_dark", g)
    for x in RUEDA_XS:
        for py in (PLANO_RUEDAS_A, PLANO_RUEDAS_B):
            pinon(pinones_r, x, py, WHEEL_Z)

    pinones_m = part("PINONES_MOTORES", "metal_dark", g)
    pinon(pinones_m, -MOTOR_X, PLANO_MOTOR_A, PINON_Z)
    pinon(pinones_m, +MOTOR_X, PLANO_MOTOR_B, PINON_Z)

    # --- las CUATRO cadenas ----------------------------------------------
    # una por motor: sube desde el motor hasta el eje de los medianos ...
    cadena("CADENA_MOTOR_A", (-MOTOR_X, PINON_Z),
           (ENGR_MEDIO_X, ENGR_MEDIO_Z), PLANO_MOTOR_A, g)
    cadena("CADENA_MOTOR_B", (+MOTOR_X, PINON_Z),
           (ENGR_MEDIO_X, ENGR_MEDIO_Z), PLANO_MOTOR_B, g)
    # ... y una por cara, que abraza su engranaje mediano Y LAS DOS RUEDAS:
    # asi cada rueda lleva DOS cadenas, una de cada lado
    for py, lado in ((PLANO_RUEDAS_A, "A"), (PLANO_RUEDAS_B, "B")):
        cadena_varios("CADENA_RUEDAS_%s" % lado,
                      [(ENGR_MEDIO_X, ENGR_MEDIO_Z, ENGR_MEDIO_R)] +
                      [(x, WHEEL_Z, CHAIN_R) for x in RUEDA_XS], py, g)


# --------------------------------------------------------------------------
#  MODULOS IMPRIMIBLES
# --------------------------------------------------------------------------
def _pared_con_huecos(p, y, ancho, z0, z1, huecos):
    """Pared normal-Y de ancho `ancho`, menos los rectangulos (cx, w, cz, h)."""
    x0, x1 = -ancho / 2.0, ancho / 2.0
    xs, zs = {x0, x1}, {z0, z1}
    for (cx, w, cz, hh) in huecos:
        xs.update((cx - w / 2.0, cx + w / 2.0))
        zs.update((cz - hh / 2.0, cz + hh / 2.0))
    xs = sorted({min(max(v, x0), x1) for v in xs})
    zs = sorted({min(max(v, z0), z1) for v in zs})
    for a, b in zip(xs, xs[1:]):
        for c, d in zip(zs, zs[1:]):
            if b - a <= 1e-6 or d - c <= 1e-6:
                continue                       # recorte degenerado: sin caja
            mx, mz = (a + b) / 2.0, (c + d) / 2.0
            if any(abs(mx - cx) <= w / 2.0 and abs(mz - cz) <= hh / 2.0
                   for (cx, w, cz, hh) in huecos):
                continue
            p.solid(prim_box(b - a, 4.0, d - c), (mx, y, mz))


def caja_hueca(name, mat, label, z_top, z_bot, group, techo=True,
               trasera=True, huecos_trasera=()):
    """CUADRADO HUECO: suelo + los dos costados + la pared de DETRAS.

    Es la version sencilla de los modulos: una caja vacia por dentro, sin
    paneles, componentes ni cables. Se levantan los DOS COSTADOS (paredes en
    X) y UNA pared, la de detras: la cara de delante queda abierta, de modo
    que se ve el mecanismo por delante y, por detras, como entra el
    rodamiento por el agujero de la pared. `huecos_trasera` = rectangulos
    (cx, ancho, cz, alto) que se restan de esa pared. `techo=False` la deja
    abierta tambien por arriba.
    """
    h = z_top - z_bot
    mid = (z_top + z_bot) / 2.0
    p = part(name, mat, group, label)
    p.solid(prim_box(MOD_W, MOD_D, 4.0), (0.0, 0.0, z_bot + 2.0))     # suelo
    if techo:
        p.solid(prim_box(MOD_W, MOD_D, 4.0), (0.0, 0.0, z_top - 2.0))
    for sx in (-1.0, 1.0):                                           # costados
        p.solid(prim_box(4.0, MOD_D, h), (sx * (MOD_W / 2.0 - 2.0), 0.0, mid))
    if trasera:                                        # pared de detras (Y-)
        _pared_con_huecos(p, -MOD_D / 2.0 + 2.0, MOD_W, z_bot, z_top,
                          huecos_trasera)
    return p


def module_pins(group, z):
    """Pasadores + collarines de interconexion visibles entre modulos."""
    p = part("PINES_UNION_MODULOS_Z%+d" % int(z), "metal_steel", group)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            p.solid(prim_cylinder(3.5, 16.0, 14, 'z'),
                    (sx * (MOD_W / 2.0 - 4.0), sy * 36.0, z))
    return p


def build_modules():
    gA = "MODULE A: CAJA HUECA (SIN TAPA)"
    gB = "MODULE B: CAJA HUECA"
    gC = "MODULE C: CAJA HUECA + 2 MOTORES"
    # Los TRES modulos son CUADRADOS HUECOS: una caja vacia por dentro con
    # solo los palos que salen de ella. Solo llevan UNA pared (la de detras):
    # la cara de delante queda abierta para ver el mecanismo.
    caja_hueca("MODULE_A_CARCASA", "plastic_white",
               "MODULE A: CAJA HUECA (SIN TAPA)",
               MOD_A_Z[1], MOD_A_Z[0], gA, techo=False,   # abierta arriba
               huecos_trasera=[(ENGR_MEDIO_X, 30.0, ENGR_MEDIO_Z, 26.0)])
    caja_hueca("MODULE_B_CARCASA", "plastic_white",
               "MODULE B: CAJA HUECA",
               MOD_B_Z[1], MOD_B_Z[0], gB,
               huecos_trasera=[(ENGR_MEDIO_X, 30.0, -2.5, 5.0)])
    caja_hueca("MODULE_C_CARCASA", "plastic_white",
               "MODULE C: CAJA HUECA + 2 MOTORES",
               MOD_C_Z[1], MOD_C_Z[0], gC,
               huecos_trasera=[(MOTOR_X, 14.0, PINON_Z, 30.0)])
    # DOS motores, cada uno saca su PALO (el eje) por su costado hasta el
    # pinon de su cadena: es la unica pieza de dentro que se conserva.
    for x, signo, lado in ((-MOTOR_X, 1.0, "A"), (MOTOR_X, -1.0, "B")):
        motor = part("MODULE_C_MOTOR_%s" % lado, "metal_dark", gC)
        motor.solid(prim_box(34.0, 34.0, 32.0), (x, signo * -8.0, PINON_Z))
        part("MODULE_C_EJE_MOTOR_%s" % lado, "metal_steel", gC).solid(
            prim_cylinder(4.0, 86.0, 16, 'y'), (x, signo * 52.0, PINON_Z))

    # palos que unen los modulos entre si
    module_pins(gA, 0.0)
    module_pins(gB, -35.0)


# --------------------------------------------------------------------------
#  TENSOR DE CABLE  ->  DESACTIVADO
# --------------------------------------------------------------------------
# Con las DOS ruedas separadas arriba el cable queda apoyado en dos puntos y ya
# no hace falta nada por debajo que lo empuje: este conjunto NO se construye.
# Se conserva aqui entero (y su posicion sigue siendo valida: bajo el cable y a
# x=60, fuera del vano de las ruedas) por si se quisiera volver a poner. Para
# recuperarlo basta CON_TENSOR_INFERIOR = True y anadir su grupo a GROUP_META.
CON_TENSOR_INFERIOR = False
TENSOR_GROUP = "TENSOR DE CABLE (RODILLO + RESORTE)"


def build_tensioner():
    """Rodillo inferior con resorte que empujaba el cable hacia las ruedas."""
    g = TENSOR_GROUP
    part("TENSOR_BRAZO_SOPORTE", "metal_steel", g).solid(
        prim_box(26.0, 24.0, 8.0), (57.0, 0.0, 20.0))
    part("TENSOR_RESORTE", "metal_dark", g).solid(
        prim_spring(5.0, 9.0, 4.5, 1.2, 18, 8), (60.0, 0.0, 27.5))
    part("TENSOR_HORQUILLA", "metal_steel", g).solid(
        prim_box(16.0, 26.0, 6.0), (60.0, 0.0, 34.0))
    roll = part("TENSOR_RODILLO", "rubber_black", g)
    roll.solid(prim_cylinder(10.0, 24.0, 26, 'y'), (60.0, 0.0, 47.0))
    roll.solid(prim_annulus(10.5, 5.0, 26.5, 22, 'y'), (60.0, 0.0, 47.0))


# --------------------------------------------------------------------------
#  exportadores
# --------------------------------------------------------------------------
def write_mtl(path):
    with open(path, "w") as fh:
        fh.write("# robot_modular.mtl\n")
        for name, (kd, d, ns, ks) in MATS.items():
            fh.write("\nnewmtl %s\n" % name)
            fh.write("Ka %.3f %.3f %.3f\n" % (kd[0] * 0.3, kd[1] * 0.3, kd[2] * 0.3))
            fh.write("Kd %.3f %.3f %.3f\n" % kd)
            fh.write("Ks %.3f %.3f %.3f\n" % ks)
            fh.write("Ns %d\n" % ns)
            fh.write("d %.3f\n" % d)
            fh.write("illum 2\n")


def write_obj(path):
    with open(path, "w") as fh:
        fh.write("# robot_modular.obj - generado por generar_robot_modular.py\n")
        fh.write("# unidades: mm\nmtllib robot_modular.mtl\n")
        base = 1
        for p in PARTS:
            fh.write("\no %s\nusemtl %s\n" % (p.name, p.mat))
            for (x, y, z) in p.verts:
                fh.write("v %.4f %.4f %.4f\n" % (x, y, z))
            for face in p.faces:
                fh.write("f " + " ".join(str(i + base) for i in face) + "\n")
            base += len(p.verts)


def part_triangles(parts):
    tris = []
    for p in parts:
        for face in p.faces:
            for t in fan_triangles(face):
                tris.append([p.verts[i] for i in t])
    return tris


def pack_stl(path, tris, header):
    with open(path, "wb") as fh:
        fh.write(header.encode("ascii", "replace")[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<12fH", nx / ln, ny / ln, nz / ln,
                                 a[0], a[1], a[2], b[0], b[1], b[2],
                                 c[0], c[1], c[2], 0))
    return len(tris)


def write_stl(path):
    return pack_stl(path, part_triangles(PARTS),
                    "robot modular cable-rider - generar_robot_modular.py")


def _xml_esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def write_3mf(path):
    """UN solo .3mf con las piezas como OBJETOS SEPARADOS, ya colocados.

    Es la respuesta al problema del STL: el STL no admite varios objetos (por
    eso Tinkercad lo importa como una sola pieza que no se puede separar),
    mientras que el 3MF guarda N objetos con nombre, posicion y color dentro
    de un unico archivo. Lo abren Bambu Studio, PrusaSlicer, Orca, los visores
    3MF y Blender, y en todos ellos cada pieza se borra o mueve por separado.

    Un 3MF es un ZIP con tres entradas: [Content_Types].xml, _rels/.rels y
    3D/3dmodel.model (aqui dentro van vertices, triangulos y el <build>).
    """
    mats = []
    for p in PARTS:
        if p.mat not in mats:
            mats.append(p.mat)
    midx = {m: i for i, m in enumerate(mats)}

    def color(mat):
        rgb, alpha = MATS[mat][0], MATS[mat][1]
        c = "#" + "".join("%02X" % max(0, min(255, int(round(v * 255.0))))
                          for v in rgb)
        if alpha < 1.0:
            c += "%02X" % max(0, min(255, int(round(alpha * 255.0))))
        return c

    x = []
    x.append('<?xml version="1.0" encoding="UTF-8"?>')
    x.append('<model unit="millimeter" xml:lang="es" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">')
    x.append(' <metadata name="Title">ROBOT MODULAR SOBRE CABLE</metadata>')
    x.append(' <resources>')
    x.append('  <basematerials id="1">')
    for m in mats:
        x.append('   <base name="%s" displaycolor="%s"/>'
                 % (_xml_esc(m), color(m)))
    x.append('  </basematerials>')

    ntri = 0
    for i, p in enumerate(PARTS):
        x.append('  <object id="%d" type="model" name="%s" pid="1" pindex="%d">'
                 % (2 + i, _xml_esc(p.name), midx[p.mat]))
        x.append('   <mesh><vertices>')
        for (vx, vy, vz) in p.verts:
            x.append('    <vertex x="%.4f" y="%.4f" z="%.4f"/>' % (vx, vy, vz))
        x.append('   </vertices><triangles>')
        for face in p.faces:
            for (a, b, c) in fan_triangles(face):
                x.append('    <triangle v1="%d" v2="%d" v3="%d"/>' % (a, b, c))
                ntri += 1
        x.append('   </triangles></mesh>')
        x.append('  </object>')

    x.append(' </resources>')
    x.append(' <build>')
    for i in range(len(PARTS)):
        x.append('  <item objectid="%d"/>' % (2 + i))
    x.append(' </build>')
    x.append('</model>')
    model = "\n".join(x)

    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
             'content-types">\n'
             ' <Default Extension="rels" ContentType="application/vnd.'
             'openxmlformats-package.relationships+xml"/>\n'
             ' <Default Extension="model" ContentType="application/vnd.'
             'ms-package.3dmanufacturing-3dmodel+xml"/>\n'
             '</Types>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships">\n'
            ' <Relationship Id="rel0" Target="/3D/3dmodel.model" Type="http://'
            'schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
            '</Relationships>\n')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model.encode("utf-8"))
    return len(PARTS), ntri


# grupo -> (prefijo, nombre de archivo)
GROUP_META = {
    TOP_GROUP: ("T", "CONJUNTO_SUPERIOR"),
    "MODULE A: CAJA HUECA (SIN TAPA)": ("A", "MODULE_A_CAJA"),
    "MODULE B: CAJA HUECA": ("B", "MODULE_B_CAJA"),
    "MODULE C: CAJA HUECA + 2 MOTORES": ("C", "MODULE_C_CAJA"),
    # solo aparece si se vuelve a activar CON_TENSOR_INFERIOR
    "TENSOR DE CABLE (RODILLO + RESORTE)": ("X", "TENSOR_CABLE"),
}
GROUP_PREFIX = {g: v[0] for g, v in GROUP_META.items()}


def bbox(parts):
    xs = [v[0] for p in parts for v in p.verts]
    ys = [v[1] for p in parts for v in p.verts]
    zs = [v[2] for p in parts for v in p.verts]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def write_stl_groups(folder):
    """Un STL por CONJUNTO (4 archivos) + tabla de posiciones para Tinkercad.

    Tinkercad no permite subir varios archivos a la vez y centra cada
    importacion en el origen, asi que cada conjunto viene con la posicion
    exacta (X/Y/Z en mm) que hay que teclear para dejarlo en su sitio.
    """
    os.makedirs(folder, exist_ok=True)
    groups = {}
    for p in PARTS:
        groups.setdefault(p.group, []).append(p)

    ax0, ay0, az0, ax1, ay1, az1 = bbox(PARTS)
    ref = ((ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0, az0)

    rows = []
    for gname, plist in groups.items():
        pref, slug = GROUP_META.get(gname, ("Z", "GRUPO"))
        x0, y0, z0, x1, y1, z1 = bbox(plist)
        fname = "%s_%s.stl" % (pref, slug)
        pack_stl(os.path.join(folder, fname), part_triangles(plist),
                 "%s conjunto %s mm" % (fname, gname))
        # centrado del import -> posicion a teclear en Tinkercad
        pos = ((x0 + x1) / 2.0 - ref[0], (y0 + y1) / 2.0 - ref[1], z0 - ref[2])
        rows.append((fname, len(plist), (x1 - x0, y1 - y0, z1 - z0), pos))

    with open(os.path.join(folder, "POSICIONES.txt"), "w") as fh:
        fh.write("ROBOT MODULAR SOBRE CABLE - %d conjuntos para Tinkercad\n"
                 % len(rows))
        fh.write("=" * 74 + "\n\n")
        fh.write("Tinkercad sube UN archivo por vez y CENTRA cada import en el\n"
                 "origen. Por eso cada conjunto lleva la posicion exacta a la que\n"
                 "hay que llevarlo despues de importarlo:\n\n"
                 "  1) Importar -> Subir el .stl\n"
                 "  2) Seleccionar la pieza y escribir en 'Position':\n"
                 "     X / Y = centro de la pieza, Z = base (elevacion)\n\n")
        fh.write("%-26s %5s %18s %22s\n" % ("archivo", "piezas", "tamano (mm)",
                                            "Position X / Y / Z"))
        fh.write("-" * 74 + "\n")
        for fname, n, size, pos in rows:
            fh.write("%-26s %5d   %5.1f x %5.1f x %5.1f   %8.1f %8.1f %8.1f\n"
                     % (fname, n, size[0], size[1], size[2], pos[0], pos[1], pos[2]))
        fh.write("\nOrden recomendado: T (arriba), luego A, B y por ultimo C.\n"
                 "Si solo quieres editar un modulo, sube ese y listo.\n")
        nshell = sum(p.shells() for p in PARTS)
        fh.write("\nMEJOR OPCION: no uses Tinkercad para esto. Tinkercad solo\n"
                 "acepta STL/OBJ/SVG, no admite 3MF, e importa cualquier malla\n"
                 "como UN solo objeto que NO se puede separar (no hay Ungroup\n"
                 "para una malla importada).\n\n"
                 "En su lugar abre robot_modular.3mf: un solo archivo que SI\n"
                 "lleva las %d piezas como objetos independientes, ya colocados\n"
                 "y con color. Bambu Studio / PrusaSlicer / Orca / Blender lo\n"
                 "abren asi y en todos se borra o mueve una pieza suelta.\n\n"
                 "Alternativa con el STL: robot_modular.stl trae las piezas como\n"
                 "cascaras SEPARADAS (%d en total, porque cada pieza es union de\n"
                 "varias primitivas: la cadena sola son ~100 rodillos y placas).\n"
                 "Cualquier programa con 'separar por partes sueltas' lo\n"
                 "descompone en un clic: Bambu/Orca 'Split to parts' CONSERVA\n"
                 "las posiciones, 'Split to objects' lo reacomoda en la cama\n"
                 "(PrusaSlicer: clic derecho > Split; Blender: Separate by loose\n"
                 "parts; Meshmixer: Separate Shells).\n" % (len(PARTS), nshell))
    return rows


def write_stl_parts(folder, escala=1.0):
    """Un STL por pieza: en Tinkercad importas solo lo que quieras editar."""
    os.makedirs(folder, exist_ok=True)
    rows = []
    for p in PARTS:
        pref = GROUP_PREFIX.get(p.group, "Z")
        fname = "%s_%s.stl" % (pref, p.name)
        n = pack_stl(os.path.join(folder, fname), part_triangles([p]),
                     "%s (%s) mm" % (p.name, p.mat))
        rows.append((fname, p.label or p.group, p.tri_count(), p.volume()))
    with open(os.path.join(folder, "INDICE.txt"), "w") as fh:
        fh.write("ROBOT MODULAR SOBRE CABLE - indice de piezas (%d)\n" % len(rows))
        fh.write("Medidas reales en milimetros. OJO: Tinkercad centra cada import\n"
                 "en el origen, asi que si cargas varias aparecen superpuestas:\n"
                 "muevelas para componer el robot (o usa robot_modular.obj en Blender,\n"
                 "que mantiene las piezas como objetos separados ya colocados).\n"
                 "T=conjunto superior, A/B/C=modulos\n\n")
        for fname, label, nt, vol in sorted(rows):
            fh.write("%-36s tris=%-6d vol=%9.0f mm3   %s\n" % (fname, nt, vol, label))
    return rows


LABELS = [
    ("2 ENGRANAJES MEDIOS (UNO POR CARA, PEGADOS A LA CAJA)", (0.0, 0.0, 30.0)),
    ("BARRA QUE UNE LOS 2 EJES MEDIANOS", (0.0, 22.0, ENGR_MEDIO_Z + 8.0)),
    ("MODULE A: CAJA HUECA (SIN TAPA)", (0.0, 45.0, 30.0)),
    ("MODULE B: CAJA HUECA", (0.0, 45.0, -18.0)),
    ("MODULE C: CAJA HUECA + 2 MOTORES", (0.0, 45.0, -62.0)),
    ("DOS RUEDAS DE TRACCION", (-VANO, 0.0, 130.0)),
    ("4 CADENAS: 2 MOTORES -> 2 MEDIANOS -> RUEDAS", (-MOTOR_X, PLANO_MOTOR_A, -20.0)),
    ("CABLE METALICO", (140.0, 0.0, CABLE_Z)),
]


def write_preview(path):
    """Previsualizacion interactiva: datos embebidos + canvas 2D."""
    verts, tris, cols = [], [], []
    index = {}
    mat_list = list(MATS.keys())
    for p in PARTS:
        ci = mat_list.index(p.mat)
        for face in p.faces:
            for t in fan_triangles(face):
                tri = []
                for i in t:
                    v = p.verts[i]
                    key = (round(v[0], 2), round(v[1], 2), round(v[2], 2))
                    if key not in index:
                        index[key] = len(verts)
                        verts.append([key[0], key[1], key[2]])
                    tri.append(index[key])
                tris.append(tri)
                cols.append(ci)

    colors = []
    for name in mat_list:
        kd = MATS[name][0]
        colors.append("#%02x%02x%02x" % tuple(int(round(c * 255)) for c in kd))
    alphas = [MATS[n][1] for n in mat_list]
    data = {"V": [c for v in verts for c in v], "T": [i for t in tris for i in t],
            "C": cols, "col": colors, "alpha": alphas, "L": LABELS}
    html = PREVIEW_TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    with open(path, "w") as fh:
        fh.write(html)
    return len(verts), len(tris), os.path.getsize(path)


PREVIEW_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Robot modular sobre cable - vista previa 3D</title>
<style>
 html,body{margin:0;height:100%;background:#3a3d42;overflow:hidden;
   font:12px/1.4 system-ui,Segoe UI,Roboto,sans-serif;color:#eee}
 #cv{display:block;width:100%;height:100%;cursor:grab}
 #hud{position:fixed;left:12px;top:10px;background:rgba(18,20,24,.72);
   padding:10px 14px;border-radius:8px;max-width:330px;backdrop-filter:blur(4px)}
 #hud b{color:#7fd1ff}
 #hud small{opacity:.75}
 #lab{position:fixed;inset:0;pointer-events:none}
 .lb{position:absolute;transform:translate(-50%,-50%);background:rgba(14,16,20,.78);
   border:1px solid #7fd1ff55;color:#dff2ff;padding:2px 7px;border-radius:5px;
   font-size:11px;white-space:nowrap}
</style></head><body>
<canvas id="cv"></canvas><div id="lab"></div>
<div id="hud"><b>ROBOT MODULAR SOBRE CABLE</b><br>
<small>arrastra = rotar &middot; rueda = zoom &middot; doble clic = reset<br>
<span id="st"></span></small></div>
<script>
const D=__DATA__;
const V=new Float32Array(D.V), T=new Uint32Array(D.T), C=D.C;
const cv=document.getElementById('cv'), g=cv.getContext('2d');
const lab=document.getElementById('lab');
let yaw=-2.25, pit=0.22, zoom=1, drag=false, lx=0, ly=0;
function fit(){ const d=devicePixelRatio||1;
  cv.width=Math.max(1,Math.round(innerWidth*d)); cv.height=Math.max(1,Math.round(innerHeight*d));
  g.setTransform(d,0,0,d,0,0); }
addEventListener('resize',()=>{fit();draw();});
if(window.ResizeObserver) new ResizeObserver(()=>{fit();draw();}).observe(document.body);
let cx=0,cy=0,cz=0,nv=V.length/3;
for(let i=0;i<nv*3;i+=3){cx+=V[i];cy+=V[i+1];cz+=V[i+2];}
cx/=nv;cy/=nv;cz/=nv;
const dists=[];
for(let i=0;i<nv*3;i+=3) dists.push(Math.hypot(V[i]-cx,V[i+1]-cy,V[i+2]-cz));
dists.sort((a,b)=>a-b);
let R=Math.max(dists[Math.floor(dists.length*0.85)]*1.15, dists[dists.length-1]*0.32);
document.getElementById('st').textContent=nv+' vertices / '+(T.length/3)+' triangulos';
cv.addEventListener('mousedown',e=>{drag=true;lx=e.clientX;ly=e.clientY;cv.style.cursor='grabbing';});
addEventListener('mouseup',()=>{drag=false;cv.style.cursor='grab';});
addEventListener('mousemove',e=>{ if(!drag)return;
  yaw+=(e.clientX-lx)*0.008; pit=Math.max(-1.35,Math.min(1.35,pit+(e.clientY-ly)*0.008));
  lx=e.clientX;ly=e.clientY; draw(); });
cv.addEventListener('wheel',e=>{e.preventDefault();
  zoom=Math.max(0.35,Math.min(3.5,zoom*(e.deltaY>0?0.9:1.11))); draw();},{passive:false});
cv.addEventListener('dblclick',()=>{yaw=-2.25;pit=0.22;zoom=1;draw();});
const L=[[0.45,0.55,0.72],[0.75,-0.3,0.35],[-0.4,0.2,-0.5]];
function draw(){
 const dpr=devicePixelRatio||1;
 if(cv.width!==Math.round(innerWidth*dpr)||cv.height!==Math.round(innerHeight*dpr)) fit();
 const W=innerWidth,H=innerHeight;
 const bg=g.createRadialGradient(W*0.45,H*0.38,40,W*0.5,H*0.5,Math.max(W,H)*0.85);
 bg.addColorStop(0,'#54585f'); bg.addColorStop(1,'#2c2f34');
 g.fillStyle=bg; g.fillRect(0,0,W,H);
 const ca=Math.cos(yaw),sa=Math.sin(yaw),cp=Math.cos(pit),sp=Math.sin(pit);
 const RV=[ca,sa,0], UV=[-sa*sp,ca*sp,cp], FV=[-sa*cp,ca*cp,-sp];
 const sc=Math.min(W,H)/(2.95*R)*zoom, DCAM=3.1*R;
 const pr=new Float32Array(nv*3), pz=new Float32Array(nv);
 for(let i=0;i<nv*3;i+=3){
   const x=V[i]-cx,y=V[i+1]-cy,z=V[i+2]-cz;
   const sx3=x*RV[0]+y*RV[1], sy3=x*UV[0]+y*UV[1]+z*UV[2];
   const dv=x*FV[0]+y*FV[1]+z*FV[2];
   const p=DCAM/(DCAM+dv);
   pr[i]=W/2+sx3*sc*p; pr[i+1]=H/2-sy3*sc*p; pr[i+2]=dv; pz[i/3]=dv;
 }
 const nt=T.length/3, order=new Array(nt);
 const dep=new Float32Array(nt);
 for(let i=0;i<nt;i++){const a=T[i*3],b=T[i*3+1],c=T[i*3+2];
   dep[i]=(pz[a]+pz[b]+pz[c])/3; order[i]=i;}
 order.sort((i,j)=>dep[j]-dep[i]);
 for(const i of order){
  const a=T[i*3],b=T[i*3+1],c=T[i*3+2];
  const e1=[V[b*3]-V[a*3],V[b*3+1]-V[a*3+1],V[b*3+2]-V[a*3+2]];
  const e2=[V[c*3]-V[a*3],V[c*3+1]-V[a*3+1],V[c*3+2]-V[a*3+2]];
  let n=[e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]];
  const nl=Math.hypot(n[0],n[1],n[2])||1; n=[n[0]/nl,n[1]/nl,n[2]/nl];
  if(n[0]*FV[0]+n[1]*FV[1]+n[2]*FV[2]>=0) continue;
  const ax=pr[a*3],ay=pr[a*3+1],bx=pr[b*3],by=pr[b*3+1],dx2=pr[c*3],dy2=pr[c*3+1];
  let sh=0.34;
  for(const l of L){const d=Math.max(0,n[0]*l[0]+n[1]*l[1]+n[2]*l[2])*0.85;
    sh+=Math.max(0,d)*0.34;}
  const col=D.col[C[i]];
  g.globalAlpha=D.alpha[C[i]];
  g.fillStyle=shade(col,Math.min(1.45,sh));
  g.beginPath();g.moveTo(ax,ay);g.lineTo(bx,by);g.lineTo(dx2,dy2);g.closePath();
  g.fill(); g.globalAlpha=1;
 }
 const pts=[];
 for(const [txt,p] of D.L){
  const x=p[0]-cx,y=p[1]-cy,z=p[2]-cz;
  const sx3=x*RV[0]+y*RV[1], sy3=x*UV[0]+y*UV[1]+z*UV[2];
  const dv=x*FV[0]+y*FV[1]+z*FV[2];
  const pp=DCAM/(DCAM+dv);
  const sx=W/2+sx3*sc*pp, sy=H/2-sy3*sc*pp;
  let dxs=sx-W/2, dys=sy-H/2; const dl=Math.hypot(dxs,dys)||1;
  pts.push({t:txt,ax:sx,ay:sy,x:sx+dxs/dl*80,y:sy+dys/dl*80+16,z:dv});
 }
 pts.sort((a,b)=>a.y-b.y);
 for(let i=1;i<pts.length;i++) if(pts[i].y-pts[i-1].y<22) pts[i].y=pts[i-1].y+22;
 for(const p of pts){ p.y=Math.max(14,Math.min(H-14,p.y));
   p.x=Math.max(96,Math.min(W-96,p.x)); }
 g.lineWidth=1;
 for(const p of pts){ g.strokeStyle='rgba(127,209,255,.40)';
  g.beginPath(); g.moveTo(p.ax,p.ay); g.lineTo(p.x,p.y); g.stroke();
  g.fillStyle='#7fd1ff'; g.beginPath(); g.arc(p.ax,p.ay,2,0,6.3); g.fill(); }
 lab.innerHTML='';
 for(const p of pts){
  const e=document.createElement('div'); e.className='lb';
  e.style.left=p.x+'px'; e.style.top=p.y+'px'; e.textContent=p.t;
  e.style.opacity=p.z<0?1:0.72; lab.appendChild(e);
 }
}
function shade(hex,m){const r=parseInt(hex.substr(1,2),16),g2=parseInt(hex.substr(3,2),16),
 b=parseInt(hex.substr(5,2),16);
 return 'rgb('+Math.min(255,r*m|0)+','+Math.min(255,g2*m|0)+','+Math.min(255,b*m|0)+')';}
draw();
</script></body></html>
"""


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Genera el robot modular sobre cable")
    ap.add_argument("--stl", action="store_true",
                    help="exportar robot_modular.stl + carpeta stl_piezas/ (una pieza por archivo)")
    ap.add_argument("--sin-piezas", action="store_true",
                    help="con --stl: no generar la carpeta stl_piezas/")
    ap.add_argument("--3mf", dest="m3mf", action="store_true",
                    help="exportar robot_modular.3mf (piezas separadas y colocadas)")
    ap.add_argument("--escala", type=float, default=1.0, help="factor de escala")
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    build_top()
    build_modules()
    if CON_TENSOR_INFERIOR:
        build_tensioner()

    if args.escala != 1.0:
        s = args.escala
        for p in PARTS:
            p.verts = [(v[0] * s, v[1] * s, v[2] * s) for v in p.verts]

    out = args.dir
    obj = os.path.join(out, "robot_modular.obj")
    mtl = os.path.join(out, "robot_modular.mtl")
    prev = os.path.join(out, "robot_modular_preview.html")
    write_mtl(mtl)
    write_obj(obj)
    nv, ntri, hsize = write_preview(prev)

    bad = [p.name for p in PARTS if p.edges_ok() != 0]
    neg = [p.name for p in PARTS if p.volume() <= 0.0]
    groups = {}
    for p in PARTS:
        groups.setdefault(p.group, []).append(p)

    print("=" * 78)
    print("ROBOT MODULAR SOBRE CABLE  -  %d piezas / %d grupos" % (len(PARTS), len(groups)))
    print("=" * 78)
    for gname in groups:
        print("\n[%s]" % gname)
        for p in groups[gname]:
            print("   %-34s %-14s %6d tris  vol=%9.1f mm3  %s"
                  % (p.name, p.mat, p.tri_count(), p.volume(),
                     "OK" if (p.edges_ok() == 0 and p.volume() > 0) else "REVISAR"))

    xs = [v[0] for p in PARTS for v in p.verts]
    ys = [v[1] for p in PARTS for v in p.verts]
    zs = [v[2] for p in PARTS for v in p.verts]
    print("\n%-34s %s" % ("Bounding box (mm)", "X %.0f..%.0f  Y %.0f..%.0f  Z %.0f..%.0f"
                          % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))))
    print("%-34s %d piezas, %d triangulos" % ("Malla total", len(PARTS),
                                              sum(p.tri_count() for p in PARTS)))
    print("%-34s %d" % ("Cascaras sueltas en el STL",
                        sum(p.shells() for p in PARTS)))
    print("%-34s %s" % ("Aristas mal emparejadas", "0 (estanco)" if not bad else bad))
    print("%-34s %s" % ("Volumen negativo (normales)", "0 (correcto)" if not neg else neg))

    if args.m3mf or args.stl:
        m = os.path.join(out, "robot_modular.3mf")
        n3o, n3t = write_3mf(m)
        print("\n3MF piezas separadas: %s  (%d objetos, %d triangulos, %.0f KB)"
              % (m, n3o, n3t, os.path.getsize(m) / 1024.0))
        print("  Un solo archivo con las %d piezas como OBJETOS INDEPENDIENTES,"
              % n3o)
        print("  con nombre, posicion y color, ya montados. Aqui SI se puede")
        print("  borrar o mover una pieza sola.")
        print("  Lo abren: Bambu Studio / PrusaSlicer / Orca (arrastrar el .3mf),")
        print("  Blender (importador 3MF) y los visores 3MF online gratuitos.")

    if args.stl:
        stl = os.path.join(out, "robot_modular.stl")
        n = write_stl(stl)
        print("\nSTL ensamblaje: %s  (%d triangulos, %.0f KB)"
              % (stl, n, os.path.getsize(stl) / 1024.0))
        gfolder = os.path.join(out, "stl_grupos")
        grows = write_stl_groups(gfolder)
        print("STL conjuntos:  %s  (%d archivos + POSICIONES.txt)"
              % (gfolder, len(grows)))
        print("\n  Tinkercad sube un archivo por vez y centra cada import, "
              "asi que tras\n  importar cada conjunto hay que teclear su "
              "posicion (mm):")
        print("  %-26s %8s %8s %8s" % ("archivo", "Pos X", "Pos Y", "Pos Z"))
        for fname, _n, _size, pos in grows:
            print("  %-26s %8.1f %8.1f %8.1f" % (fname, pos[0], pos[1], pos[2]))
        if not args.sin_piezas:
            folder = os.path.join(out, "stl_piezas")
            rows = write_stl_parts(folder)
            print("\nSTL por piezas: %s  (%d archivos + INDICE.txt)" % (folder, len(rows)))
        print("\n     -> IMPRIMIR: robot_modular.stl")
        print("     -> TINKERCAD, editar un modulo: los 5 de stl_grupos/ + POSICIONES.txt")
        print("     -> SIN SUBIR NADA: robot_modular.stl + 'separar por partes sueltas'")
        print("        (PrusaSlicer/Bambu: Split to objects | Blender: Separate by")
        print("         loose parts | Meshmixer: Separate Shells) -> %d cascaras en un clic"
              % sum(p.shells() for p in PARTS))
        print("     -> BLENDER: robot_modular.obj ya entra con las %d piezas separadas"
              % len(PARTS))

    print("\nEDITOR EN EL NAVEGADOR: python3 editor_web.py  ->  editor_web.html")
    print("   Abre el ensamblaje y permite BORRAR, AISLAR, DUPLICAR y RECOLOCAR")
    print("   cada pieza, exportando a 3MF / OBJ / STL. Sin instalar nada y sin")

    print("   conexion: three.js y las piezas van incrustados en el archivo.")

    print("\nOBJ: %s\nMTL: %s\nPREVIEW: %s  (%.0f KB, %d verts, %d tris)"
          % (obj, mtl, prev, hsize / 1024.0, nv, ntri))
    print("\nBlender: File > Import > Wavefront (.obj)  -> materiales incluidos")
    print("Render fotorrealista: abre render_robot_blender.py dentro de Blender "
          "(Scripting > Run)")

    if bad or neg:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
