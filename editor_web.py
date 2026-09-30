#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDITOR WEB LOCAL  ->  editor_web.html

Genera una herramienta de un solo archivo (sin servidor, sin internet, sin
instalar nada) para abrir el ensamblaje y BORRAR, AISLAR, DUPLICAR o RECOLOCAR
sus piezas desde el navegador, exportando el resultado en 3MF, OBJ o STL.

Como se construye:
  1. reutiliza el generador: importa generar_robot_modular y llama a sus
     funciones de construccion, de modo que las piezas son EXACTAMENTE las
     mismas que las del .obj / .3mf (una sola fuente de verdad);
  2. serializa las piezas (vertices, triangulos, color, material) a JSON;
  3. incrusta three.js (build UMD, define el global THREE) dentro del HTML,
     asi que el archivo funciona incluso sin conexion.

Uso:
    python3 editor_web.py
    python3 editor_web.py --salida otro.html
"""

import argparse
import datetime
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import generar_robot_modular as G   # noqa: E402  (necesita el sys.path de arriba)

# materiales que se comportan como metal en el visor (heuristica a partir del
# brillo/color especular definidos en el generador, no de un dato inventado)
METALES = {"metal_steel", "metal_dark", "copper"}


def apariencia(nombre_mat):
    """Devuelve (metalico, rugosidad) a partir del brillo Ns del material."""
    kd, alfa, ns, ks = G.MATS[nombre_mat]
    if nombre_mat in METALES:
        return round(min(0.95, 0.55 + ns / 500.0), 3), round(max(0.08, 1.0 - ns / 400.0), 3)
    return 0.0, round(min(0.95, max(0.12, 1.0 - ns / 500.0)), 3)


def hexagonal(color):
    return "#" + "".join("%02X" % max(0, min(255, int(round(c * 255)))) for c in color)


def centro(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return [round((min(xs) + max(xs)) / 2.0, 3),
            round((min(ys) + max(ys)) / 2.0, 3),
            round((min(zs) + max(zs)) / 2.0, 3)]


def construir_datos():
    G.build_top()
    G.build_modules()

    prefijo = G.GROUP_PREFIX
    partes, tris_total = [], 0
    for p in G.PARTS:
        planos = [round(c, 3) for v in p.verts for c in v]
        tri = []
        for cara in p.faces:
            for t in G.fan_triangles(cara):
                tri.extend(t)
        tris_total += len(tri) // 3
        metal, rug = apariencia(p.mat)
        partes.append({
            "n": p.name,                        # nombre de la pieza
            "g": p.group,                       # grupo completo
            "p": prefijo.get(p.group, "Z"),     # prefijo/letra del grupo
            "m": p.mat,                         # material
            "c": hexagonal(G.MATS[p.mat][0]),   # color
            "a": G.MATS[p.mat][1],              # alfa
            "metal": metal, "rug": rug,
            "v": planos, "t": tri,
            "k": centro(p.verts),               # centro (pivote de giro)
        })

    orden = list(G.GROUP_META.keys())
    for g in partes:
        if g["g"] not in orden:
            orden.append(g["g"])
    grupos = [{"g": g, "p": prefijo.get(g, "Z"), "slug": G.GROUP_META.get(g, ("Z", "OTROS"))[1]}
              for g in orden if any(x["g"] == g for x in partes)]

    xs = [v[0] for p in G.PARTS for v in p.verts]
    ys = [v[1] for p in G.PARTS for v in p.verts]
    zs = [v[2] for p in G.PARTS for v in p.verts]
    return {
        "meta": {"piezas": len(partes), "tris": tris_total, "unidad": "mm",
                 "bbox": [round(min(xs), 2), round(min(ys), 2), round(min(zs), 2),
                          round(max(xs), 2), round(max(ys), 2), round(max(zs), 2)]},
        "grupos": grupos,
        "partes": partes,
        "etiquetas": [[t, list(pt)] for t, pt in G.LABELS],
    }


def main():
    ap = argparse.ArgumentParser(description="Genera el editor web local del ensamblaje")
    ap.add_argument("--salida", default=os.path.join(AQUI, "editor_web.html"))
    ap.add_argument("--plantilla", default=os.path.join(AQUI, "editor_web_template.html"))
    ap.add_argument("--three", default=os.path.join(AQUI, "vendor", "three-0.149.0.min.js"))
    args = ap.parse_args()

    for ruta in (args.plantilla, args.three):
        if not os.path.exists(ruta):
            print("ERROR: falta %s" % ruta)
            if ruta == args.three:
                print("       descargalo con:")
                print("       curl -o vendor/three-0.149.0.min.js \\")
                print("         https://unpkg.com/three@0.149.0/build/three.min.js")
            return 1

    with open(args.plantilla, encoding="utf-8") as fh:
        html = fh.read()
    with open(args.three, encoding="utf-8") as fh:
        three = fh.read()

    for marca in ("/*@@THREE@@*/", "/*@@DATOS@@*/", "@@SELLO@@"):
        if marca not in html:
            print("ERROR: la plantilla no contiene %s" % marca)
            return 1

    # un "</script" dentro del codigo incrustado cerraria la etiqueta antes de
    # tiempo: se escapa como "<\/script" (identico en JavaScript)
    cierres = three.count("</script")
    if cierres:
        three = three.replace("</script", "<\\/script")

    datos = construir_datos()
    json_txt = json.dumps(datos, separators=(",", ":"), ensure_ascii=False)

    # Sello de compilación (fecha y hora): va en el título de la pestaña y en una
    # pastilla de la cabecera. Es la forma de saber si el navegador está mostrando
    # el archivo recién generado o una copia cacheada.
    sello = datetime.datetime.now().strftime("%d/%m %H:%M")
    html = (html.replace("/*@@THREE@@*/", three)
                .replace("/*@@DATOS@@*/", json_txt)
                .replace("@@SELLO@@", sello))
    with open(args.salida, "w", encoding="utf-8") as fh:
        fh.write(html)

    # ---- comprobaciones: no publicar algo roto -------------------------
    problemas = []
    for marca in ("/*@@DATOS@@*/", "/*@@THREE@@*/", "@@SELLO@@"):
        if marca in html:
            problemas.append("quedo el marcador %s sin sustituir" % marca)
    if "window.__THREE__" not in html and "WebGLRenderer" not in html:
        problemas.append("three.js no parece estar dentro del archivo")
    for obligatorio in ("WebGLRenderer", "construirOBJ", "construirSTL", "construir3MF",
                        "zipGuardado", "crc32", "MeshStandardMaterial"):
        if obligatorio not in html:
            problemas.append("falta la funcion %s en el HTML generado" % obligatorio)
    externos = [m for m in ('src="http', "href=\"http", "src='http") if m in html]
    if externos:
        problemas.append("hay referencias externas: %s" % externos)
    if "\ufffd" in html:
        problemas.append("el archivo contiene caracteres mal codificados")
    ida = json.loads(json_txt)
    if len(ida["partes"]) != datos["meta"]["piezas"]:
        problemas.append("el JSON no se puede releer igual")

    kb = os.path.getsize(args.salida) / 1024.0
    print("=" * 74)
    print("EDITOR WEB: %s" % args.salida)
    print("=" * 74)
    print("  piezas.................. %d" % datos["meta"]["piezas"])
    print("  triangulos.............. %d" % datos["meta"]["tris"])
    print("  grupos.................. %s"
          % ", ".join("%s=%s" % (g["p"], g["slug"][:18]) for g in datos["grupos"]))
    print("  etiquetas............... %d" % len(datos["etiquetas"]))
    print("  datos del modelo........ %.0f KB" % (len(json_txt) / 1024.0))
    print("  three.js incrustado..... %.0f KB%s"
          % (len(three) / 1024.0, "  (%d cierres de script escapados)" % cierres
             if cierres else ""))
    print("  sello de compilacion.... %s" % sello)
    print("  tamano final............ %.0f KB" % kb)
    print("  autocontenido........... %s" % ("si: sin CDN, sin servidor, "
          "funciona abriendo el archivo" if not externos
          else "NO: %s" % externos))
    print("  avisos.................. %s" % ("ninguno" if not problemas else problemas))
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
