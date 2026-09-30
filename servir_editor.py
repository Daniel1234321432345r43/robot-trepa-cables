#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERVIDOR LOCAL SIN CACHE  ->  http://127.0.0.1:8123/editor_web.html

Por qué existe. `python3 -m http.server` no manda `Cache-Control`, así que el
navegador aplica su heurística de frescura (10 % del tiempo transcurrido desde
el `Last-Modified`) y puede seguir sirviendo la copia vieja de `editor_web.html`
después de reconstruirlo. El síntoma es desconcertante: el archivo en disco ya
es el nuevo (se comprueba con `grep`) pero la pestaña sigue mostrando el
anterior. Este servidor manda `no-store` en todo, así que cada recarga trae el
archivo de disco, sin excepciones.

Uso:
    python3 servir_editor.py                 # puerto 8123
    python3 servir_editor.py --puerto 9000
"""

import argparse
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))


class SinCache(SimpleHTTPRequestHandler):
    """Sirve archivos añadiendo cabeceras que prohíben el almacenamiento."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        # Que no conteste 304 "Not Modified": queremos el archivo entero siempre,
        # porque un 304 deja al navegador usando su copia guardada.
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        return super().send_head()

    def log_message(self, formato, *args):
        # Solo lo que importa: peticiones que no sean el favicon
        if "favicon" not in self.path:
            sys.stderr.write("%s - %s\n" % (self.address_string(), formato % args))


def main():
    ap = argparse.ArgumentParser(description="Sirve el editor web sin caché")
    ap.add_argument("--puerto", type=int, default=8123)
    ap.add_argument("--raiz", default=AQUI)
    args = ap.parse_args()

    manejador = partial(SinCache, directory=args.raiz)
    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), manejador)
    print("=" * 66)
    print("Sirviendo %s" % args.raiz)
    print("  http://127.0.0.1:%d/editor_web.html" % args.puerto)
    print("  (Cache-Control: no-store: recargar siempre trae el archivo de disco)")
    print("  Ctrl+C para parar")
    print("=" * 66)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nparado")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
