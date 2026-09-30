#!/usr/bin/env python3
"""
Generador de piezas 3D paramétricas -> STL (imprimible en 3D / editable en Blender / importable en Tinkercad)

Demo: tuerca hexagonal métrica (norma DIN 934 aproximada).
Sin dependencias externas: solo la librería estándar de Python.
Uso:  python3 generar_tuerca.py                 (tuerca M8)
      python3 generar_tuerca.py --medida M10
"""

import math
import struct
import argparse

# ---------------- Parámetros paramétricos (mm) ----------------
def parametros(medida: str) -> dict:
    """Dimensiones estándar aproximadas para tuercas hexagonales DIN 934."""
    tabla = {
        "M4":  {"llave": 7.0,  "altura": 3.2},
        "M6":  {"llave": 10.0, "altura": 5.0},
        "M8":  {"llave": 13.0, "altura": 6.5},
        "M10": {"llave": 17.0, "altura": 8.0},
        "M12": {"llave": 19.0, "altura": 10.0},
    }
    d = float(medida[1:])
    return {
        "d_nominal": d + 0.2,          # holgura de impresión (sin roscar: calza roscando)
        "s_llave":   tabla[medida]["llave"] + 0.3,  # holgura en llave fija
        "h_altura":  tabla[medida]["altura"],
        "n_lados":   6,
    }

# ---------------- Geometría: malla de triángulos ----------------
class Malla:
    def __init__(self):
        self.verts = []
        self.tris = []

    def agregar_vert(self, x, y, z):
        self.verts.append((x, y, z))
        return len(self.verts) - 1

    def agregar_tri(self, a, b, c):
        self.tris.append((a, b, c))

    def exportar_stl(self, ruta, nombre="pieza"):
        with open(ruta, "wb") as f:
            f.write(nombre.encode().ljust(80, b"\0")[:80])
            f.write(struct.pack("<I", len(self.tris)))
            for a, b, c in self.tris:
                va, vb, vc = self.verts[a], self.verts[b], self.verts[c]
                u = [vb[i] - va[i] for i in range(3)]
                v = [vc[i] - va[i] for i in range(3)]
                n = (u[1] * v[2] - u[2] * v[1],
                     u[2] * v[0] - u[0] * v[2],
                     u[0] * v[1] - u[1] * v[0])
                mod = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
                f.write(struct.pack("<3f", n[0] / mod, n[1] / mod, n[2] / mod))
                f.write(struct.pack("<9f", *va, *vb, *vc))
                f.write(struct.pack("<H", 0))

# ---------------- Construcción de la tuerca ----------------
def construir_tuerca(p) -> Malla:
    """
    Estrategia: los anillos exterior (hexágono) e interior (círculo) usan los
    MISMOS 24 ángulos, así cada segmento se acopla 1 a 1 y la malla es estanca
    por construcción (cada arista se comparte exactamente entre 2 caras).
    """
    m = Malla()
    n = p["n_lados"]
    apotema = p["s_llave"] / 2
    h = p["h_altura"]
    r_int = p["d_nominal"] / 2
    seg = 24  # segmentos por anillo (múltiplo de n para caer en los vértices)

    paso = 2 * math.pi / n

    def punto_hex(theta):
        """Punto sobre el contorno del hexágono en el ángulo theta."""
        e = int(theta / paso) % n              # arista activa
        m_ang = (e + 0.5) * paso               # ángulo medio de esa arista
        t = apotema / math.cos(theta - m_ang)  # distancia radial al borde
        return (t * math.cos(theta), t * math.sin(theta))

    ext_bajo, ext_top, int_bajo, int_top = [], [], [], []
    for i in range(seg):
        th = 2 * math.pi * i / seg
        ex, ey = punto_hex(th)
        ix, iy = r_int * math.cos(th), r_int * math.sin(th)
        ext_bajo.append(m.agregar_vert(ex, ey, 0))
        ext_top.append(m.agregar_vert(ex, ey, h))
        int_bajo.append(m.agregar_vert(ix, iy, 0))
        int_top.append(m.agregar_vert(ix, iy, h))

    def quad(a, b, c, d):
        m.agregar_tri(a, b, c)
        m.agregar_tri(a, c, d)

    for i in range(seg):
        j = (i + 1) % seg
        quad(int_bajo[i], int_bajo[j], ext_bajo[j], ext_bajo[i])  # tapa inferior (normal -z)
        quad(int_top[j], int_top[i], ext_top[i], ext_top[j])      # tapa superior (normal +z)
        quad(ext_bajo[i], ext_bajo[j], ext_top[j], ext_top[i])    # pared exterior
        quad(int_bajo[j], int_bajo[i], int_top[i], int_top[j])    # pared del agujero

    return m

# ---------------- Vista previa (HTML con SVG) ----------------
def exportar_preview(p, ruta):
    n = p["n_lados"]
    apotema = p["s_llave"] / 2
    r_hex = apotema / math.cos(math.pi / n)
    r_int = p["d_nominal"] / 2
    h = p["h_altura"]
    sc = 9  # px por mm

    # Vista superior: hexágono con vértices en k*60° (igual que la geometría real)
    pts = [(r_hex * math.cos(2 * math.pi * i / n), r_hex * math.sin(2 * math.pi * i / n)) for i in range(n)]
    poly = " ".join(f"{150 + sc * x:.1f},{120 + sc * y:.1f}" for x, y in pts)

    # Vista en alzado (sección lateral): ancho variable del hexágono
    ancho_max = 2 * r_hex * sc
    svg = f'''<html><body style="margin:0;background:#1e1e2e;color:#cdd6f4;font-family:monospace;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh">
  <h3 style="margin:8px">Tuerca M8 — vista previa del STL</h3>
  <svg width="480" height="360" viewBox="0 0 300 240">
    <polygon points="{poly}" fill="#89b4fa" stroke="#cdd6f4" stroke-width="2"/>
    <circle cx="150" cy="120" r="{sc * r_int:.1f}" fill="#1e1e2e" stroke="#cdd6f4" stroke-width="1.5" stroke-dasharray="4,2"/>
    <rect x="200" y="{120 - h * sc / 2:.1f}" width="{ancho_max * 0.87:.0f}" height="{h * sc:.1f}" fill="#a6e3a1" stroke="#cdd6f4" stroke-width="2"/>
    <line x1="{150 - sc * apotema:.1f}" y1="230" x2="{150 + sc * apotema:.1f}" y2="230" stroke="#f9e2af" stroke-width="1.5"/>
    <text x="150" y="244" fill="#f9e2af" font-size="10" text-anchor="middle">boca de llave {p["s_llave"]:.1f} mm</text>
    <text x="245" y="{120 - h * sc / 2 - 6:.0f}" fill="#f9e2af" font-size="10" text-anchor="middle">altura {h} mm</text>
  </svg>
  <p style="font-size:12px">izquierda: vista superior · derecha: alzado</p>
</body></html>'''
    with open(ruta, "w") as f:
        f.write(svg)

# ---------------- Main ----------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--medida", default="M8", choices=["M4", "M6", "M8", "M10", "M12"])
    args = ap.parse_args()

    p = parametros(args.medida)
    malla = construir_tuerca(p)
    salida_stl = f"tuerca_{args.medida.lower()}.stl"
    malla.exportar_stl(salida_stl, f"tuerca_{args.medida}")
    exportar_preview(p, salida_stl.replace(".stl", "_preview.html"))
    print(f"✅ {salida_stl}: {len(malla.tris)} triángulos")
    print(f"   Agujero: {p['d_nominal']:.2f} mm | Boca de llave: {p['s_llave']:.1f} mm | Altura: {p['h_altura']:.1f} mm")
