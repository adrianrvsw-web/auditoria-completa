#!/usr/bin/env python3
"""
construir.py — informe.json redactado → presentacion/index.html

    python3 construir.py ../clientes/<slug>            # valida y construye
    python3 construir.py ../clientes/<slug> --validar  # solo valida

Lee   informe.json, analisis/checks.json, datos/sitio.json, datos/rendimiento.json,
      datos/capturas/*.png, evidencia/*.png, reglas.json, servicios.json
Deja  presentacion/index.html          CSS y JS incrustados
      presentacion/assets/…            logos, capturas y evidencia en WebP

Estructura de la pieza: portada con el sitio montado en dispositivos → índice lateral
fijo + contenido (01 En dos minutos · 02 Cómo se ve hoy · 03 Área por área ·
04 Qué hacer primero · 05 Un solo paquete · [06 Competencia] · Siguiente paso · Anexo).

El diagnóstico no compromete fechas ni plazos: propone resolver todo en un paquete de
servicios organizado en tres frentes (servicios.json → frentes). construir.py avisa si
algún texto visible habla de semanas, meses o «de inmediato».

No construye si queda algún {{REDACTAR}}, si una rúbrica está incompleta, si falta la
sección de diseño o si un hallazgo visible no queda dentro de ningún frente del paquete.
"""
from __future__ import annotations

import html
import json
import math
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import REGLAS, SERVICIOS, puntuar  # noqa: E402

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
PLANTILLA = SKILL / "assets" / "plantilla"
LOGOS = SKILL / "assets" / "logos"
SEVS = ["critica", "alta", "media", "baja"]
SEV_TXT = {"critica": "Crítica", "alta": "Alta", "media": "Media", "baja": "Baja"}
LIM = {"titulo": 90, "que_vimos": 340, "por_que": 280, "recomendacion": 280}
MARCA = "{{REDACTAR}}"

CHIPS = {
    "ux": [("ux.viewport", "Se adapta al teléfono"), ("ux.desborde_movil", "Sin desbordes"), ("ux.capa_bloquea", "Nada tapa al llegar"), ("ux.texto_pequeno", "Texto legible"), ("ux.fijos_movil", "Barras fijas contenidas"), ("ux.imagenes_rotas", "Imágenes completas")],
    "leads": [("leads.formulario", "Formulario de contacto"), ("leads.cta_home", "Contacto visible al llegar"), ("leads.whatsapp", "WhatsApp"), ("leads.tel_clicable", "Teléfono clicable"), ("leads.aviso_privacidad", "Aviso de privacidad"), ("leads.medicion", "Analítica"), ("leads.pixeles", "Píxeles de campañas")],
    "seo": [("seo.indexable", "Indexable"), ("seo.titulos", "Títulos"), ("seo.descripciones", "Descripciones"), ("seo.h1", "Encabezados H1"), ("seo.sitemap", "Sitemap"), ("seo.schema", "Datos estructurados"), ("seo.canonicalizacion", "Dominio único"), ("seo.error404", "Error 404")],
    "geo": [("geo.bots_ia", "Bots de IA permitidos"), ("geo.sin_js", "Texto legible sin JavaScript"), ("geo.entidad", "Empresa descrita"), ("geo.faq", "Preguntas frecuentes"), ("geo.llms_txt", "llms.txt")],
    "tecnica": [("tec.https", "HTTPS"), ("tec.certificado", "Certificado"), ("tec.version_servidor", "Versión de PHP"), ("tec.cms", "CMS al día"), ("tec.librerias", "Librerías"), ("tec.cabeceras", "Cabeceras de seguridad"), ("tec.errores_js", "Sin errores JS")],
    "accesibilidad": [("a11y.axe", "Barreras graves"), ("a11y.contraste", "Contraste"), ("a11y.alt", "Textos alternativos"), ("a11y.psi", "Lighthouse")],
    "contenido": [("cont.relleno", "Sin texto de relleno"), ("cont.caducado", "Sin menciones caducadas"), ("cont.anio", "Año al día"), ("cont.actualizacion", "Actualizado"), ("cont.blog", "Blog activo"), ("cont.enlaces_externos", "Enlaces externos")],
}
GLOSARIO = [
    ("SEO", "Posicionamiento en buscadores: que el sitio aparezca, y aparezca bien, cuando alguien busca en Google."),
    ("GEO", "Optimización para motores generativos: que ChatGPT, Gemini, Perplexity o las respuestas con IA de Google puedan leer el sitio y citarlo."),
    ("PageSpeed / Lighthouse", "Herramientas de Google que miden la velocidad y la calidad técnica de una página en una escala de 0 a 100."),
    ("LCP", "Tiempo hasta que aparece el contenido principal de la página. Google lo considera bueno por debajo de 2.5 segundos."),
    ("CLS", "Cuánto «saltan» los elementos mientras carga la página. Bueno por debajo de 0.1."),
    ("INP", "Cuánto tarda la página en reaccionar cuando la persona toca o hace clic. Bueno por debajo de 200 ms."),
    ("Datos estructurados (schema)", "Código invisible que describe a la empresa, sus productos o sus preguntas frecuentes para que buscadores e IA lo entiendan sin adivinar."),
    ("WCAG 2.1 AA", "Estándar internacional de accesibilidad web. axe-core revisa automáticamente una parte de sus criterios."),
    ("Píxel", "Fragmento de código de Meta, Google Ads o LinkedIn que permite medir campañas y crear audiencias."),
]


def e(s):
    return html.escape(str(s or ""), quote=True)


def rich(s, grad="gradient-text"):
    """Escapa y admite **negrita** y *énfasis con degradado*."""
    t = e(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"\*(.+?)\*", rf'<span class="{grad}">\1</span>', t)


ICON = {
    "ok": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    "bad": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    "mid": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 4v16" /></svg>',
    "na": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 12h12"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg>',
    "arrow": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "scroll": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="3" width="10" height="18" rx="5"/><path d="M12 7v4"/></svg>',
    "zoom": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4M11 8v6M8 11h6"/></svg>',
    "menu": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h10"/></svg>',
}
EST_ICON = {"ok": "ok", "falla": "bad", "parcial": "mid", "na": "na"}
PLAZO = re.compile(r"\b(?:\d+\s*[–-]\s*)?\d*\s*(?:semanas?|meses|mes \d|trimestres?|d[ií]as h[aá]biles|horas de trabajo|de inmediato|inmediat[oa]s?|en semanas|en d[ií]as|garantiz\w+)\b", re.I)
# Si Newemage hizo o mantiene el sitio (cliente.relacion = "mantenemos"), el tono cambia: el sitio
# no «cumplió su ciclo», pide su siguiente etapa. Ver references/redaccion.md → «Cuando el sitio es nuestro».
SUB_SENALES = {"externo": "Señales de un diseño que ya cumplió su ciclo", "mantenemos": "Lo que el sitio ya pide para su siguiente etapa"}
ASPECTO_TXT = {"desactualizado": "Desactualizado", "mejorable": "Mejorable", "actual": "Actual"}


def veredicto_visual(d):
    """Resumen del bloque diseno.veredicto: (estado, n desactualizados, n total) o None."""
    v = d.get("veredicto") or {}
    cr = v.get("criterios") or []
    if not v or not cr:
        return None
    return v.get("estado") or "Desactualizado", sum(1 for x in cr if x["estado"] == "desactualizado"), len(cr)


def plural(t):
    """«Desactualizado» → «desactualizados», «Actual» → «actuales», «Insuficiente» → «insuficientes»."""
    t = t.lower()
    return t + ("s" if t[-1] in "aeiou" else "es")


EST_TXT = {"ok": "Cumple", "falla": "No cumple", "parcial": "A medias", "na": "No aplica"}


def ring(v, color, sub="", cls=""):
    r = 45
    L = 2 * math.pi * r
    off = L * (1 - (v or 0) / 100)
    return (f'<div class="ring c-{color} {cls}" data-v="{v or 0}" role="img" aria-label="{v if v is not None else "sin dato"} de 100">'
            f'<svg viewBox="0 0 100 100" aria-hidden="true"><circle class="trk" cx="50" cy="50" r="{r}" stroke-width="7"/>'
            f'<circle class="val" cx="50" cy="50" r="{r}" stroke-width="7" style="stroke-dasharray:{L:.1f};stroke-dashoffset:{off:.1f};--len:{L:.1f}"/></svg>'
            f'<div><span class="ring__num">{v if v is not None else "–"}</span>{f"<span class=ring__sub>{e(sub)}</span>" if sub else ""}</div></div>')


# ─────────────────────────── imágenes ────────────────────────────────
class Medios:
    """Convierte cada imagen una sola vez a WebP y recuerda su tamaño."""

    def __init__(self, raiz: Path, dst: Path):
        self.raiz, self.dst, self.cache = raiz, dst, {}

    def buscar(self, nombre):
        return buscar_img(self.raiz, nombre)

    def webp(self, src: Path, maxw=1400, maxh=2600, q=80, sufijo=""):
        clave = (str(src), maxw, maxh, q)
        if clave in self.cache:
            return self.cache[clave]
        from PIL import Image
        im = Image.open(src)
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        if im.height > maxh:  # capturas completas: se conserva la parte alta
            im = im.crop((0, 0, im.width, maxh))
        nombre = re.sub(r"[^a-z0-9-]+", "-", src.stem.lower()).strip("-") + sufijo + f"-{maxw}.webp"
        im.save(self.dst / nombre, "WEBP", quality=q, method=6)
        self.cache[clave] = (f"assets/img/{nombre}", im.width, im.height)
        return self.cache[clave]


def captura(M, nombre):
    """Portada, «Cómo se ve hoy» y galería: prefiere la captura sin ventanas emergentes ni chat
    (datos/capturas-limpias, de capturas_limpias.js); si no existe, la original."""
    return M.buscar(f"capturas-limpias/{nombre}") or M.buscar(f"capturas/{nombre}")


def buscar_img(raiz, nombre):
    for base in (raiz / "evidencia", raiz / "datos", raiz / "datos" / "capturas", raiz):
        p = base / nombre
        if nombre and p.is_file():
            return p
    return None


def marco(tipo, img_html, url="", boton=None, scroll=False, etiqueta=""):
    """Envuelve una captura en un navegador, un teléfono o nada. boton = dict de data-* para el visor."""
    cls = f"frame frame--{tipo}" + (" frame--scroll" if scroll else "")
    barra = f'<div class="frame__bar" aria-hidden="true"><i></i><i></i><i></i><span>{e(url)}</span></div>' if tipo == "browser" else ""
    vista = (f'<div class="frame__view" tabindex="0" role="region" aria-label="{e(etiqueta)}">{img_html}</div>' if scroll
             else f'<div class="frame__view">{img_html}</div>')
    if boton is not None:
        datos = " ".join(f'data-{k}="{e(v)}"' if v is not True else f"data-{k}" for k, v in boton.items() if v)
        return f'<button type="button" class="{cls}" {datos} aria-label="Ampliar: {e(boton.get("cap") or etiqueta)}">{barra}{vista}<span class="zoom" aria-hidden="true">{ICON["zoom"]} Ampliar</span></button>'
    return f'<div class="{cls}">{barra}{vista}</div>'


def img_tag(ruta, w, h, alt, lazy=True):
    return f'<img src="{ruta}" width="{w}" height="{h}" alt="{e(alt)}"{" loading=lazy decoding=async" if lazy else ""}>'


def tipo_marco(ev, w, h, nombre):
    if ev.get("marco") in ("browser", "phone", "plain"):
        return ev["marco"]
    if w / h > 3.2:
        return "plain"
    if h / w > 1.3 and (w <= 820 or nombre.startswith("mobile-") or "movil" in nombre):
        return "phone"   # solo capturas verticales: en un recorte apaisado la «isla» taparía el contenido
    if w <= 820:
        return "plain"   # recorte pequeño de teléfono (p. ej. la cabecera): sin marco, a su tamaño
    return "browser"


# ─────────────────────────── validación ──────────────────────────────
def pendientes(o, ruta=""):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if not k.startswith("_"):
                out += pendientes(v, f"{ruta}.{k}" if ruta else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += pendientes(v, f"{ruta}[{i}]")
    elif isinstance(o, str) and MARCA in o:
        out.append(ruta)
    return out


def validar(inf, raiz):
    err, warn = [], []
    hs = inf.get("hallazgos", [])
    vis = [h for h in hs if h.get("visible")]
    ids = {h["id"] for h in hs}
    for p in pendientes(dict(inf, hallazgos=vis)):  # los ocultos pueden quedar sin redactar
        err.append(f"Falta redactar: {p}")
    for h in hs:
        if h.get("area") not in REGLAS["areas"]:
            err.append(f"{h.get('id')}: área desconocida {h.get('area')}")
        if h.get("severidad") not in SEVS:
            err.append(f"{h['id']}: severidad inválida {h.get('severidad')}")
        if h.get("servicio") not in SERVICIOS["servicios"]:
            err.append(f"{h['id']}: servicio desconocido {h.get('servicio')}")
        if h.get("impacto") not in (1, 2, 3) or h.get("esfuerzo") not in (1, 2, 3):
            err.append(f"{h['id']}: impacto y esfuerzo van de 1 a 3")
        if h.get("visible"):
            for k, lim in LIM.items():
                if len(h.get(k) or "") > lim:
                    warn.append(f"{h['id']}.{k}: {len(h[k])} caracteres (máx. recomendado {lim}). Recorta: el cliente no lee bloques largos.")
            for ev in h.get("evidencia", []):
                if not buscar_img(raiz, ev.get("img", "")):
                    err.append(f"{h['id']}: no existe la imagen de evidencia {ev.get('img')}")
    sin_img = [h["id"] for h in vis if h["area"] in ("ux", "leads", "contenido") and not h.get("evidencia")]
    if sin_img:
        warn.append(f"Hallazgos visuales sin captura: {', '.join(sin_img)}. Una imagen convence más que el texto.")
    d = inf.get("diseno") or {}
    if not d:
        err.append("diseno: falta la sección «Cómo se ve hoy» (titular, texto, señales ≥ 3)")
    else:
        if not 3 <= len(d.get("senales", [])) <= 8:
            err.append("diseno.senales: entre 3 y 8 señales, cada una con su captura")
        for x in (d.get("veredicto") or {}).get("criterios", []):
            if x.get("estado") not in ASPECTO_TXT:
                err.append(f"diseno.veredicto: estado inválido «{x.get('estado')}» en {x.get('aspecto')} (desactualizado | mejorable | actual)")
        for i, s in enumerate(d.get("senales", [])):
            if not buscar_img(raiz, s.get("img", "")):
                err.append(f"diseno.senales[{i}]: no existe la imagen {s.get('img')}")
    pr = inf.get("prioridades", [])
    if len(pr) != 3:
        err.append("prioridades: deben ser exactamente 3 IDs de hallazgos visibles")
    for p in pr:
        if p not in {h["id"] for h in vis}:
            err.append(f"prioridades: {p} no es un hallazgo visible")
    for p in inf.get("inmediatos", []):
        if p not in {h["id"] for h in vis}:
            err.append(f"inmediatos: {p} no es un hallazgo visible")
        elif p in pr:
            err.append(f"inmediatos: {p} ya es una de las tres prioridades")
    for aid, crit in REGLAS["rubricas"].items():
        if aid.startswith("_") or REGLAS["areas"][aid]["mezcla"]["rubrica"] == 0:
            continue
        for c in crit:
            pts = (inf.get("rubricas", {}).get(aid, {}).get(c["id"]) or {}).get("puntos")
            if pts not in (0, 1, 2):
                err.append(f"rúbrica {aid}.{c['id']}: puntos debe ser 0, 1 o 2")
    paq = inf.get("paquete", {})
    cubiertos = {x for fr in paq.values() for x in fr.get("hallazgos", [])}
    for h in vis:
        if h["id"] not in cubiertos:
            err.append(f"{h['id']} es visible pero no está en ningún frente del paquete")
    for k, fr in paq.items():
        if k not in SERVICIOS["frentes"]:
            err.append(f"paquete: frente desconocido {k}")
        for s in fr.get("servicios", []):
            if s not in SERVICIOS["servicios"]:
                err.append(f"paquete.{k}: servicio desconocido {s}")
        for x in fr.get("hallazgos", []):
            if x not in ids:
                err.append(f"paquete.{k}: hallazgo inexistente {x}")
        faltan = {h["servicio"] for h in vis if h["id"] in fr.get("hallazgos", [])} - set(fr.get("servicios", []))
        if faltan:
            warn.append(f"paquete.{k}: sus hallazgos se resuelven con {', '.join(sorted(faltan))}, que no está en sus servicios")
    usados = [x for fr in paq.values() for x in fr.get("servicios", [])]
    for x in sorted({x for x in usados if usados.count(x) > 1}):
        warn.append(f"paquete: {x} aparece en más de un frente; en un paquete cada servicio va una sola vez")
    # Sin compromisos de tiempo: el diagnóstico propone un paquete, no un calendario
    visibles = [inf.get("resumen"), inf.get("fortalezas"), inf.get("diseno"), inf.get("areas"), inf.get("paquete"), inf.get("cierre"), vis]
    for m in sorted(set(PLAZO.findall(json.dumps(visibles, ensure_ascii=False)))):
        warn.append(f"Texto con plazo o compromiso de tiempo: «{m}». El diagnóstico no promete fechas; quítalo o reformúlalo")
    por_area = {}
    for h in vis:
        por_area[h["area"]] = por_area.get(h["area"], 0) + 1
    for a, n in por_area.items():
        if n > 6:
            warn.append(f"{a}: {n} hallazgos visibles. Más de 6 por área cansa: fusiona o pasa los menores a visible:false")
    if len(vis) > 30:
        warn.append(f"{len(vis)} hallazgos visibles en total: apunta a 18–28")
    if len(inf.get("resumen", {}).get("parrafo", "")) > 480:
        warn.append("resumen.parrafo pasa de 480 caracteres: el resumen debe leerse en 20 segundos")
    if len(inf.get("fortalezas", [])) < 3:
        err.append("fortalezas: se necesitan 3 (se abre reconociendo lo que funciona)")
    return err, warn


# ─────────────────────────── secciones ───────────────────────────────
def sec_hero(inf, gen, sitio, M, hs):
    c = inf["cliente"]
    home = sitio["paginas"][0]
    vis = [h for h in hs if h.get("visible")]
    comp = ""
    dk, mb = captura(M, f"desktop-{home['id']}.png"), captura(M, f"mobile-{home['id']}.png")
    if dk:
        r, w, h = M.webp(dk, 1200, 900, 82)
        comp += marco("browser", img_tag(r, w, h, f"Página de inicio de {c['dominio']} en computadora", lazy=False), c["dominio"])
    if mb:
        r, w, h = M.webp(mb, 360, 780, 82)
        comp += marco("phone", img_tag(r, w, h, f"Página de inicio de {c['dominio']} en teléfono", lazy=False))
    vv = veredicto_visual(inf.get("diseno") or {})
    hero_vv = f'<a class="hero__verdict" href="#diseno"><span>Diseño</span><b>{e(vv[0])}</b><small>{vv[1]} de {vv[2]} aspectos</small></a>' if vv else ""
    showcase = f'<figure class="showcase">{comp}<figcaption>Así se ve hoy · {e(c["dominio"])}</figcaption></figure>' if comp else ""
    return f'''
<header class="on-dark hero" id="portada">
  <div class="mesh" aria-hidden="true"><span class="b1"></span><span class="b2"></span><span class="b3"></span></div>
  <div class="wrap">
    <div class="hero__grid">
      <div>
        <p class="hero__badge"><i aria-hidden="true"></i>Diagnóstico digital · {e(c["dominio"])}</p>
        <h1>{rich(inf["resumen"]["titular"], "text-gradient")}</h1>
        <p class="hero__lead">{rich(inf["resumen"]["parrafo"])}</p>
        <div class="hero__ctas">
          <a class="btn btn--warm" href="#resumen">Ver el diagnóstico {ICON["arrow"]}</a>
          <a class="btn btn--ghost" href="#diseno">Cómo se ve hoy</a>
        </div>
        <div class="hero__stats rv">
          {ring(gen["final"], gen["color"], "de 100")}
          <div><span class="lbl c-{gen["color"]}">{e(gen["etiqueta"])}</span><b>Calificación general</b><small>8 áreas revisadas · {len(vis)} hallazgos · 3 prioridades</small></div>
          {hero_vv}
        </div>
      </div>
      {showcase}
    </div>
    <dl class="hero__meta">
      <div><dt>Sitio</dt><dd>{e(c["dominio"])}</dd></div>
      <div><dt>Fecha</dt><dd>{e(inf["fecha"])}</dd></div>
      <div><dt>Alcance</dt><dd>{len(sitio["paginas"])} páginas · 8 áreas</dd></div>
      <div><dt>Dispositivos</dt><dd>Computadora y teléfono</dd></div>
    </dl>
  </div>
</header>'''


def sec_toc(inf, areas, hay_comp):
    subs = "".join(f'<li><a href="#area-{aid}"><i class="c-{areas[aid]["color"]}" aria-hidden="true"></i>{e(a["corto"])}<b>{areas[aid]["final"]}</b></a></li>'
                   for aid, a in sorted(REGLAS["areas"].items(), key=lambda x: x[1]["orden"]))
    items = [("resumen", "01", "En dos minutos"), ("diseno", "02", "Cómo se ve hoy"), ("areas", "03", "Área por área")]
    html_ = ""
    for i, n, t in items:
        html_ += f'<li><a href="#{i}"><span class="n">{n}</span>{t}</a>' + (f'<ol class="toc__sub">{subs}</ol>' if i == "areas" else "") + "</li>"
    resto = [("matriz", "04", "Qué hacer primero"), ("paquete", "05", "Un solo paquete")] + ([("comparativa", "06", "Frente a la competencia")] if hay_comp else []) + [("cierre", "→", "Siguiente paso"), ("anexo", "+", "Anexo")]
    html_ += "".join(f'<li><a href="#{i}"><span class="n">{n}</span>{t}</a></li>' for i, n, t in resto)
    return f'''
<nav class="toc" id="indice" aria-label="Contenido del diagnóstico">
  <div class="toc__in">
    <div class="toc__head"><span class="tag">Contenido</span><button type="button" class="toc__close" aria-label="Cerrar índice">×</button></div>
    <ol>{html_}</ol>
    <div class="toc__cta"><b>¿Lo revisamos juntos?</b><p>Revisemos el diagnóstico y armemos el paquete a su medida.</p><a class="btn btn--warm btn--sm" href="#cierre">Hablemos {ICON["arrow"]}</a></div>
  </div>
</nav>
<div class="toc-scrim" aria-hidden="true"></div>
<button type="button" class="toc-fab" aria-controls="indice" aria-expanded="false">{ICON["menu"]} Índice</button>'''


def sec_resumen(inf, hs_by_id, hs, sitio):
    vis = [h for h in hs if h.get("visible")]
    n = lambda s: sum(1 for h in vis if h["severidad"] == s)  # noqa: E731
    rap = sum(1 for h in vis if h["impacto"] >= 3 and h["esfuerzo"] == 1)
    kpis = (f'<div class="card kpi"><b>{len(vis)}</b><span>hallazgos en {len(sitio["paginas"])} páginas</span></div>'
            f'<div class="card kpi kpi--critica"><b>{n("critica")}</b><span>de prioridad crítica</span></div>'
            f'<div class="card kpi kpi--alta"><b>{n("alta")}</b><span>de prioridad alta</span></div>'
            f'<div class="card kpi"><b>{n("media") + n("baja")}</b><span>de prioridad media o baja</span></div>'
            f'<div class="card kpi kpi--quick"><b>{rap}</b><span>arreglos rápidos</span></div>')
    fort = "".join(f'<li>{ICON["check"]}<div><b>{e(f["titulo"])}</b><span>{rich(f["texto"])}</span></div></li>' for f in inf["fortalezas"])
    # Arreglos inmediatos: mucho efecto y poco esfuerzo, fuera de las 3 prioridades (no compiten con ellas)
    # informe.inmediatos (opcional) fija la lista a mano: arreglos de poco esfuerzo que conviene nombrar aunque su impacto sea medio
    if inf.get("inmediatos"):
        inm = [hs_by_id[i] for i in inf["inmediatos"]][:3]
    else:
        inm = [h for h in vis if h["impacto"] >= 3 and h["esfuerzo"] == 1 and h["id"] not in inf["prioridades"]][:3]
    rapidos = ('<div class="inm"><span>Además, arreglos inmediatos</span><ul>' + "".join(f'<li><a href="#h-{e(h["id"])}"><code>{e(h["id"])}</code>{e(h["titulo"])}</a></li>' for h in inm) + "</ul></div>") if inm else ""
    prios = ""
    for i, pid in enumerate(inf["prioridades"], 1):
        h = hs_by_id[pid]
        prios += (f'<a class="prio" href="#h-{e(pid)}"><span class="prio__n">{i}</span><div><b>{e(h["titulo"])}</b>'
                  f'<small>{e(REGLAS["areas"][h["area"]]["nombre"])} · lo resuelve: {e(SERVICIOS["servicios"][h["servicio"]]["nombre"])}</small></div>'
                  f'<span class="prio__go">{ICON["arrow"]}</span></a>')
    return f'''
<section class="sec" id="resumen">
  <div class="sec__head rv"><span class="sec__n">01</span><h2>En dos minutos</h2>
    <p>Lo que ya tiene a su favor y las tres cosas que más conviene atender primero.</p></div>
  <div class="kpis rv">{kpis}</div>
  <div class="brief">
    <div class="card strengths rv"><span class="tag">Lo que ya funciona</span><h3>Una base con la que trabajar</h3><ul>{fort}</ul></div>
    <div class="card prios rv"><span class="tag">Por dónde empezar</span><h3>Las tres prioridades</h3>{prios}{rapidos}</div>
  </div>
</section>'''


def sec_diseno(inf, sitio, M):
    d, c = inf["diseno"], inf["cliente"]
    home = sitio["paginas"][0]
    live = ""
    dk, mb = captura(M, f"desktop-{home['id']}-full.png"), captura(M, f"mobile-{home['id']}-full.png")
    if dk:
        r, w, h = M.webp(dk, 1100, 7000, 70, "-vivo")
        live += marco("browser", img_tag(r, w, h, f"Página de inicio completa de {c['dominio']} en computadora"), c["dominio"], scroll=True, etiqueta="Página de inicio en computadora: desplácese dentro")
    if mb:
        r, w, h = M.webp(mb, 540, 12000, 68, "-vivo")
        live += marco("phone", img_tag(r, w, h, f"Página de inicio completa de {c['dominio']} en teléfono"), scroll=True, etiqueta="Página de inicio en teléfono: desplácese dentro")
    live_html = f'<div class="live rv">{live}<p class="live__hint">{ICON["scroll"]}Desplácese dentro de cada pantalla para recorrer la página de inicio tal como la ve hoy un visitante.</p></div>' if live else ""

    sen = ""
    for i, s in enumerate(d["senales"], 1):
        src = M.buscar(s["img"])
        r, w, h = M.webp(src, 1400, 2600, 80)
        sen += (f'<article class="card signal rv">{marco("plain", img_tag(r, w, h, s.get("pie") or s["titulo"]), boton={"cap": s.get("pie") or s["titulo"]})}'
                f'<div class="signal__body"><span class="signal__n">Señal {i:02d}</span><h4>{e(s["titulo"])}</h4><p>{rich(s["texto"])}</p></div></article>')
    vs = ""
    if d.get("comparacion"):
        hoy = "".join(f'<li>{ICON["bad"]}<span>{rich(x["hoy"])}</span></li>' for x in d["comparacion"])
        esp = "".join(f'<li>{ICON["ok"]}<span>{rich(x["se_espera"])}</span></li>' for x in d["comparacion"])
        vs = f'<div class="card vs rv"><div class="vs__col"><h4>Hoy en {e(c["dominio"])}</h4><ul>{hoy}</ul></div><div class="vs__col"><h4>Lo que hoy espera un visitante</h4><ul>{esp}</ul></div></div>'

    ver = ""
    vv = veredicto_visual(d)
    if vv:
        v = d["veredicto"]
        # veredicto.etiquetas (opcional) renombra los tres estados, p. ej. {"desactualizado": "Insuficiente"} cuando el problema
        # no es la antigüedad sino un diseño demasiado simple; las claves y los colores no cambian
        txt = {**ASPECTO_TXT, **{k: t for k, t in (v.get("etiquetas") or {}).items() if k in ASPECTO_TXT}}
        asp = "".join(f'<li class="asp asp--{x["estado"]}"><span class="asp__st">{e(txt[x["estado"]])}</span><b>{e(x["aspecto"])}</b><small>{rich(x["nota"])}</small></li>' for x in v["criterios"])
        n = {k: sum(1 for x in v["criterios"] if x["estado"] == k) for k in ASPECTO_TXT}
        barra = "".join(f'<i class="asp--{k}" style="flex:{n[k]}"></i>' for k in ASPECTO_TXT if n[k])
        ver = (f'<div class="on-dark vv rv"><div class="vv__main"><span class="tag">Veredicto visual</span><b class="vv__v">{e(vv[0])}</b>'
               f'<p>{rich(v.get("texto", ""))}</p><div class="vv__bar" aria-hidden="true">{barra}</div>'
               f'<small>{" · ".join(f"{n[k]} {plural(txt[k])}" for k in ASPECTO_TXT)}</small></div><ul class="aspects">{asp}</ul></div>')

    gal = ""
    for p in sitio["paginas"]:
        fold, full = captura(M, f"desktop-{p['id']}.png"), captura(M, f"desktop-{p['id']}-full.png")
        if not fold:
            continue
        r, w, h = M.webp(fold, 560, 400, 72, "-mini")
        ruta = urlparse(p["url"]).path or "/"
        grande = M.webp(full, 900, 5200, 66, "-completa")[0] if full else r
        gal += (f'<figure>{marco("browser", img_tag(r, w, h, f"Página {ruta}"), c["dominio"] + ruta, boton={"full": grande, "cap": f"{c["dominio"]}{ruta} · página completa", "tall": bool(full)})}'
                f'<figcaption><b>{e(ruta)}</b><span>Ver completa</span></figcaption></figure>')
    return f'''
<section class="sec" id="diseno">
  <div class="sec__head rv"><span class="sec__n">02</span><h2>{rich(d["titular"])}</h2><p>{rich(d["texto"])}</p></div>
  {ver}
  {live_html}
  <h3 class="sub rv">{e(d.get("subtitulo") or (SUB_SENALES["mantenemos"] if inf["cliente"].get("relacion") == "mantenemos" else SUB_SENALES["externo"]))}</h3>
  <p class="hint rv">Capturas tomadas del sitio el {e(inf["fecha"])}. Toque cualquiera para ampliarla.</p>
  <div class="signals">{sen}</div>
  {vs}
  <h3 class="sub rv">Todas las páginas revisadas</h3>
  <p class="hint rv">Toque una página para verla completa.</p>
  <div class="gallery rv" tabindex="0" role="region" aria-label="Galería de páginas revisadas">{gal}</div>
</section>'''


def sec_tablero(inf, areas, hs):
    tiles = ""
    for aid, a in sorted(REGLAS["areas"].items(), key=lambda x: x[1]["orden"]):
        ar = areas[aid]
        n = sum(1 for h in hs if h.get("visible") and h["area"] == aid)
        tiles += (f'<a class="card tile rv" href="#area-{aid}"><div class="tile__top">{ring(ar["final"], ar["color"])}'
                  f'<span class="lbl c-{ar["color"]}">{e(ar["etiqueta"])}</span></div>'
                  f'<h3>{e(a["nombre"])}</h3><p>{rich(inf["areas"][aid]["veredicto"])}</p><span class="tile__n">{f'{n} hallazgo{"s" if n != 1 else ""}' if n else "Sin hallazgos prioritarios"} →</span></a>')
    escala = "".join(f'<span class="lbl c-{x["color"]}">{x["min"]}{"–" + str(prev - 1) if prev else "+"} · {e(x["nombre"])}</span>'
                     for x, prev in zip(REGLAS["etiquetas"], [None] + [y["min"] for y in REGLAS["etiquetas"][:-1]]))
    return f'''
<section class="sec" id="areas">
  <div class="sec__head rv"><span class="sec__n">03</span><h2>El sitio, área por área</h2>
    <p>Ocho áreas. Cada calificación combina mediciones automáticas y, donde aplica, una evaluación experta con criterios fijos. Toque cualquiera para ir al detalle.</p></div>
  <div class="scale rv" aria-label="Escala">{escala}</div>
  <div class="board">{tiles}</div>
</section>'''


def chip(est, txt):
    k = EST_ICON[est]
    return f'<span class="chip {k}">{ICON[k]}{e(txt)}<span class="sr"> — {EST_TXT[est]}</span></span>'


def panel_rendimiento(checks, rend):
    if not rend:
        return ""
    ms = [m for m in rend["mediciones"] if m.get("puntuaciones")]
    home = ms[0]["url"] if ms else None
    mob = [m for m in ms if m["url"] == home and m["strategy"] == "mobile"]
    desk = [m for m in ms if m["url"] == home and m["strategy"] == "desktop"]
    out = []

    def color(v, bueno, malo, menor_mejor=False):
        if v is None:
            return "na"
        if menor_mejor:
            return "ok" if v <= bueno else ("warn" if v <= malo else "bad")
        return "ok" if v >= bueno else ("warn" if v >= malo else "bad")
    if mob:
        ps = [m["puntuaciones"]["performance"] for m in mob]
        v = round(sum(ps) / len(ps))
        rng = f"{min(ps)}–{max(ps)}" if min(ps) != max(ps) else str(ps[0])
        out.append(("Velocidad en teléfono", rng, "/100 · prueba de Google", v, color(v, 90, 50)))
    if desk:
        v = desk[0]["puntuaciones"]["performance"]
        out.append(("Velocidad en computadora", str(v), "/100 · prueba de Google", v, color(v, 90, 50)))
    lcps = sorted(m["laboratorio"]["lcp"] for m in ms if m["strategy"] == "mobile" and m["laboratorio"].get("lcp"))
    if lcps:
        a, b = lcps[0] / 1000, lcps[-1] / 1000
        val = f"{a:.0f}–{b:.0f} s" if b - a >= 1 else f"{a:.1f} s"
        out.append(("Contenido principal visible", val, "en teléfono · bueno: menos de 2.5 s", max(0, min(100, 100 - (a - 2.5) * 18)), color(a, 2.5, 4, True)))
    pk = [m["laboratorio"]["pesoKB"] for m in mob if m["laboratorio"].get("pesoKB")]
    if pk:
        mb = pk[0] / 1024
        out.append(("Peso de la home", f"{mb:.1f} MB", "bueno: menos de 2.5 MB", max(0, min(100, 100 - (mb - 1) * 20)), color(mb, 2.5, 5, True)))
    campo = checks.get("rend.campo", {})
    if campo.get("estado") == "na":
        out.append(("Usuarios reales", "Sin datos", "Google aún no registra visitas suficientes", None, "na"))
    elif campo:
        out.append(("Usuarios reales", f"{round(campo['valor'] * 3)}/3", "métricas Core Web Vitals aprobadas", campo["valor"] * 100, {"ok": "ok", "parcial": "warn", "falla": "bad"}[campo["estado"]]))
    fuente = "Lighthouse en local (el sitio no permitió PageSpeed Insights)" if any(m.get("fuente") == "lighthouse-local" for m in ms) else "Google PageSpeed Insights"
    celdas = "".join(f'<div class="card metric c-{c}"><dt>{e(t)}</dt><dd><span class="v">{e(v)}</span><small>{e(s)}</small>'
                     + (f'<span class="bar" aria-hidden="true"><i style="width:{max(4, min(100, b)):.0f}%"></i></span>' if b is not None else "") + "</dd></div>" for t, v, s, b, c in out)
    return f'<dl class="metrics rv">{celdas}</dl><p class="tag metrics-src">Fuente: {e(fuente)} · {len(mob)} medición(es) de la home en teléfono</p>'


def tarjeta(h, M, dominio):
    figs = ""
    for ev in h.get("evidencia", [])[:2]:
        src = M.buscar(ev["img"])
        from PIL import Image
        w0, h0 = Image.open(src).size
        tipo = tipo_marco(ev, w0, h0, Path(ev["img"]).name)
        r, w, hh = M.webp(src, 600 if tipo == "phone" else 1400, 2600, 80)
        url = ev.get("url") or (dominio + (h.get("paginas") or [""])[0])
        figs += (f'<figure class="{"is-phone" if tipo == "phone" else "is-strip" if tipo == "plain" else ""}">'
                 f'{marco(tipo, img_tag(r, w, hh, ev.get("pie") or h["titulo"]), url, boton={"cap": ev.get("pie")})}'
                 f'<figcaption>{e(ev.get("pie"))}</figcaption></figure>')
    kv = "".join(f'<span>{e(d["k"])}: <b>{e(d["v"])}</b></span>' for d in h.get("datos", [])[:4])
    rapido = h["impacto"] >= 3 and h["esfuerzo"] == 1  # mismo criterio que el cuadrante «Arreglos rápidos»
    paginas = ", ".join(h.get("paginas", [])[:4]) + (f" y {len(h['paginas']) - 4} más" if len(h.get("paginas", [])) > 4 else "")
    srv = SERVICIOS["servicios"][h["servicio"]]
    return f'''
<article class="card finding" id="h-{e(h["id"])}">
  <div class="finding__top">
    <div class="finding__meta"><span class="sev sev--{h["severidad"]}">Prioridad {SEV_TXT[h["severidad"]].lower()}</span>{'<span class="quick">Arreglo rápido</span>' if rapido else ''}<span class="fid">{e(h["id"])}</span></div>
    <h3>{e(h["titulo"])}</h3>
  </div>
  {f'<div class="stage">{figs}</div>' if figs else ''}
  <div class="finding__cols">
    <div><h4>Qué vimos</h4><p>{rich(h["que_vimos"])}</p></div>
    <div><h4>Por qué importa</h4><p>{rich(h["por_que"])}</p></div>
    <div class="rec"><h4>Qué recomendamos</h4><p>{rich(h["recomendacion"])}</p></div>
  </div>
  {f'<div class="kv">{kv}</div>' if kv else ''}
  <div class="finding__foot">{f'<span>Dónde: <b>{e(paginas)}</b></span>' if paginas else ''}<span>Lo resuelve: <b>{e(srv["nombre"])}</b></span></div>
</article>'''


def sec_area(n, aid, inf, areas, checks, hs, M, rend):
    a, ar = REGLAS["areas"][aid], areas[aid]
    dominio = inf["cliente"]["dominio"]
    mias = sorted([h for h in hs if h["area"] == aid and h.get("visible")], key=lambda h: (SEVS.index(h["severidad"]), -h["impacto"], h["esfuerzo"]))
    chips = "".join(chip(checks[c]["estado"], t) for c, t in CHIPS.get(aid, []) if c in checks and checks[c]["estado"] != "na")
    panel = panel_rendimiento(checks, rend) if aid == "rendimiento" else (f'<div class="chips rv">{chips}</div>' if chips else "")
    primeras, resto = mias[:3], mias[3:]  # tres a la vista por área; el resto a un clic
    cards = "".join(tarjeta(h, M, dominio) for h in primeras)
    mas = f'<details class="more"><summary>Ver {len(resto)} hallazgo{"s" if len(resto) > 1 else ""} más en esta área</summary><div class="findings">{"".join(tarjeta(h, M, dominio) for h in resto)}</div></details>' if resto else ""
    if not mias:
        cards = '<p class="card" style="padding:24px">Sin hallazgos prioritarios en esta área. Los detalles menores están en «Ver las revisiones» y en el anexo.</p>'
    items = ""
    for cid, rc in REGLAS["checks"].items():
        if rc["area"] != aid:
            continue
        c = checks[cid]
        k = EST_ICON[c["estado"]]
        items += f'<li class="{k}">{ICON[k]}<div>{e(rc["titulo"])}<small>{e(EST_TXT[c["estado"]])} · {e(c["detalle"])}</small></div></li>'
    for cr in REGLAS["rubricas"].get(aid, []):
        r = inf.get("rubricas", {}).get(aid, {}).get(cr["id"], {})
        p = r.get("puntos") or 0
        k = ["bad", "mid", "ok"][p]
        items += (f'<li class="{k}">{ICON[k]}<div>{e(cr["criterio"])}<span class="rub" aria-label="{p} de 2">'
                  f'{"".join(f"<i class={chr(34)}on{chr(34)}></i>" if i < p else "<i></i>" for i in range(2))}</span><small>Evaluación experta · {e(r.get("nota", ""))}</small></div></li>')
    desglose = f'<div><dt>Medición automática</dt><dd>{ar["auto"] if ar["auto"] is not None else "–"}</dd></div>'
    if ar["rubrica"] is not None:
        desglose += f'<div><dt>Evaluación experta</dt><dd>{ar["rubrica"]}</dd></div>'
    sev_n = {s: sum(1 for h in mias if h["severidad"] == s) for s in SEVS}
    resumen = " · ".join(f"{v} {SEV_TXT[s].lower()}{'s' if v > 1 else ''}" for s, v in sev_n.items() if v) or "sin hallazgos"
    return f'''
<section class="area" id="area-{aid}">
  <div class="area__head rv">
    <div><span class="tag">03.{n} · {e(a["corto"])}</span><h2>{e(a["nombre"])}</h2><p class="area__q">{e(a["pregunta"])}</p>
      <p class="verdict">{rich(inf["areas"][aid]["veredicto"])}</p></div>
    <div class="card scorecard">{ring(ar["final"], ar["color"])}<span class="lbl c-{ar["color"]}" style="justify-self:start">{e(ar["etiqueta"])}</span>
      <small>{f'{len(mias)} hallazgo{"s" if len(mias) != 1 else ""}: {e(resumen)}' if mias else "Sin hallazgos prioritarios"}</small><dl>{desglose}</dl></div>
  </div>
  {panel}
  <div class="findings">{cards}</div>
  {mas}
  <details class="more"><summary>Ver las {items.count("<li")} revisiones de esta área</summary><ul class="mini">{items}</ul></details>
</section>'''


def sec_matriz(hs):
    vis = [h for h in hs if h.get("visible")]
    q = {"win": [], "key": [], "minor": [], "later": []}
    for h in vis:
        alto, facil = h["impacto"] >= 3, h["esfuerzo"] == 1
        q["win" if alto and facil else "key" if alto else "minor" if facil else "later"].append(h)

    def dots(lst):
        lst = sorted(lst, key=lambda h: SEVS.index(h["severidad"]))
        return "".join(f'<a class="dot dot--{h["severidad"]}" href="#h-{e(h["id"])}" data-tip="{e(h["titulo"])}">{e(h["id"])}</a>' for h in lst) or '<span class="tag">—</span>'
    quad = lambda k, t, d, extra="": f'<div class="card quad {extra}"><h4>{t}</h4><p>{d}</p><div class="dots">{dots(q[k])}</div></div>'  # noqa: E731
    return f'''
<section class="sec" id="matriz">
  <div class="sec__head rv"><span class="sec__n">04</span><h2>Qué hacer primero</h2>
    <p>Cada hallazgo, según lo que aporta y lo que cuesta resolverlo. Pase el cursor por un código para ver de qué se trata; tóquelo para ir al detalle.</p></div>
  <div class="matrix rv">
    <div class="matrix__y">Impacto →</div>
    <div class="matrix__grid">
      {quad("win", "Arreglos rápidos", "Mucho efecto, poco esfuerzo. Lo primero.", "quad--win")}
      {quad("key", "Proyectos clave", "Mucho efecto; requieren un proyecto de diseño o desarrollo.")}
      {quad("minor", "Mejoras de paso", "Efecto moderado y poco esfuerzo: conviene hacerlas junto con lo demás.")}
      {quad("later", "Mejoras planeadas", "Efecto moderado; se resuelven mejor dentro de un proyecto.")}
    </div>
    <div class="matrix__x">Esfuerzo →</div>
  </div>
</section>'''


def sec_paquete(inf, hs_by_id, hs):
    vis = [h for h in hs if h.get("visible")]
    todos, cols = [], ""
    orden = [k for k in inf["paquete"] if k in SERVICIOS["frentes"]] + [k for k in SERVICIOS["frentes"] if k not in inf["paquete"]]
    for i, (k, fr) in enumerate(((k, SERVICIOS["frentes"][k]) for k in orden), 1):
        r = inf["paquete"].get(k) or {}
        todos += [x for x in r.get("servicios", []) if x not in todos]
        svcs = "".join(f'<li><b>{e(SERVICIOS["servicios"][x]["nombre"])}</b><small>{e(SERVICIOS["servicios"][x]["que"])}</small></li>' for x in r.get("servicios", []))
        ids = "".join(f'<a class="dot dot--{hs_by_id[x]["severidad"]}" href="#h-{e(x)}" data-tip="{e(hs_by_id[x]["titulo"])}">{e(x)}</a>' for x in r.get("hallazgos", []) if x in hs_by_id and hs_by_id[x].get("visible"))
        cols += (f'<div class="front front--{i}"><span class="front__n">Frente {i}</span><h3>{e(fr["nombre"])}</h3><p>{e(fr["idea"])}</p>'
                 f'<ul class="front__svc">{svcs}</ul><div class="front__ids" aria-label="Hallazgos que atiende">{ids}</div>'
                 f'<p class="front__res">{rich(r.get("resultado", ""))}</p></div>')
    return f'''
<section class="sec" id="paquete">
  <div class="sec__head rv"><span class="sec__n">05</span><h2>Todo, en un solo paquete</h2>
    <p>Cada hallazgo de este diagnóstico tiene un servicio que lo resuelve. En lugar de atenderlos por separado, le proponemos resolverlos juntos, con un solo equipo.</p></div>
  <div class="card pack rv">
    <div class="pack__top">
      <div><span class="tag">Paquete Newemage para {e(inf["cliente"]["nombre"])}</span>
        <p>Tres frentes que se trabajan en conjunto y se ajustan a lo que {e(inf["cliente"]["nombre"])} necesita.</p></div>
      <ul class="pack__stats"><li><b>{len(vis)}</b>hallazgos atendidos</li><li><b>{len(todos)}</b>servicios</li><li><b>1</b>equipo</li></ul>
    </div>
    <div class="pack__fronts">{cols}</div>
    <div class="pack__foot">
      <ul><li>{ICON["check"]}Un solo interlocutor para todo el sitio</li><li>{ICON["check"]}Cada servicio atiende hallazgos concretos de este diagnóstico</li><li>{ICON["check"]}El alcance final lo definimos juntos</li></ul>
      <a class="btn btn--ink" href="#cierre">Armemos el paquete {ICON["arrow"]}</a>
    </div>
  </div>
</section>'''


def sec_competidores(rend, inf):
    comp = (rend or {}).get("competidores")
    if not comp:
        return ""
    yn = lambda b: '<span class="y">Sí</span>' if b else '<span class="n">No</span>'  # noqa: E731
    me = rend.get("clienteSenales") or {}
    mob = [m for m in rend["mediciones"] if m.get("puntuaciones") and m["strategy"] == "mobile"]
    filas = [(inf["cliente"]["nombre"], mob[0]["puntuaciones"]["performance"] if mob else None, me, True)] + [(c["nombre"], (c.get("movil") or {}).get("performance"), c.get("senales") or {}, False) for c in comp]
    tr = "".join(f'<tr><td class="{"me" if yo else ""}">{e(n)}</td><td>{v if v is not None else "–"}</td><td>{yn(s.get("descripcion"))}</td><td>{yn(s.get("jsonld"))}</td>'
                 f'<td>{yn(s.get("whatsapp"))}</td><td>{yn(s.get("ga4") or s.get("gtm"))}</td><td>{yn(s.get("metaPixel"))}</td><td>{yn(s.get("llmsTxt"))}</td></tr>' for n, v, s, yo in filas)
    return f'''
<section class="sec" id="comparativa">
  <div class="sec__head rv"><span class="sec__n">06</span><h2>Frente a su competencia</h2>
    <p>Las mismas señales básicas revisadas en la página de inicio de cada sitio, el mismo día.</p></div>
  <div class="tbl-wrap rv"><table><thead><tr><th>Sitio</th><th>Velocidad móvil</th><th>Descripción en Google</th><th>Datos estructurados</th><th>WhatsApp</th><th>Analítica</th><th>Píxel Meta</th><th>llms.txt</th></tr></thead><tbody>{tr}</tbody></table></div>
</section>'''


def sec_cierre(inf):
    c, a = inf["cierre"], inf["autor"]
    ini = "".join(x[0] for x in a["nombre"].split()[:2]).upper()
    wa = f'<a class="btn btn--ghost" href="https://wa.me/{re.sub(r"\D", "", a["whatsapp"])}">WhatsApp</a>' if a.get("whatsapp") else ""
    return f'''
<section class="on-dark close" id="cierre">
  <div class="mesh" aria-hidden="true"><span class="b1"></span><span class="b2"></span></div>
  <span class="tag">Siguiente paso</span>
  <h2>{rich(c["titular"], "text-gradient")}</h2>
  <p>{rich(c["texto"])}</p>
  <div class="hero__ctas"><a class="btn btn--warm" href="{e(c["enlace"])}">{e(c["cta"])} {ICON["arrow"]}</a>{wa}</div>
  <div class="author"><i aria-hidden="true">{e(ini)}</i><div><b>{e(a["nombre"])}</b><span>{e(a["puesto"])} · {e(a["email"])}</span></div></div>
</section>'''


def sec_anexo(inf, checks, sitio, hs):
    met = "".join(f'<li><b>{e(a["nombre"])}</b> — peso {a["peso"]:g} %. ' + (f'{round(a["mezcla"]["auto"] * 100)} % mediciones automáticas y {round(a["mezcla"]["rubrica"] * 100)} % evaluación experta con {len(REGLAS["rubricas"][aid])} criterios fijos.' if a["mezcla"]["rubrica"] else "100 % mediciones automáticas.") + "</li>"
                  for aid, a in sorted(REGLAS["areas"].items(), key=lambda x: x[1]["orden"]))
    filas = ""
    for cid, rc in REGLAS["checks"].items():
        c = checks[cid]
        filas += (f'<tr data-area="{rc["area"]}" data-st="{c["estado"]}"><td>{e(REGLAS["areas"][rc["area"]]["corto"])}</td><td>{e(rc["titulo"])}</td>'
                  f'<td><span class="st st--{c["estado"]}">{EST_TXT[c["estado"]]}</span></td><td>{e(c["detalle"])}</td></tr>')
    fa = '<button type="button" data-k="area" data-v="todas" aria-pressed="true">Todas</button>' + "".join(f'<button type="button" data-k="area" data-v="{k}" aria-pressed="false">{e(a["corto"])}</button>' for k, a in sorted(REGLAS["areas"].items(), key=lambda x: x[1]["orden"]))
    fe = '<button type="button" data-k="st" data-v="todos" aria-pressed="true">Todos</button>' + "".join(f'<button type="button" data-k="st" data-v="{k}" aria-pressed="false">{v}</button>' for k, v in EST_TXT.items())
    otros = [h for h in hs if not h.get("visible")]
    otros_html = "".join(f'<li><b>{e(h["titulo"] if MARCA not in h.get("titulo", MARCA) else h["_tecnico"]["check"])}</b> — {rich(h["que_vimos"] if MARCA not in h.get("que_vimos", MARCA) else h["_tecnico"]["detalle"])}</li>' for h in otros)
    pags = "".join(f'<li><a href="{e(p["url"])}" rel="noopener" target="_blank">{e(urlparse(p["url"]).path or "/")}</a></li>' for p in sitio["paginas"])
    glos = "".join(f"<li><b>{e(t)}</b>: {e(d)}</li>" for t, d in GLOSARIO)
    lim = "".join(f"<li>{rich(x)}</li>" for x in inf.get("limitaciones", []))
    return f'''
<section class="sec annex" id="anexo">
  <div class="sec__head rv"><span class="sec__n">Anexo</span><h2>El detalle</h2>
    <p>Para quien quiera revisar cómo se calificó y todo lo que se comprobó.</p></div>
  <details class="block"><summary>Cómo calificamos</summary><div class="body">
    <p>La calificación general es el promedio ponderado de las ocho áreas. Cada revisión automática vale según su peso y puede cumplirse por completo, a medias o no cumplirse; las evaluaciones expertas usan una escala de 0 a 2 por criterio, con una observación concreta en cada uno. Las severidades salen de reglas fijas, no de una opinión caso por caso.</p>
    <ul>{met}</ul>
    <p>Herramientas: recorrido con Google Chrome en computadora (1440 px) y teléfono (390 px); Google PageSpeed Insights / Lighthouse para velocidad; axe-core (WCAG 2.1 AA) para accesibilidad; revisión directa de robots.txt, sitemap, cabeceras del servidor y enlaces.</p>
  </div></details>
  <details class="block"><summary>Todas las revisiones ({len(REGLAS["checks"])})</summary><div class="body">
    <div class="filters" data-for="tbl-checks">{fa}</div><div class="filters" data-for="tbl-checks">{fe}</div>
    <div class="tbl-wrap"><table id="tbl-checks"><thead><tr><th>Área</th><th>Revisión</th><th>Resultado</th><th>Detalle</th></tr></thead><tbody>{filas}</tbody></table></div>
  </div></details>
  {f'<details class="block"><summary>Otros detalles de menor prioridad ({len(otros)})</summary><div class="body"><ul>{otros_html}</ul></div></details>' if otros else ''}
  <details class="block"><summary>Páginas revisadas ({len(sitio["paginas"])})</summary><div class="body"><ul>{pags}</ul></div></details>
  <details class="block"><summary>Límites de esta revisión</summary><div class="body"><ul>{lim}</ul></div></details>
  <details class="block"><summary>Glosario</summary><div class="body"><ul>{glos}</ul></div></details>
</section>'''


def construir(raiz: Path, solo_validar=False):
    inf = json.loads((raiz / "informe.json").read_text())
    err, warn = validar(inf, raiz)
    for w in warn:
        print("  ⚠", w)
    if err:
        print(f"\n✗ {len(err)} problema(s); no se construye:")
        for x in err:
            print("   ·", x)
        sys.exit(1)
    if solo_validar:
        print("✓ informe.json válido")
        return
    checks = json.loads((raiz / "analisis" / "checks.json").read_text())
    for cid in REGLAS["checks"]:  # checks añadidos a reglas.json después del análisis de este cliente
        if cid not in checks:
            print(f"  ⚠ {cid} no está en analisis/checks.json: corre analizar.py de nuevo. Se cuenta como «No aplica».")
            checks[cid] = {"estado": "na", "valor": None, "detalle": "No se evaluó en este análisis", "evidencia": [], "paginas": [], "datos": []}
    sitio = json.loads((raiz / "datos" / "sitio.json").read_text())
    rf = raiz / "datos" / "rendimiento.json"
    rend = json.loads(rf.read_text()) if rf.exists() else None
    areas, gen = puntuar(checks, inf.get("rubricas"))
    hs = inf["hallazgos"]
    hs_by_id = {h["id"]: h for h in hs}

    out = raiz / "presentacion"
    if out.exists():
        shutil.rmtree(out)
    (out / "assets" / "img").mkdir(parents=True)
    shutil.copytree(LOGOS, out / "assets" / "logos")
    M = Medios(raiz, out / "assets" / "img")

    orden = [aid for aid, _ in sorted(REGLAS["areas"].items(), key=lambda x: x[1]["orden"])]
    cuerpo_areas = "".join(sec_area(i, aid, inf, areas, checks, hs, M, rend) for i, aid in enumerate(orden, 1))
    comp = sec_competidores(rend, inf)
    css = (PLANTILLA / "estilos.css").read_text()
    js = (PLANTILLA / "app.js").read_text()
    c = inf["cliente"]
    pagina = f'''<!doctype html>
<html lang="es-MX">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Diagnóstico digital · {e(c["nombre"])} — Newemage</title>
<meta name="description" content="{e(re.sub(r"[*]", "", inf["resumen"]["parrafo"])[:200])}">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="assets/logos/icon-newemage.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wdth,wght@0,75..100,400..700;1,75..100,400..700&family=Inter:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
<script>document.documentElement.classList.add('js')</script>
<style>
{css}
</style>
</head>
<body>
<a class="skip" href="#resumen">Saltar al contenido</a>
<div class="nav" role="banner">
  <div class="wrap nav__row">
    <a class="nav__brand" href="#portada" aria-label="Newemage — ir al inicio">
      <img class="logo-dark" src="assets/logos/logo-newemage-white.svg" alt="Newemage" width="95" height="34">
      <img class="logo-light" src="assets/logos/logo-newemage-dark.svg" alt="" width="95" height="34" aria-hidden="true">
      <span class="nav__para">Diagnóstico digital · {e(c["nombre"])}</span>
    </a>
    <a class="btn btn--ink btn--sm nav__cta" href="#cierre">Hablemos</a>
  </div>
  <span class="progress" aria-hidden="true"></span>
</div>
{sec_hero(inf, gen, sitio, M, hs)}
<div class="layout">
{sec_toc(inf, areas, bool(comp))}
<main class="main" id="contenido">
{sec_resumen(inf, hs_by_id, hs, sitio)}
{sec_diseno(inf, sitio, M)}
{sec_tablero(inf, areas, hs)}
{cuerpo_areas}
{sec_matriz(hs)}
{sec_paquete(inf, hs_by_id, hs)}
{comp}
{sec_cierre(inf)}
{sec_anexo(inf, checks, sitio, hs)}
</main>
</div>
<footer class="foot"><img src="assets/logos/logo-newemage-dark.svg" alt="Newemage" width="84" height="30"><span>Diagnóstico elaborado para {e(c["nombre"])} · {e(inf["fecha"])} · Documento confidencial</span></footer>
<div class="lb" role="dialog" aria-modal="true" aria-label="Evidencia ampliada"><button type="button" class="lb__x" aria-label="Cerrar">×</button><div class="lb__box"><img alt="" hidden><p></p></div></div>
<script>
{js}
</script>
</body>
</html>
'''
    (out / "index.html").write_text(pagina)
    kb = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) // 1024
    vis = sum(1 for h in hs if h.get("visible"))
    print(f"✓ presentacion/index.html · general {gen['final']} ({gen['etiqueta']}) · {vis} hallazgos visibles · {len(M.cache)} imágenes · {kb} KB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 construir.py ../clientes/<slug> [--validar]")
    construir(Path(sys.argv[1]).resolve(), "--validar" in sys.argv)
