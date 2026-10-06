#!/usr/bin/env python3
"""
empaquetar.py — deja el entregable listo para mandar o subir

    python3 empaquetar.py ../clientes/<slug> [--pdf]

Crea en clientes/<slug>/entrega/:
  diagnostico-<slug>/            carpeta para subir a un hosting (index.html + assets/)
  diagnostico-<slug>.zip         la misma carpeta comprimida
  diagnostico-<slug>.html        archivo ÚNICO con imágenes y logos incrustados:
                                 se abre con doble clic o se adjunta en un correo
  diagnostico-<slug>.pdf         (con --pdf) versión impresa con Chrome, todo desplegado

No sube nada a ningún servidor: eso se hace solo con confirmación explícita.
"""
import base64
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

def detectar_chrome():
    """Usa CHROME_PATH o busca Google Chrome en las ubicaciones habituales."""
    configurado = os.environ.get("CHROME_PATH")
    if configurado:
        ruta = Path(configurado).expanduser()
        if not ruta.is_file():
            raise FileNotFoundError("CHROME_PATH no apunta a un archivo existente")
        return str(ruta)

    for nombre in ("google-chrome", "google-chrome-stable", "chrome", "chrome.exe", "chromium", "chromium-browser"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta

    candidatas = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        if os.environ.get(variable):
            candidatas.append(Path(os.environ[variable]) / "Google/Chrome/Application/chrome.exe")
    for ruta in candidatas:
        if ruta.is_file():
            return str(ruta)
    raise FileNotFoundError("No se encontró Chrome. Instálalo o define CHROME_PATH con la ruta a su ejecutable")


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 empaquetar.py ../clientes/<slug> [--pdf]")
    raiz = Path(sys.argv[1]).resolve()
    slug = raiz.name
    pres = raiz / "presentacion"
    if not (pres / "index.html").exists():
        sys.exit("Falta presentacion/index.html: corre construir.py primero")
    ent = raiz / "entrega"
    if ent.exists():
        shutil.rmtree(ent)
    ent.mkdir()
    nombre = f"diagnostico-{slug}"
    carpeta = ent / nombre
    shutil.copytree(pres, carpeta)
    shutil.make_archive(str(ent / nombre), "zip", ent, nombre)

    html = (pres / "index.html").read_text(encoding="utf-8")

    def incrustar(m):
        ruta = pres / m.group(2)
        if not ruta.is_file():
            return m.group(0)
        mime = mimetypes.guess_type(ruta.name)[0] or ("image/webp" if ruta.suffix == ".webp" else "image/svg+xml")
        return f'{m.group(1)}="data:{mime};base64,{base64.b64encode(ruta.read_bytes()).decode()}"'
    unico = re.sub(r'(src|href|data-full)="(assets/[^"]+)"', incrustar, html)  # data-full: páginas completas de la galería
    (ent / f"{nombre}.html").write_text(unico, encoding="utf-8")

    print(f"✓ {carpeta.relative_to(raiz)}/")
    print(f"✓ {nombre}.zip  ({(ent / f'{nombre}.zip').stat().st_size // 1024} KB)")
    print(f"✓ {nombre}.html (archivo único, {len(unico.encode()) // 1024} KB)")

    if "--pdf" in sys.argv:
        pdf = ent / f"{nombre}.pdf"
        try:
            chrome = detectar_chrome()
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                            "--virtual-time-budget=6000", f"--print-to-pdf={pdf}", (carpeta / "index.html").as_uri()],
                           check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not pdf.is_file() or pdf.stat().st_size == 0:
                raise RuntimeError("Chrome no generó un PDF válido")
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            sys.exit(f"✗ No se pudo generar el PDF: {error}. El HTML y el ZIP ya están en entrega/")
        print(f"✓ {pdf.name}")


if __name__ == "__main__":
    main()
