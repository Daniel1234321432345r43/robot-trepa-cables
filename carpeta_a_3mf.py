#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARPETA DE STLs  ->  UN SOLO .3mf CON PIEZAS INDIVIDUALES Y COLOCADAS

Este script existe porque el STL no puede guardar varias piezas: por eso,
cuando subes un STL a Tinkercad, entra como UNA sola pieza que no se puede
separar ni borrar por partes. El formato 3MF si guarda N objetos, cada uno
con su nombre, su posicion y su color, dentro de un unico archivo.

Entrada:  una carpeta con archivos .stl (por ejemplo stl_piezas/ o stl_grupos/).
          Las coordenadas de cada STL se respetan tal cual, asi que si los
          STLs ya venian montados el ensamblaje sale en su sitio exacto.
Salida:   un .3mf que se abre en Bambu Studio, PrusaSlicer, Orca Slicer,
          los visores 3MF online y Blender, con cada pieza como objeto aparte
          (se puede borrar, mover o editar una sin tocar las demas).

Uso:
    python3 carpeta_a_3mf.py stl_piezas
    python3 carpeta_a_3mf.py stl_piezas robot_completo.3mf
    python3 carpeta_a_3mf.py --comprobar robot_completo.3mf
"""

import argparse
import math
import os
import struct
import sys
import zipfile

# Colores distinguibles (sRGB) para que las piezas no salgan todas del mismo tono
PALETA = [
    "#E8E8E4", "#2B2B30", "#B8433A", "#3C6FB5", "#D9A62E", "#3F8F5B",
    "#8E5BB5", "#C87A3C", "#5AA9C4", "#9A9A9E", "#7A4B2A", "#D0D0CC",
]

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


# --------------------------------------------------------------------------
#  Lectura de STL (binario y ASCII)
# --------------------------------------------------------------------------
def leer_stl(path):
    """Devuelve (verts, tris) de un STL binario o ASCII, en sus coordenadas."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) < 84:
        raise ValueError("archivo demasiado corto")

    # Binario: cabecera 80 bytes + uint32 n + n * 50 bytes. Si el tamano cuadra
    # exacto es binario (un STL ASCII no puede cuadrar por casualidad con esto).
    if len(blob) >= 84:
        n = struct.unpack("<I", blob[80:84])[0]
        if 84 + n * 50 == len(blob):
            verts, tris = [], []
            for i in range(n):
                rec = 84 + i * 50
                f = struct.unpack("<12f", blob[rec:rec + 48])
                base = len(verts)
                verts.extend([(f[3], f[4], f[5]), (f[6], f[7], f[8]),
                              (f[9], f[10], f[11])])
                tris.append((base, base + 1, base + 2))
            return verts, tris

    # ASCII
    texto = blob.decode("utf-8", "replace")
    if "facet" not in texto:
        raise ValueError("no parece un STL (ni binario ni ASCII)")
    verts, tris = [], []
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith("vertex"):
            p = s.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
    # en ASCII los vertices llegan en grupos de 3, uno por triangulo
    if len(verts) % 3:
        raise ValueError("vertices ASCII incompletos")
    for i in range(0, len(verts), 3):
        tris.append((i, i + 1, i + 2))
    return verts, tris


# --------------------------------------------------------------------------
#  Escritura de 3MF
# --------------------------------------------------------------------------
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def escribir_3mf(path, objetos):
    """objetos: lista de (nombre, color, verts, tris)."""
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<model unit="millimeter" xml:lang="es" xmlns="%s">' % NS,
         ' <metadata name="Title">%s</metadata>'
         % esc(os.path.splitext(os.path.basename(path))[0]),
         ' <resources>',
         '  <basematerials id="1">']
    for _nombre, color, _v, _t in objetos:
        x.append('   <base name="%s" displaycolor="%s"/>' % (esc(_nombre), color))
    x.append('  </basematerials>')

    for i, (nombre, _color, verts, tris) in enumerate(objetos):
        x.append('  <object id="%d" type="model" name="%s" pid="1" pindex="%d">'
                 % (2 + i, esc(nombre), i))
        x.append('   <mesh><vertices>')
        for (vx, vy, vz) in verts:
            x.append('    <vertex x="%.4f" y="%.4f" z="%.4f"/>' % (vx, vy, vz))
        x.append('   </vertices><triangles>')
        for (a, b, c) in tris:
            x.append('    <triangle v1="%d" v2="%d" v3="%d"/>' % (a, b, c))
        x.append('   </triangles></mesh>')
        x.append('  </object>')

    x.append(' </resources>')
    x.append(' <build>')
    for i in range(len(objetos)):
        x.append('  <item objectid="%d"/>' % (2 + i))
    x.append(' </build>')
    x.append('</model>')

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
        z.writestr("3D/3dmodel.model", "\n".join(x).encode("utf-8"))


def bbox(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def comprobar(path):
    """Valida el .3mf leyendolo como lo haria un slicer."""
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(path)
    faltan = [n for n in ("[Content_Types].xml", "_rels/.rels",
                          "3D/3dmodel.model") if n not in z.namelist()]
    if faltan:
        print("   FALTAN entradas obligatorias: %s" % faltan)
        return 1
    if z.testzip() is not None:
        print("   ZIP CORRUPTO")
        return 1
    nx = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
    r = ET.fromstring(z.read("3D/3dmodel.model"))
    objs = r.find(nx + "resources").findall(nx + "object")
    items = r.find(nx + "build").findall(nx + "item")
    ids = {int(o.get("id")) for o in objs}
    ok = (r.get("unit") == "millimeter"
          and len(objs) == len(items)
          and len(items) == len({i.get("objectid") for i in items})
          and {int(i.get("objectid")) for i in items} <= ids
          and min(ids) > 0)
    print("   unidad=%s  objetos=%d  items=%d  referencias OK=%s"
          % (r.get("unit"), len(objs), len(items), ok))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="Une una carpeta de STLs en un solo 3MF con piezas separadas")
    ap.add_argument("carpeta", help="carpeta con archivos .stl")
    ap.add_argument("salida", nargs="?", help="nombre del .3mf de salida")
    ap.add_argument("--comprobar", action="store_true",
                    help="si 'carpeta' es un .3mf: validarlo y salir")
    args = ap.parse_args()

    if args.comprobar:
        print("Comprobando %s" % args.carpeta)
        return comprobar(args.carpeta)

    if not os.path.isdir(args.carpeta):
        print("ERROR: '%s' no es una carpeta." % args.carpeta)
        return 1
    archivos = sorted(f for f in os.listdir(args.carpeta)
                      if f.lower().endswith(".stl"))
    if not archivos:
        print("ERROR: no hay ningun .stl en '%s'." % args.carpeta)
        return 1

    objetos = []
    for i, f in enumerate(archivos):
        try:
            verts, tris = leer_stl(os.path.join(args.carpeta, f))
        except ValueError as e:
            print("   saltado %-40s (%s)" % (f, e))
            continue
        objetos.append((os.path.splitext(f)[0], PALETA[i % len(PALETA)],
                        verts, tris))

    salida = args.salida or (os.path.basename(os.path.abspath(args.carpeta)) + ".3mf")
    escribir_3mf(salida, objetos)

    print("=" * 78)
    print("CARPETA -> 3MF")
    print("=" * 78)
    print("entrada:  %s  (%d archivos)" % (args.carpeta, len(archivos)))
    print("salida:   %s  (%d objetos, %.0f KB)"
          % (salida, len(objetos), os.path.getsize(salida) / 1024.0))
    print("\n%-42s %6s %9s  %s" % ("objeto", "tris", "verts", "centro X/Y/Z (mm)"))
    print("-" * 78)
    todos = []
    for nombre, _c, verts, tris in objetos:
        x0, y0, z0, x1, y1, z1 = bbox(verts)
        todos.extend(verts)
        print("%-42s %6d %9d  %8.1f %8.1f %8.1f"
              % (nombre, len(tris), len(verts),
                 (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    x0, y0, z0, x1, y1, z1 = bbox(todos)
    print("-" * 78)
    print("ensamblaje: X %.0f..%.0f  Y %.0f..%.0f  Z %.0f..%.0f mm"
          % (x0, x1, y0, y1, z0, z1))
    print("\nCada pieza conserva las coordenadas de su STL, asi que el conjunto")
    print("sale montado sin recolocar nada. Si un STL venia centrado en el")
    print("origen (no es el caso de stl_piezas/ ni de stl_grupos/), esa pieza")
    print("aparecera en el centro: muevela una vez y listo.")
    print("\nAbrir con: Bambu Studio / PrusaSlicer / Orca (arrastrar el .3mf)")
    print("           Blender (importador 3MF) | visores 3MF online gratuitos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
