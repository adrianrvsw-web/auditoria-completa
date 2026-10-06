#!/usr/bin/env python3
"""
analizar.py — datos recolectados → checks deterministas → puntuaciones → resumen

    python3 analizar.py ../clientes/<slug>

Lee   datos/sitio.json, datos/paginas/*.json, datos/rendimiento.json (opcional)
Deja  analisis/checks.json        estado, valor (0–1), detalle y evidencia de cada check
      analisis/puntuaciones.json  puntuación automática por área
      analisis/resumen.md         lo que Claude lee antes de redactar
      informe.borrador.json       esqueleto del informe con los hallazgos automáticos
                                  (solo si todavía no existe informe.json)

Todo aquí es determinista: mismos datos, mismos checks, mismas severidades.
El modelo redacta; no elige la regla, el peso ni la severidad.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REGLAS = json.loads((HERE / "reglas.json").read_text())
SERVICIOS = json.loads((HERE / "servicios.json").read_text())
HOY = date.today()
SEV_ORDEN = ["baja", "media", "alta", "critica"]
PHP_EOL = {"5": "2018-12-31", "7.0": "2019-01-10", "7.1": "2019-12-01", "7.2": "2020-11-30", "7.3": "2021-12-06",
           "7.4": "2022-11-28", "8.0": "2023-11-26", "8.1": "2025-12-31", "8.2": "2026-12-31", "8.3": "2027-12-31", "8.4": "2028-12-31"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
LEGAL = re.compile(r"privacidad|privacy|aviso|terminos|t%C3%A9rminos|legal|cookies", re.I)
PLANTILLA = re.compile(r"responsive html5? template|lorem ipsum|just another wordpress|otro sitio realizado con wordpress|sample page|hello world|my blog|mi blog", re.I)


# ─────────────────────────────── carga ───────────────────────────────
class Datos:
    def __init__(self, raiz: Path):
        self.raiz = raiz
        d = raiz / "datos"
        self.sitio = json.loads((d / "sitio.json").read_text())
        self.cfg = json.loads((raiz / "config.json").read_text())
        rend = d / "rendimiento.json"
        self.rend = json.loads(rend.read_text()) if rend.exists() else None
        self.pags = []
        for p in self.sitio["paginas"]:
            f = d / "paginas" / f"{p['id']}.json"
            if not f.exists():
                continue
            j = json.loads(f.read_text())
            v = j.get("vistas", {})
            j["d"] = v.get("desktop") or {}
            j["m"] = v.get("mobile") or {}
            j["dd"] = j["d"].get("dom") or {}
            j["md"] = j["m"].get("dom") or {}
            j["ruta"] = urlparse(j["url"]).path or "/"
            j["legal"] = bool(LEGAL.search(j["url"]))
            self.pags.append(j)
        self.home = self.pags[0] if self.pags else {}

    @property
    def utiles(self):
        return [p for p in self.pags if p["dd"] and not p["d"].get("error")]


def R(estado, valor, detalle, evidencia=None, severidad=None, paginas=None, datos=None):
    return {"estado": estado, "valor": round(float(valor), 3) if valor is not None else None, "detalle": detalle,
            "evidencia": evidencia or [], "severidad": severidad, "paginas": paginas or [], "datos": datos or []}


NA = lambda motivo: R("na", None, motivo)  # noqa: E731


def ratio_estado(ok, total, detalle, **kw):
    if total == 0:
        return NA("Sin páginas aplicables")
    v = ok / total
    return R("ok" if v >= 0.999 else ("parcial" if v >= 0.5 else "falla"), v, detalle, **kw)


def rutas(ps):
    return [p["ruta"] for p in ps]


def de_n(n, total, cosa="páginas"):
    return f"{n} de {total} {cosa}"


def dias_desde(s):
    try:
        f = datetime.fromisoformat(s.replace("Z", "+00:00")[:25])
        if f.tzinfo is None:
            f = f.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - f).days
    except Exception:
        return None


def ver(s):
    try:
        return tuple(int(x) for x in re.findall(r"\d+", s)[:3])
    except Exception:
        return ()


# ─────────────────────────────── checks ──────────────────────────────
CHECKS = {}


def check(cid):
    def deco(f):
        CHECKS[cid] = f
        return f
    return deco


# ── UX ──
@check("ux.viewport")
def _(D):
    malas = [p for p in D.utiles if "width=device-width" not in (p["md"].get("viewportMeta") or "")]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles),
                        "Todas las páginas declaran viewport para teléfono" if not malas else f"Sin viewport móvil en {de_n(len(malas), len(D.utiles))}",
                        paginas=rutas(malas))


@check("ux.desborde_movil")
def _(D):
    malas = [p for p in D.utiles if (p["md"].get("desborde") or {}).get("excede")]
    ev = [f"{p['ruta']}: ancho {p['md']['desborde']['anchoDoc']}px en pantalla de 390px · {', '.join(p['md']['desborde']['elementos'][:2])}" for p in malas]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Sin desbordes horizontales" if not malas else f"La página se sale de la pantalla en {de_n(len(malas), len(D.utiles))}",
                        evidencia=ev, paginas=rutas(malas))


@check("ux.capa_bloquea")
def _(D):
    malas = []
    for p in D.utiles:
        for vp in ("dd", "md"):
            c = p[vp].get("capaCentro")
            if c:
                malas.append((p, vp, c))
    if not malas:
        return R("ok", 1, "Nada tapa el contenido al llegar")
    ev = [f"{p['ruta']} ({'escritorio' if vp == 'dd' else 'teléfono'}): cubre {c['cubre']} % · «{c['txt'][:80]}»" for p, vp, c in malas]
    ps = {p["ruta"] for p, _, _ in malas}
    return R("falla" if len(ps) > 1 else "parcial", 1 - len(ps) / len(D.utiles), f"Una capa tapa el centro de la pantalla al llegar en {len(ps)} página(s)", ev, paginas=sorted(ps))


@check("ux.fijos_movil")
def _(D):
    malas = [p for p in D.utiles if (p["md"].get("fijos") or {}).get("pctPantalla", 0) > 25]
    ev = [f"{p['ruta']}: {p['md']['fijos']['pctPantalla']} % de la pantalla · " + " | ".join(f"«{x['txt'][:40]}» {x['pct']}%" for x in p["md"]["fijos"]["lista"][:3]) for p in malas]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Barras fijas contenidas" if not malas else f"Elementos fijos ocupan más de un cuarto del teléfono en {de_n(len(malas), len(D.utiles))}", evidencia=ev, paginas=rutas(malas))


@check("ux.texto_pequeno")
def _(D):
    malas = [p for p in D.utiles if (p["md"].get("textoPequeno") or {}).get("pct", 0) > 10]
    ev = [f"{p['ruta']}: {p['md']['textoPequeno']['pct']} % del texto < 12px · " + "; ".join(p["md"]["textoPequeno"]["muestra"][:2]) for p in malas]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Tamaños de texto legibles" if not malas else f"Texto demasiado pequeño en teléfono en {de_n(len(malas), len(D.utiles))}", evidencia=ev, paginas=rutas(malas))


@check("ux.objetivos_tactiles")
def _(D):
    ns = [(p, (p["md"].get("objetivosChicos") or {}).get("total", 0)) for p in D.utiles]
    if not ns:
        return NA("Sin datos móviles")
    prom = statistics.mean(n for _, n in ns)
    v = max(0.0, 1 - prom / 40)
    peor = max(ns, key=lambda x: x[1])
    return R("ok" if prom <= 8 else ("parcial" if prom <= 25 else "falla"), v, f"Promedio de {prom:.0f} botones/enlaces menores a 24px por página en teléfono",
             [f"{peor[0]['ruta']}: {peor[1]} · ej. " + ", ".join((peor[0]['md'].get('objetivosChicos') or {}).get('muestra', [])[:5])])


@check("ux.imagenes_rotas")
def _(D):
    malas = [(p, (p["dd"].get("imagenes") or {}).get("rotas", [])) for p in D.utiles]
    malas = [(p, r) for p, r in malas if r]
    if not malas:
        return R("ok", 1, "Todas las imágenes cargan")
    return R("falla", 1 - len(malas) / len(D.utiles), f"Imágenes rotas en {de_n(len(malas), len(D.utiles))}", [f"{p['ruta']}: {r[0]}" for p, r in malas], paginas=rutas(p for p, _ in malas))


# ── Leads ──
def forms_contacto(D):
    out = []
    for p in D.utiles:
        for f in p["dd"].get("formularios", []):
            if f["clase"] == "contacto" and f["visible"] and f["nCampos"] >= 2:
                out.append((p, f))
    return out


@check("leads.formulario")
def _(D):
    fc = forms_contacto(D)
    ifr = [(p, x) for p in D.utiles for x in p["dd"].get("iframesForm", [])]
    if fc or ifr:
        donde = sorted({p["ruta"] for p, _ in fc + ifr})
        return R("ok", 1, f"Formulario de contacto en {', '.join(donde[:4])}", paginas=donde)
    login = [(p, f) for p in D.utiles for f in p["dd"].get("formularios", []) if f["clase"] == "login"]
    cot = [p for p in D.utiles if re.search(r"cotiz|contact|quote", p["url"], re.I)]
    ev = []
    if login:
        ev.append("Solo se encontraron formularios de inicio de sesión: " + ", ".join(sorted({p['ruta'] for p, _ in login})))
    if cot:
        ev.append("Páginas de contacto/cotización revisadas: " + ", ".join(rutas(cot)))
    return R("falla", 0, "No hay un formulario para pedir información sin crear cuenta", ev, severidad="critica" if login else None)


@check("leads.cta_home")
def _(D):
    h = D.home
    if not h:
        return NA("Sin home")
    dk = (h["dd"].get("ctas") or {}).get("pliegueFuertes", [])
    mb = (h["md"].get("ctas") or {}).get("pliegueFuertes", [])
    datos = [{"k": "Escritorio", "v": ", ".join(dk[:3]) or "ninguna"}, {"k": "Teléfono", "v": ", ".join(mb[:3]) or "ninguna"}]
    if dk and mb:
        return R("ok", 1, "Acción de contacto visible al llegar en ambas pantallas", datos=datos)
    if dk or mb:
        return R("parcial", 0.5, f"Acción de contacto visible al llegar solo en {'escritorio' if dk else 'teléfono'}", datos=datos)
    return R("falla", 0, "La home no muestra ninguna acción de contacto sin desplazarse", [f"Botones visibles al llegar: {', '.join((h['dd'].get('ctas') or {}).get('pliegue', [])[:5]) or 'ninguno'}"], datos=datos)


@check("leads.cta_paginas")
def _(D):
    ps = [p for p in D.utiles if not p["legal"]]
    ok = [p for p in ps if (p["dd"].get("ctas") or {}).get("fuertes", 0) > 0 or any(f["clase"] == "contacto" for f in p["dd"].get("formularios", []))]
    sin = [p for p in ps if p not in ok]
    return ratio_estado(len(ok), len(ps), f"{de_n(len(ok), len(ps))} tienen una acción de contacto clara", paginas=rutas(sin),
                        evidencia=[f"Sin acción clara: {', '.join(rutas(sin)[:6])}"] if sin else [])


@check("leads.campos")
def _(D):
    fc = forms_contacto(D)
    if not fc:
        return NA("Sin formularios de contacto")
    largos = [(p, f) for p, f in fc if f["nCampos"] > 7]
    datos = [{"k": p["ruta"], "v": f"{f['nCampos']} campos, {f['obligatorios']} obligatorios"} for p, f in fc[:4]]
    return R("ok" if not largos else "falla", 1 - len(largos) / len(fc), "Formularios cortos" if not largos else f"{len(largos)} formulario(s) con más de 7 campos", datos=datos, paginas=rutas(p for p, _ in largos))


@check("leads.aviso_privacidad")
def _(D):
    fc = forms_contacto(D)
    if not fc:
        return NA("Sin formularios de contacto")
    sin = [(p, f) for p, f in fc if not f["avisoPrivacidad"]]
    return R("ok" if not sin else "falla", 1 - len(sin) / len(fc), "Aviso de privacidad junto a los formularios" if not sin else f"{len(sin)} formulario(s) sin aviso de privacidad a la vista", paginas=rutas(p for p, _ in sin))


@check("leads.antispam")
def _(D):
    fc = forms_contacto(D)
    if not fc:
        return NA("Sin formularios de contacto")
    sin = [(p, f) for p, f in fc if not f["captcha"]]
    return R("ok" if not sin else "falla", 1 - len(sin) / len(fc), "Formularios protegidos" if not sin else f"{len(sin)} formulario(s) sin reCAPTCHA u otra protección visible", paginas=rutas(p for p, _ in sin))


@check("leads.whatsapp")
def _(D):
    con = [p for p in D.utiles if (p["dd"].get("contacto") or {}).get("whatsapp", 0) > 0 or any("WhatsApp" in c for c in p["d"].get("chat", []))]
    flot = any((p["dd"].get("contacto") or {}).get("whatsFlotante") for p in D.utiles)
    if not con:
        return R("falla", 0, "No hay forma de escribir por WhatsApp desde el sitio")
    v = len(con) / len(D.utiles)
    return R("ok" if flot or v >= 0.8 else "parcial", 1 if flot else max(0.5, v), f"WhatsApp en {de_n(len(con), len(D.utiles))}" + (" (botón flotante)" if flot else " (sin botón flotante)"))


@check("leads.whatsapp_pais")
def _(D):
    con = [p for p in D.utiles if (p["dd"].get("contacto") or {}).get("whatsNums")]
    if not con:
        return NA("Sin enlaces de WhatsApp")
    malas = [p for p in con if p["dd"]["contacto"].get("whatsSinPais")]
    n = sorted({w for p in malas for w in p["dd"]["contacto"]["whatsSinPais"]})
    ev = [f"{p['ruta']}: wa.me/{', wa.me/'.join(p['dd']['contacto']['whatsSinPais'][:3])}" for p in malas]
    return R("ok", 1, "Los enlaces de WhatsApp llevan la clave de país") if not malas else \
        R("falla", 0, f"{len(n)} enlace(s) de WhatsApp sin clave de país en {de_n(len(malas), len(con))}: WhatsApp no los reconoce", evidencia=ev, paginas=rutas(malas))


@check("leads.tel_clicable")
def _(D):
    con_tel = [p for p in D.utiles if (p["md"].get("contacto") or {}).get("telsTexto")]
    if not con_tel:
        return NA("No se muestran teléfonos en texto")
    def sin_enlace(p):  # un número enlazado a WhatsApp también cuenta como enlazado
        wa = (p["md"]["contacto"].get("whatsNums") or []) + ((p["dd"].get("contacto") or {}).get("whatsNums") or [])
        return [x for x in p["md"]["contacto"]["telsSinEnlace"] if not any(w.endswith(x) for w in wa)]
    malas = [p for p in con_tel if sin_enlace(p)]
    ev = [f"{p['ruta']}: {', '.join(sin_enlace(p)[:3])}" for p in malas]
    return ratio_estado(len(con_tel) - len(malas), len(con_tel), "Teléfonos clicables" if not malas else f"Teléfonos sin enlace para llamar en {de_n(len(malas), len(con_tel))}", evidencia=ev, paginas=rutas(malas))


@check("leads.contacto_menu")
def _(D):
    nav = (D.home.get("dd") or {}).get("nav", [])
    hit = [n["txt"] for n in nav if re.search(r"contact|cotiz|presupuesto|agenda", n["txt"] + " " + n["href"], re.I)]
    return R("ok", 1, f"En el menú: {', '.join(hit[:2])}") if hit else R("falla", 0, "El menú principal no tiene contacto ni cotización")


def medicion_total(D):
    herr = sorted({m for p in D.utiles for vp in ("d", "m") for m in p[vp].get("medicion", [])})
    ids = {k: sorted({i for p in D.utiles for i in (p["dd"].get("idsMedicion") or {}).get(k, []) if isinstance(i, str)}) for k in ("ga4", "ua", "gtm", "ads")}
    return herr, ids


@check("leads.medicion")
def _(D):
    herr, ids = medicion_total(D)
    datos = [{"k": "Herramientas detectadas", "v": ", ".join(herr) or "ninguna"}]
    if "GA4" in herr or "Google Tag Manager" in herr or ids["ga4"] or ids["gtm"]:
        return R("ok", 1, "Analítica activa: " + ", ".join(herr or ids["ga4"] + ids["gtm"]), datos=datos)
    if ids["ua"] or any("Universal" in h for h in herr):
        return R("falla", 0, "Solo tiene Universal Analytics, que Google apagó en julio de 2023: no se está midiendo nada", severidad="critica", datos=datos)
    return R("falla", 0, "No se detectó ninguna herramienta de analítica: no hay forma de saber cuántos contactos llegan del sitio", datos=datos)


@check("leads.pixeles")
def _(D):
    herr, ids = medicion_total(D)
    px = [h for h in herr if h in ("Meta Pixel", "Google Ads", "LinkedIn Insight", "TikTok Pixel")]
    return R("ok", 1, "Píxeles: " + ", ".join(px)) if px else R("falla", 0, "Sin píxeles de publicidad: no se pueden crear audiencias ni medir campañas")


# ── SEO ──
@check("seo.indexable")
def _(D):
    if D.sitio["robots"].get("bloqueaTodo"):
        return R("falla", 0, "robots.txt bloquea todo el sitio a los buscadores", severidad="critica")
    malas = [p for p in D.utiles if re.search(r"noindex", (p["dd"].get("robots") or "") + " " + str((p.get("cabeceras") or {}).get("x-robots-tag", "")), re.I) and not p["legal"]]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Indexable" if not malas else f"Páginas marcadas para no aparecer en Google: {', '.join(rutas(malas))}", paginas=rutas(malas),
                        severidad="critica" if D.home in malas else None)


@check("seo.titulos")
def _(D):
    ts = [(p, (p["dd"].get("titulo") or "").strip()) for p in D.utiles]
    cnt = {}
    for _, t in ts:
        cnt[t] = cnt.get(t, 0) + 1
    malas, ev = [], []
    for p, t in ts:
        prob = []
        if not t:
            prob.append("sin título")
        elif len(t) < 20:
            prob.append(f"corto ({len(t)})")
        elif len(t) > 65:
            prob.append(f"largo ({len(t)})")
        if t and cnt[t] > 1:
            prob.append("repetido")
        if prob:
            malas.append(p)
            ev.append(f"{p['ruta']}: «{t[:70]}» — {', '.join(prob)}")
    return ratio_estado(len(ts) - len(malas), len(ts), "Títulos correctos" if not malas else f"Títulos con problemas en {de_n(len(malas), len(ts))}", evidencia=ev, paginas=rutas(malas))


@check("seo.descripciones")
def _(D):
    ds = [(p, (p["dd"].get("descripcion") or "").strip()) for p in D.utiles]
    cnt = {}
    for _, d in ds:
        cnt[d] = cnt.get(d, 0) + 1
    malas, ev, plantilla = [], [], False
    for p, d in ds:
        prob = []
        if not d:
            prob.append("sin descripción")
        elif PLANTILLA.search(d):
            prob.append("texto de la plantilla"); plantilla = True
        elif len(d) < 70:
            prob.append(f"corta ({len(d)})")
        if d and cnt[d] > 1:
            prob.append(f"repetida en {cnt[d]} páginas")
        if prob:
            malas.append(p)
            ev.append(f"{p['ruta']}: «{d[:90]}» — {', '.join(prob)}")
    r = ratio_estado(len(ds) - len(malas), len(ds), "Descripciones propias" if not malas else f"Descripciones con problemas en {de_n(len(malas), len(ds))}", evidencia=ev, paginas=rutas(malas))
    if plantilla:
        r["severidad"] = "alta"
    return r


@check("seo.h1")
def _(D):
    malas, ev = [], []
    for p in D.utiles:
        h = [x for x in p["dd"].get("h1", []) if x.strip()]
        vacios = len(p["dd"].get("h1", [])) - len(h)
        if len(h) != 1:
            malas.append(p)
            ev.append(f"{p['ruta']}: {len(h)} H1 con texto" + (f" ({' | '.join(x[:30] for x in h[:3])})" if h else "") + (f" y {vacios} vacío(s)" if vacios else ""))
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Un H1 por página" if not malas else f"Encabezado principal ausente o duplicado en {de_n(len(malas), len(D.utiles))}", evidencia=ev, paginas=rutas(malas))


@check("seo.canonical")
def _(D):
    malas = [p for p in D.utiles if not p["dd"].get("canonical")]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Canónicas declaradas" if not malas else f"Sin canónica en {de_n(len(malas), len(D.utiles))}", paginas=rutas(malas))


@check("seo.sitemap")
def _(D):
    sm = D.sitio["sitemap"]
    if sm["encontrados"]:
        return R("ok", 1, f"Sitemap con {sm['urls']} URLs", datos=[{"k": "Sitemap", "v": sm["encontrados"][0]}])
    return R("falla", 0, "No existe sitemap.xml: Google tiene que adivinar qué páginas hay")


@check("seo.robots")
def _(D):
    rb = D.sitio["robots"]
    if not rb["existe"]:
        return R("falla", 0, "No hay robots.txt" + (" (la dirección devuelve una página HTML)" if rb.get("status") == 200 else ""))
    if not rb["sitemaps"]:
        return R("parcial", 0.5, "robots.txt existe pero no declara el sitemap")
    return R("ok", 1, "robots.txt con sitemap declarado")


@check("seo.schema")
def _(D):
    tipos = sorted({t for p in D.utiles for t in (p["dd"].get("jsonld") or {}).get("tipos", [])})
    org = any((p["dd"].get("jsonld") or {}).get("organizacion") for p in D.utiles)
    inval = sum((p["dd"].get("jsonld") or {}).get("invalidos", 0) for p in D.utiles)
    datos = [{"k": "Tipos encontrados", "v": ", ".join(tipos[:8]) or "ninguno"}]
    if org and not inval:
        return R("ok", 1, "Datos estructurados con la empresa descrita", datos=datos)
    if tipos:
        return R("parcial", 0.5, "Hay datos estructurados, pero no describen a la empresa" + (f" ({inval} bloque(s) inválido(s))" if inval else ""), datos=datos)
    return R("falla", 0, "Ninguna página tiene datos estructurados (schema.org)", datos=datos)


@check("seo.og")
def _(D):
    og = D.home.get("dd", {}).get("og") or {}
    n = bool(og.get("titulo")) + bool(og.get("imagen"))
    return R(["falla", "parcial", "ok"][n], n / 2, ["Sin vista previa al compartir en WhatsApp/redes", "Vista previa incompleta (falta " + ("imagen" if og.get("titulo") else "título") + ")", "Vista previa configurada"][n])


@check("seo.lang")
def _(D):
    malas = [p for p in D.utiles if not p["dd"].get("lang")]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Idioma declarado" if not malas else f"Sin idioma declarado en {de_n(len(malas), len(D.utiles))}", paginas=rutas(malas))


@check("seo.error404")
def _(D):
    e = D.sitio["error404"]
    return R("falla", 0, "Una dirección inexistente responde «200 OK»: Google puede indexar páginas vacías") if e["soft404"] else R("ok", 1, f"Responde {e['status']}")


@check("seo.enlaces_rotos")
def _(D):
    rotos = D.sitio.get("enlaces", {}).get("rotosInternos", [])
    anclas = [(p, a) for p in D.utiles for a in (p["dd"].get("enlaces") or {}).get("anclasRotas", [])]
    ev = [f"{x['url']} → {x['status']}" for x in rotos[:8]] + [f"{p['ruta']}: ancla {a} no existe" for p, a in anclas[:5]]
    n = D.sitio.get("enlaces", {}).get("internosRevisados", 0)
    if not rotos and not anclas:
        return R("ok", 1, f"{n} enlaces internos revisados, ninguno roto")
    return R("falla", max(0, 1 - (len(rotos) + len(anclas)) / max(n, 10)), f"{len(rotos)} enlace(s) interno(s) roto(s) y {len(anclas)} ancla(s) sin destino", ev)


@check("seo.canonicalizacion")
def _(D):
    vs = D.sitio["variantes"]
    finales = {urlparse(v["final"] or "").netloc for v in vs if v["statusFinal"] and v["statusFinal"] < 400}
    caidas = [v["desde"] for v in vs if not v["statusFinal"]]
    ev = [f"{v['desde']} → {v['final']} ({v['statusFinal'] or 'no responde'})" for v in vs]
    if caidas:
        return R("falla", 0.5, f"{', '.join(sorted({urlparse(c).netloc for c in caidas}))} no responde: quien lo escriba así no llega al sitio", ev)
    if len(finales) > 1:
        return R("falla", 0.3, "El dominio responde en varias versiones sin redirigir a una sola", ev)
    return R("ok", 1, "Todas las variantes llevan a " + next(iter(finales), "?"), ev)


@check("seo.contenido")
def _(D):
    ps = [p for p in D.utiles if not p["legal"] and not re.search(r"contact|cotiz|login|gracias", p["url"], re.I)]
    malas = [p for p in ps if p["dd"].get("palabras", 0) < 250]
    return ratio_estado(len(ps) - len(malas), len(ps), "Texto suficiente" if not malas else f"Poco texto (< 250 palabras) en {de_n(len(malas), len(ps))}",
                        evidencia=[f"{p['ruta']}: {p['dd'].get('palabras', 0)} palabras" for p in malas], paginas=rutas(malas))


# ── GEO ──
BOTS_BUSQUEDA = ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Claude-SearchBot", "ClaudeBot", "GPTBot", "Google-Extended"]


@check("geo.bots_ia")
def _(D):
    b = D.sitio["robots"]["botsIA"]
    bloq = [x for x in BOTS_BUSQUEDA if b.get(x) == "bloqueado"]
    datos = [{"k": x, "v": b.get(x, "permitido")} for x in BOTS_BUSQUEDA]
    if not bloq:
        return R("ok", 1, "Ningún buscador de IA está bloqueado", datos=datos)
    return R("falla" if len(bloq) > 3 else "parcial", 1 - len(bloq) / len(BOTS_BUSQUEDA), f"robots.txt bloquea a: {', '.join(bloq)}", datos=datos)


@check("geo.sin_js")
def _(D):
    ps = [p for p in D.utiles if p.get("crudo")]
    malas, ev = [], []
    for p in ps:
        rend, cru = p["dd"].get("palabrasTotal", 0), p["crudo"].get("palabras", 0)
        if rend > 80 and cru / rend < 0.5:
            malas.append(p)
            ev.append(f"{p['ruta']}: {cru} palabras sin JavaScript vs {rend} con JavaScript")
    return ratio_estado(len(ps) - len(malas), len(ps), "El texto está en el HTML" if not malas else f"El texto depende de JavaScript en {de_n(len(malas), len(ps))}", evidencia=ev, paginas=rutas(malas))


@check("geo.entidad")
def _(D):
    org = next(((p["dd"].get("jsonld") or {}).get("organizacion") for p in D.utiles if (p["dd"].get("jsonld") or {}).get("organizacion")), None)
    if not org:
        return R("falla", 0, "El sitio no describe a la empresa en formato que las IA entiendan (schema Organization/LocalBusiness)")
    campos = {"nombre": org["nombre"], "teléfono": org["telefono"], "dirección": org["direccion"], "redes (sameAs)": org["sameAs"] > 0}
    n = sum(bool(v) for v in campos.values())
    falta = [k for k, v in campos.items() if not v]
    return R("ok" if n == 4 else "parcial", n / 4, f"Entidad {org['tipo']}" + (f"; falta {', '.join(falta)}" if falta else " completa"))


@check("geo.llms_txt")
def _(D):
    return R("ok", 1, "llms.txt publicado") if D.sitio["llmsTxt"]["existe"] else R("falla", 0, "Sin llms.txt (estándar emergente: todavía opcional)")


@check("geo.faq")
def _(D):
    faq_schema = any("FAQPage" in (p["dd"].get("jsonld") or {}).get("tipos", []) for p in D.utiles)
    preguntas = sum(1 for p in D.utiles for h in p["dd"].get("h2", []) if "?" in h)
    faq_nav = any(re.search(r"preguntas|faq", n["txt"], re.I) for n in D.home.get("dd", {}).get("nav", []))
    if faq_schema or preguntas >= 3 or faq_nav:
        return R("ok", 1, "Hay preguntas frecuentes" + (" con schema FAQPage" if faq_schema else ""))
    return R("falla", 0, "No hay preguntas frecuentes: es el formato que más citan los buscadores con IA")


@check("geo.nosotros")
def _(D):
    hit = [n["txt"] for n in D.home.get("dd", {}).get("nav", []) if re.search(r"nosotros|about|qui[eé]nes|empresa|historia|con[oó]cenos", n["txt"] + n["href"], re.I)]
    return R("ok", 1, f"Página institucional: {hit[0]}") if hit else R("falla", 0, "No hay una página que explique quién es la empresa")


# ── Rendimiento ──
def psi(D, url=None, strategy="mobile"):
    if not D.rend:
        return []
    url = url or D.home.get("url")
    return [m for m in D.rend["mediciones"] if m.get("puntuaciones") and m["url"] == url and m["strategy"] == strategy]


@check("rend.psi_movil")
def _(D):
    ms = psi(D)
    if not ms:
        return NA("Sin medición de PageSpeed")
    ps = [m["puntuaciones"]["performance"] for m in ms]
    v = statistics.mean(ps)
    rango = f"{min(ps)}–{max(ps)}" if len(ps) > 1 and max(ps) != min(ps) else str(ps[0])
    sev = "critica" if v < 30 else ("alta" if v < 50 else "media")
    return R("ok" if v >= 90 else ("parcial" if v >= 50 else "falla"), v / 100, f"Velocidad en teléfono: {rango}/100 ({len(ps)} mediciones)", severidad=sev,
             datos=[{"k": "PageSpeed móvil", "v": f"{rango}/100"}])


@check("rend.psi_escritorio")
def _(D):
    ms = psi(D, strategy="desktop")
    if not ms:
        return NA("Sin medición de PageSpeed")
    v = ms[0]["puntuaciones"]["performance"]
    return R("ok" if v >= 90 else ("parcial" if v >= 50 else "falla"), v / 100, f"Velocidad en computadora: {v}/100", datos=[{"k": "PageSpeed escritorio", "v": f"{v}/100"}])


@check("rend.campo")
def _(D):
    ms = psi(D)
    c = next((m.get("campoOrigen") for m in ms if m.get("campoOrigen")), None)
    if not c:
        return NA("Google no tiene suficientes visitas reales registradas de este sitio (Chrome UX Report)")
    umbrales = {"lcp": 2500, "inp": 200, "cls": 25}  # CrUX reporta CLS ×100
    res, datos = [], []
    for k, u in umbrales.items():
        m = c.get(k)
        if not m:
            continue
        ok = m["p75"] <= u
        res.append(ok)
        val = f"{m['p75'] / 1000:.1f} s" if k == "lcp" else (f"{m['p75']} ms" if k == "inp" else f"{m['p75'] / 100:.2f}")
        datos.append({"k": k.upper() + " real", "v": f"{val} · {'bien' if ok else 'mal'}"})
    if not res:
        return NA("Datos de campo incompletos")
    v = sum(res) / len(res)
    return R("ok" if v == 1 else ("parcial" if v >= 0.5 else "falla"), v, f"Usuarios reales (p75): {sum(res)} de {len(res)} métricas aprobadas", datos=datos)


@check("rend.lcp")
def _(D):
    ms = psi(D)
    if not ms or not ms[0]["laboratorio"].get("lcp"):
        return NA("Sin LCP de laboratorio")
    lcp = statistics.median(m["laboratorio"]["lcp"] for m in ms if m["laboratorio"].get("lcp"))
    v = 1 if lcp <= 2500 else max(0, 1 - (lcp - 2500) / 5500)
    return R("ok" if lcp <= 2500 else ("parcial" if lcp <= 4000 else "falla"), v, f"El contenido principal aparece a los {lcp / 1000:.1f} s en teléfono (laboratorio)",
             [f"Elemento: {ms[0]['laboratorio'].get('elementoLCP') or 's/d'}"], datos=[{"k": "LCP móvil", "v": f"{lcp / 1000:.1f} s"}])


@check("rend.peso")
def _(D):
    pesos = [(p, p["d"].get("red", {}).get("bytes", 0)) for p in D.utiles if p["d"].get("red")]
    if not pesos:
        return NA("Sin datos de red")
    med = statistics.median(b for _, b in pesos) / 1048576
    peor = max(pesos, key=lambda x: x[1])
    v = 1 if med <= 2.5 else max(0, 1 - (med - 2.5) / 5.5)
    return R("ok" if med <= 2.5 else ("parcial" if med <= 5 else "falla"), v, f"Peso mediano por página: {med:.1f} MB",
             [f"Más pesada: {peor[0]['ruta']} con {peor[1] / 1048576:.1f} MB"] + [f"{x['kb']} KB · {x['url'][-70:]}" for x in peor[0]["d"]["red"].get("masPesadas", [])[:3]],
             datos=[{"k": "Peso mediano", "v": f"{med:.1f} MB"}])


@check("rend.imagenes")
def _(D):
    leg = {x["url"]: x["kb"] for p in D.utiles for x in p["d"].get("red", {}).get("imagenesLegado", [])}
    sob = {x["src"]: x for p in D.utiles for x in (p["dd"].get("imagenes") or {}).get("sobredimensionadas", [])}
    n = len(leg) + len(sob)
    if n == 0:
        return R("ok", 1, "Imágenes optimizadas")
    ev = [f"{kb} KB en JPG/PNG · {u[-60:]}" for u, kb in sorted(leg.items(), key=lambda x: -x[1])[:4]] + [f"Se descarga a {x['natural']} y se muestra a {x['mostrada']} · {s[-50:]}" for s, x in list(sob.items())[:3]]
    return R("falla" if n > 5 else "parcial", max(0, 1 - n / 12), f"{len(leg)} imagen(es) pesadas en formato antiguo y {len(sob)} mucho más grandes de lo que se muestran", ev,
             datos=[{"k": "KB ahorrables (aprox.)", "v": f"~{int(sum(leg.values()) * 0.6)} KB"}] if leg else [])


@check("rend.compresion")
def _(D):
    enc = (D.sitio.get("cabeceras") or {}).get("content-encoding", "")
    return R("ok", 1, f"Compresión {enc}") if re.search(r"br|gzip|zstd|deflate", enc) else R("falla", 0, "El servidor no comprime el HTML")


@check("rend.terceros")
def _(D):
    ns = [len(p["d"].get("red", {}).get("terceros", [])) for p in D.utiles if p["d"].get("red")]
    if not ns:
        return NA("Sin datos de red")
    prom = statistics.mean(ns)
    todos = sorted({t for p in D.utiles for t in p["d"].get("red", {}).get("terceros", [])})
    return R("ok" if prom <= 10 else ("parcial" if prom <= 20 else "falla"), 1 if prom <= 10 else max(0, 1 - (prom - 10) / 20), f"{prom:.0f} dominios externos por página en promedio", [", ".join(todos[:15])])


# ── Técnica ──
@check("tec.https")
def _(D):
    if not D.sitio["home"].startswith("https"):
        return R("falla", 0, "El sitio no usa https: el navegador lo marca como «No seguro»")
    http = [v for v in D.sitio["variantes"] if v["desde"].startswith("http:") and v["statusFinal"]]
    malas = [v for v in http if not (v["final"] or "").startswith("https")]
    return R("ok", 1, "https activo y forzado") if not malas else R("falla", 0.4, "La versión http no redirige a https", [f"{v['desde']} → {v['final']}" for v in malas], severidad="alta")


@check("tec.certificado")
def _(D):
    t = D.sitio.get("tls") or {}
    if t.get("error"):
        return R("falla", 0, f"No se pudo validar el certificado ({t['error']})")
    try:
        venc = datetime.strptime(t["validoHasta"].replace("  ", " "), "%b %d %H:%M:%S %Y %Z").date()
    except Exception:
        return NA("Fecha de certificado ilegible")
    dias = (venc - HOY).days
    datos = [{"k": "Certificado", "v": f"{t.get('emisor')} · vence {venc.isoformat()} · {t.get('protocolo')}"}]
    if dias < 0:
        return R("falla", 0, "El certificado SSL está vencido", severidad="critica", datos=datos)
    return R("ok" if dias >= 21 else "falla", 1 if dias >= 21 else 0.3, f"Vence en {dias} días", datos=datos)


@check("tec.hsts")
def _(D):
    return R("ok", 1, "HSTS activo") if (D.sitio.get("cabeceras") or {}).get("strict-transport-security") else R("falla", 0, "Sin HSTS")


@check("tec.cabeceras")
def _(D):
    h = D.sitio.get("cabeceras") or {}
    tiene = {"X-Content-Type-Options": bool(h.get("x-content-type-options")),
             "Protección contra iframes (X-Frame-Options / CSP)": bool(h.get("x-frame-options")) or "frame-ancestors" in h.get("content-security-policy", ""),
             "Referrer-Policy": bool(h.get("referrer-policy"))}
    n = sum(tiene.values())
    falta = [k for k, v in tiene.items() if not v]
    return R("ok" if n == 3 else ("parcial" if n else "falla"), n / 3, "Cabeceras básicas presentes" if not falta else f"Faltan: {', '.join(falta)}")


@check("tec.version_servidor")
def _(D):
    h = D.sitio.get("cabeceras") or {}
    pw, srv = h.get("x-powered-by", ""), h.get("server", "")
    m = re.search(r"PHP/(\d+)\.(\d+)", pw)
    datos = [{"k": "Servidor", "v": " · ".join(x for x in [srv, pw] if x) or "no expuesto"}]
    if m:
        v = f"{m.group(1)}.{m.group(2)}"
        eol = PHP_EOL.get(v) or PHP_EOL.get(m.group(1))
        if eol and date.fromisoformat(eol) < HOY:
            return R("falla", 0, f"PHP {v} expuesto y sin parches de seguridad desde {eol}", severidad="alta", datos=datos)
        return R("parcial", 0.7, f"PHP {v} con soporte, pero la versión es pública", severidad="baja", datos=datos)
    if re.search(r"\d+\.\d+", srv):
        return R("parcial", 0.7, f"El servidor publica su versión ({srv})", severidad="baja", datos=datos)
    return R("ok", 1, "El servidor no expone versiones", datos=datos)


@check("tec.cms")
def _(D):
    t = D.home.get("dd", {}).get("tecnologia") or {}
    if not t.get("wordpress"):
        return NA("No es WordPress (o no se detectó la versión)")
    v, ult = t.get("versionWP"), (D.sitio.get("wordpress") or {}).get("ultimaVersionWP")
    if not v or not ult:
        return R("ok", 1, "WordPress no expone su versión")
    a, b = ver(v), ver(ult)
    atraso = (b[0] - a[0]) * 10 + (b[1] - a[1]) if len(a) > 1 and len(b) > 1 else 0
    datos = [{"k": "WordPress", "v": f"{v} (actual: {ult})"}]
    if atraso <= 0:
        return R("ok", 1, f"WordPress {v} al día", datos=datos)
    return R("parcial" if atraso == 1 else "falla", 0.6 if atraso == 1 else 0.1, f"WordPress {v}: {atraso} versión(es) atrás de {ult}", severidad="media" if atraso == 1 else "alta", datos=datos)


@check("tec.librerias")
def _(D):
    t = D.home.get("dd", {}).get("tecnologia") or {}
    prob = []
    if t.get("jquery") and ver(t["jquery"]) < (3, 5, 0):
        prob.append(f"jQuery {t['jquery']} (vulnerabilidades XSS conocidas; corregidas en 3.5)")
    bs = t.get("bootstrap")
    if bs and ((ver(bs) < (3, 4, 1)) or ((4, 0, 0) <= ver(bs) < (4, 3, 1))):
        prob.append(f"Bootstrap {bs} (XSS conocido)")
    if not t.get("jquery") and not bs:
        return NA("Sin librerías detectables")
    return R("falla", 0, "; ".join(prob)) if prob else R("ok", 1, "Librerías sin vulnerabilidades conocidas: " + ", ".join(x for x in [f"jQuery {t.get('jquery')}" if t.get("jquery") else "", f"Bootstrap {bs}" if bs else ""] if x))


@check("tec.wp_expuesto")
def _(D):
    w = D.sitio.get("wordpress")
    if not w:
        return NA("No es WordPress")
    prob = []
    if w["usuariosExpuestos"]:
        prob.append(f"la API pública lista {w['usuariosExpuestos']} usuario(s) administrador(es)")
    if w["xmlrpcActivo"]:
        prob.append("XML-RPC activo (blanco habitual de ataques de contraseña)")
    return R("falla" if len(prob) == 2 else ("parcial" if prob else "ok"), 1 - len(prob) / 2, "; ".join(prob).capitalize() if prob else "Sin exposición")


@check("tec.contenido_mixto")
def _(D):
    m = [(p, u) for p in D.utiles for u in p["d"].get("red", {}).get("mixto", [])]
    return R("ok", 1, "Sin contenido mixto") if not m else R("falla", 0, f"{len(m)} recurso(s) por http en páginas seguras", [f"{p['ruta']}: {u}" for p, u in m[:5]])


@check("tec.errores_js")
def _(D):
    malas = [p for p in D.utiles if p["d"].get("consola")]
    ev = [f"{p['ruta']}: {p['d']['consola'][0][:140]}" for p in malas[:6]]
    return ratio_estado(len(D.utiles) - len(malas), len(D.utiles), "Sin errores en consola" if not malas else f"Errores de JavaScript en {de_n(len(malas), len(D.utiles))}", evidencia=ev, paginas=rutas(malas))


@check("tec.recursos_rotos")
def _(D):
    e = {x["url"]: x["status"] for p in D.utiles for x in p["d"].get("red", {}).get("errores4xx5xx", [])}
    return R("ok", 1, "Todos los archivos cargan") if not e else R("falla" if len(e) > 3 else "parcial", max(0, 1 - len(e) / 10), f"{len(e)} archivo(s) que no cargan", [f"{s} · {u[-80:]}" for u, s in list(e.items())[:6]])


@check("tec.favicon")
def _(D):
    return R("ok", 1, "Favicon presente") if (D.home.get("dd", {}).get("favicon") or D.sitio.get("faviconIco") == 200) else R("falla", 0, "Sin favicon")


@check("tec.obsoleta")
def _(D):
    herr, ids = medicion_total(D)
    prob = []
    if any((p["dd"].get("tecnologia") or {}).get("flash") for p in D.utiles):
        prob.append("contenido Flash (ningún navegador lo reproduce desde 2021)")
    if (ids["ua"] or any("Universal" in h for h in herr)) and not ids["ga4"] and "GA4" not in herr:
        prob.append("Universal Analytics como única analítica (apagado en 2023)")
    return R("falla", 0, "; ".join(prob)) if prob else R("ok", 1, "Sin tecnología obsoleta detectada")


# ── Accesibilidad ──
def axe_reglas(D):
    agg = {}
    for p in D.utiles:
        ax = p["d"].get("axe")
        if not isinstance(ax, list):
            continue
        for v in ax:
            if v["impacto"] in ("critical", "serious"):
                a = agg.setdefault(v["id"], {"id": v["id"], "impacto": v["impacto"], "ayuda": v["ayuda"], "nodos": 0, "paginas": []})
                a["nodos"] += v["nodos"]
                a["paginas"].append(p["ruta"])
    return sorted(agg.values(), key=lambda x: (x["impacto"] != "critical", -x["nodos"]))


@check("a11y.axe")
def _(D):
    ps = [p for p in D.utiles if isinstance(p["d"].get("axe"), list)]
    if not ps:
        return NA("axe no pudo correr")
    por_pag = [len({v["id"] for v in p["d"]["axe"] if v["impacto"] in ("critical", "serious")}) for p in ps]
    prom = statistics.mean(por_pag)
    regs = axe_reglas(D)
    ev = [f"{r['ayuda']} ({r['id']}, {r['impacto']}) · {r['nodos']} elementos en {len(r['paginas'])} página(s)" for r in regs[:8]]
    return R("ok" if prom == 0 else ("parcial" if prom <= 3 else "falla"), max(0, 1 - prom / 7), f"{len(regs)} tipo(s) de barrera grave; {prom:.1f} por página en promedio", ev)


@check("a11y.psi")
def _(D):
    ms = psi(D)
    if not ms:
        return NA("Sin medición de PageSpeed")
    v = ms[0]["puntuaciones"].get("accessibility")
    return R("ok" if v >= 90 else ("parcial" if v >= 70 else "falla"), v / 100, f"Lighthouse accesibilidad: {v}/100", datos=[{"k": "Accesibilidad (Lighthouse)", "v": f"{v}/100"}])


@check("a11y.alt")
def _(D):
    tot = sum((p["dd"].get("imagenes") or {}).get("total", 0) for p in D.utiles)
    sin = sum((p["dd"].get("imagenes") or {}).get("sinAlt", 0) for p in D.utiles)
    if not tot:
        return NA("Sin imágenes")
    v = 1 - sin / tot
    return R("ok" if v >= 0.95 else ("parcial" if v >= 0.7 else "falla"), v, f"{sin} de {tot} imágenes sin texto alternativo")


@check("a11y.contraste")
def _(D):
    n = sum(v["nodos"] for p in D.utiles if isinstance(p["d"].get("axe"), list) for v in p["d"]["axe"] if v["id"] == "color-contrast")
    ps = [p["ruta"] for p in D.utiles if isinstance(p["d"].get("axe"), list) and any(v["id"] == "color-contrast" for v in p["d"]["axe"])]
    return R("ok", 1, "Contraste suficiente") if not n else R("falla" if n > 20 else "parcial", max(0, 1 - n / 60), f"{n} textos con contraste insuficiente en {len(ps)} página(s)", paginas=ps)


# ── Contenido ──
@check("cont.relleno")
def _(D):
    # Solo texto VISIBLE en la página. La descripción de plantilla ya la cuenta seo.descripciones.
    hits = [(p, x) for p in D.utiles for x in p["dd"].get("textoRelleno", []) if x not in ("todo", "Todo", "fixme")]
    for p in D.utiles:
        val = p["dd"].get("titulo") or ""
        if PLANTILLA.search(val):
            hits.append((p, f"título de pestaña: «{val[:60]}»"))
    if not hits:
        return R("ok", 1, "Sin texto de relleno visible")
    ev = sorted({f"{p['ruta']}: {x}" for p, x in hits})[:8]
    return R("falla", 0, f"Texto de plantilla o de relleno en {len({p['ruta'] for p, _ in hits})} página(s)", ev, paginas=sorted({p["ruta"] for p, _ in hits}))


@check("cont.anio")
def _(D):
    anios = [p["dd"].get("vigencia", {}).get("anioPie") for p in D.utiles]
    anios = [a for a in anios if a]
    if not anios:
        return NA("El pie no muestra año (o se genera al cargar)")
    a = max(anios)
    if a >= HOY.year:
        return R("ok", 1, f"© {a}")
    return R("parcial" if a == HOY.year - 1 else "falla", 0.5 if a == HOY.year - 1 else 0, f"El pie dice © {a}: el sitio parece sin mantenimiento desde entonces", datos=[{"k": "Año en el pie", "v": str(a)}])


@check("cont.caducado")
def _(D):
    hits = {}
    for p in D.utiles:
        for x in p["dd"].get("textoCaducado", []):
            hits.setdefault(x, []).append(p["ruta"])
    redes = [p["ruta"] for p in D.utiles if (p["dd"].get("contacto") or {}).get("redes", {}).get("googleplus")]
    if redes:
        hits.setdefault("enlace a Google+", []).extend(redes)
    if not hits:
        return R("ok", 1, "Sin menciones caducadas")
    return R("falla", 0, "Menciones caducadas: " + ", ".join(hits), [f"«{k}» en {', '.join(sorted(set(v))[:4])}" for k, v in hits.items()])


@check("cont.actualizacion")
def _(D):
    f = D.sitio["sitemap"].get("lastmodMasReciente")
    if not f:
        return NA("El sitemap no indica fechas de actualización")
    d = dias_desde(f)
    if d is None:
        return NA("Fecha ilegible")
    return R("ok" if d <= 180 else ("parcial" if d <= 365 else "falla"), 1 if d <= 180 else (0.5 if d <= 365 else 0), f"Última actualización registrada: {f} (hace {d} días)")


@check("cont.blog")
def _(D):
    b = D.sitio.get("blog")
    if not b:
        return NA("Sin blog o noticias detectables en el sitemap")
    d = dias_desde(b["ultima"])
    return R("ok" if d <= 180 else "falla", 1 if d <= 180 else max(0, 1 - (d - 180) / 540), f"{b['entradas']} entradas; la última del {b['ultima']} (hace {d} días)")


@check("cont.enlaces_externos")
def _(D):
    r = D.sitio.get("enlaces", {}).get("rotosExternos", [])
    n = D.sitio.get("enlaces", {}).get("externosRevisados", 0)
    return R("ok", 1, f"{n} enlaces externos funcionan") if not r else R("falla" if len(r) > 2 else "parcial", max(0, 1 - len(r) / 6), f"{len(r)} enlace(s) externo(s) que ya no existen", [f"{x['url']} → {x['status']}" for x in r[:6]])


# ─────────────────────────── puntuación ──────────────────────────────
def etiqueta(p):
    for e in REGLAS["etiquetas"]:
        if p >= e["min"]:
            return e
    return REGLAS["etiquetas"][-1]


def puntuar(checks: dict, rubricas: dict | None = None):
    """Devuelve {area: {auto, rubrica, final, etiqueta}} y la general. Misma función para analizar y construir."""
    areas = {}
    for aid, a in REGLAS["areas"].items():
        ch = [(cid, c) for cid, c in checks.items() if REGLAS["checks"][cid]["area"] == aid and c["estado"] != "na"]
        pesos = sum(REGLAS["checks"][cid]["peso"] for cid, _ in ch)
        auto = round(100 * sum(REGLAS["checks"][cid]["peso"] * c["valor"] for cid, c in ch) / pesos) if pesos else None
        rub = None
        crit = REGLAS["rubricas"].get(aid)
        if crit and rubricas and rubricas.get(aid):
            pts = [rubricas[aid].get(x["id"], {}).get("puntos") for x in crit]
            if all(isinstance(x, (int, float)) for x in pts):
                rub = round(100 * sum(pts) / (2 * len(pts)))
        m = a["mezcla"]
        if auto is not None and rub is not None and m["rubrica"] > 0:
            final = round(auto * m["auto"] + rub * m["rubrica"])
        else:
            final = auto if auto is not None else rub
        areas[aid] = {"auto": auto, "rubrica": rub, "final": final, "pendienteRubrica": bool(crit) and m["rubrica"] > 0 and rub is None,
                      "etiqueta": etiqueta(final)["nombre"] if final is not None else "Sin datos", "color": etiqueta(final)["color"] if final is not None else "na"}
    val = [(REGLAS["areas"][k]["peso"], v["final"]) for k, v in areas.items() if v["final"] is not None]
    gen = round(sum(p * f for p, f in val) / sum(p for p, _ in val)) if val else None
    return areas, {"final": gen, "etiqueta": etiqueta(gen)["nombre"], "color": etiqueta(gen)["color"]}


# ─────────────────────────── salidas ─────────────────────────────────
def fecha_larga(d=HOY):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def resumen_md(D, checks, areas, general):
    L = []
    s = D.sitio
    t = D.home.get("dd", {}).get("tecnologia") or {}
    herr, ids = medicion_total(D)
    L.append(f"# Resumen de datos · {D.cfg['cliente']}\n")
    L.append(f"Sitio: {s['home']} · {len(D.utiles)} páginas recorridas de {s.get('candidatas', 0) + 1} candidatas · {fecha_larga()}\n")
    L.append(f"**Puntuación automática general: {general['final']} ({general['etiqueta']})** — las áreas con rúbrica cambiarán al calificarla.\n")
    L.append("## Datos clave\n")
    stack = [k for k in ("wordpress", "elementor", "wpbakery", "divi", "avada", "revslider", "woocommerce", "wix", "squarespace", "shopify", "webflow", "joomla", "drupal", "godaddy", "vtex") if t.get(k)]
    L.append(f"- Tecnología: {', '.join(stack) or 'HTML/PHP propio'}" + (f" · WP {t.get('versionWP')}" if t.get("versionWP") else "") + f" · jQuery {t.get('jquery')} · Bootstrap {t.get('bootstrap')} · SEO plugin: {t.get('seoPlugin')} · tipografías {t.get('tipografias')}")
    L.append(f"- Servidor: {s['cabeceras'].get('server')} · {s['cabeceras'].get('x-powered-by', '')} · TLS {s.get('tls', {}).get('protocolo')} vence {s.get('tls', {}).get('validoHasta')}")
    L.append(f"- Medición: {', '.join(herr) or 'ninguna'} · IDs {json.dumps(ids)}")
    chats = sorted({c for p in D.utiles for c in p['d'].get('chat', [])})
    cons = sorted({c for p in D.utiles for c in p['d'].get('consentimiento', [])})
    L.append(f"- Chat: {', '.join(chats) or 'ninguno'} · Consentimiento de cookies: {', '.join(cons) or 'ninguno'}")
    c = D.home.get("dd", {}).get("contacto") or {}
    L.append(f"- Contacto (home): tel {c.get('tels')} · WhatsApp {c.get('whatsapp')} (flotante {c.get('whatsFlotante')}) · mailto {c.get('mailto')} · mapa {c.get('mapa')} · redes {list((c.get('redes') or {}).keys())}")
    L.append(f"- robots.txt: {'sí' if s['robots']['existe'] else 'NO'} · sitemap: {s['sitemap']['urls']} URLs, última modificación {s['sitemap'].get('lastmodMasReciente')} · llms.txt: {'sí' if s['llmsTxt']['existe'] else 'no'} · blog: {s.get('blog')}")
    if D.rend:
        for m in D.rend["mediciones"]:
            if m.get("puntuaciones"):
                lab = m["laboratorio"]
                L.append(f"- PSI {m['strategy']} {urlparse(m['url']).path or '/'}: {m['puntuaciones']} · LCP {lab['lcp'] and round(lab['lcp'] / 1000, 1)} s · TBT {lab['tbt'] and round(lab['tbt'])} ms · CLS {lab['cls'] and round(lab['cls'], 3)} · {lab['pesoKB']} KB")
        m0 = next((m for m in D.rend["mediciones"] if m.get("campoOrigen")), None)
        L.append(f"- Datos de campo (origen): {json.dumps(m0['campoOrigen']) if m0 else 'sin datos suficientes'}")
        op = next((m for m in D.rend["mediciones"] if m.get("oportunidades")), None)
        if op:
            L.append("- Principales oportunidades PSI (home móvil): " + "; ".join(f"{o['titulo']} ({o['valor'] or ''})" for o in op["oportunidades"][:6]))
        if D.rend.get("competidores"):
            L.append("\n### Competidores\n")
            for cc in D.rend["competidores"]:
                L.append(f"- {cc['nombre']} ({cc['url']}): móvil {cc['movil']} · señales {cc['senales']}")
            L.append(f"- {D.cfg['cliente']} (señales equivalentes): {D.rend.get('clienteSenales')}")
    L.append("\n## Páginas\n")
    for p in D.utiles:
        dd = p["dd"]
        L.append(f"- `{p['id']}` {p['url']} · «{(dd.get('titulo') or '')[:60]}» · H1 {dd.get('h1')} · {dd.get('palabras')} palabras · formularios {[(f['clase'], f['nCampos']) for f in dd.get('formularios', [])]} · CTAs pliegue {dd.get('ctas', {}).get('pliegue', [])[:4]}")
    for aid, a in sorted(REGLAS["areas"].items(), key=lambda x: x[1]["orden"]):
        ar = areas[aid]
        L.append(f"\n## {a['nombre']} — auto {ar['auto']} · rúbrica {ar['rubrica'] if ar['rubrica'] is not None else 'PENDIENTE' if ar['pendienteRubrica'] else '—'} · final {ar['final']} ({ar['etiqueta']})\n")
        for cid, rc in REGLAS["checks"].items():
            if rc["area"] != aid:
                continue
            ch = checks[cid]
            icon = {"ok": "✓", "parcial": "◐", "falla": "✗", "na": "–"}[ch["estado"]]
            L.append(f"- {icon} **{cid}** ({ch['severidad'] or rc['severidad']}) {ch['detalle']}")
            for e in ch["evidencia"][:5]:
                L.append(f"    - {e}")
    L.append("\n## Capturas disponibles (datos/capturas/)\n")
    L.append(", ".join(sorted(x.name for x in (D.raiz / "datos" / "capturas").glob("*.png") if "-full" not in x.name)))
    return "\n".join(L) + "\n"


def borrador(D, checks, areas):
    pref = {"ux": "UX", "leads": "LEAD", "seo": "SEO", "geo": "GEO", "rendimiento": "VEL", "tecnica": "TEC", "accesibilidad": "ACC", "contenido": "CONT"}
    cont, hs = {}, []
    orden_sev = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    fallas = [(cid, c) for cid, c in checks.items() if c["estado"] in ("falla", "parcial")]
    fallas.sort(key=lambda x: (REGLAS["areas"][REGLAS["checks"][x[0]]["area"]]["orden"], orden_sev[x[1]["severidad"] or REGLAS["checks"][x[0]]["severidad"]]))
    for cid, c in fallas:
        rc = REGLAS["checks"][cid]
        a = rc["area"]
        cont[a] = cont.get(a, 0) + 1
        sev = c["severidad"] or rc["severidad"]
        if c["estado"] == "parcial" and sev in ("critica", "alta") and not c["severidad"]:
            sev = SEV_ORDEN[SEV_ORDEN.index(sev) - 1]
        hs.append({
            "id": f"{pref[a]}-{cont[a]:02d}", "area": a, "regla": cid, "origen": "auto", "visible": sev in ("critica", "alta", "media"),
            "severidad": sev, "impacto": {"critica": 3, "alta": 3, "media": 2, "baja": 1}[sev], "esfuerzo": rc["esfuerzo"], "servicio": rc["servicio"],
            "titulo": "{{REDACTAR}}", "que_vimos": "{{REDACTAR}}", "por_que": "{{REDACTAR}}", "recomendacion": "{{REDACTAR}}",
            "datos": c["datos"][:4], "evidencia": [], "paginas": c["paginas"][:6],
            "_tecnico": {"check": rc["titulo"], "detalle": c["detalle"], "evidencia": c["evidencia"][:6]},
        })
    rub = {aid: {x["id"]: {"puntos": None, "nota": "{{REDACTAR}}"} for x in crit} for aid, crit in REGLAS["rubricas"].items() if not aid.startswith("_")}
    lim = [f"Se recorrieron {len(D.utiles)} páginas representativas de {D.sitio.get('candidatas', 0) + 1} encontradas, en computadora (1440 px) y teléfono (390 px); la home también en tableta (768 px).",
           "Revisión desde fuera y solo de lectura: no se enviaron formularios ni se accedió al administrador del sitio, a Google Analytics ni a Search Console."]
    if not D.rend:
        lim.append("No se midió la velocidad con PageSpeed Insights.")
    elif checks["rend.campo"]["estado"] == "na":
        lim.append("Google no tiene suficientes visitas reales registradas del sitio (Chrome UX Report); la velocidad se reporta con mediciones de laboratorio.")
    if D.rend and any(m.get("fuente") == "lighthouse-local" for m in D.rend["mediciones"]):
        lim.append("El sitio no permitió la medición desde los servidores de Google (PageSpeed Insights); la velocidad se midió con Lighthouse en local, con la misma simulación de red móvil.")
    if D.rend and (D.rend.get("homeMovil") or {}).get("inestable"):
        lim.append(f"La velocidad en teléfono varió {D.rend['homeMovil']['variacion']} puntos entre mediciones; se reporta como rango.")
    return {
        "_instrucciones": "Rellena todo {{REDACTAR}} siguiendo references/redaccion.md. Fusiona, descarta (visible:false) o añade hallazgos manuales (origen: manual, regla: null). Borra las claves _tecnico antes de construir si quieres; construir.py las ignora.",
        "cliente": {"nombre": D.cfg["cliente"], "dominio": urlparse(D.sitio["home"]).netloc, "sector": "{{REDACTAR}}", "relacion": D.cfg.get("relacion", "externo")},
        "fecha": fecha_larga(),
        "autor": {"nombre": "{{REDACTAR}}", "puesto": "{{REDACTAR}}", "email": "{{REDACTAR}}", "whatsapp": ""},
        "resumen": {"titular": "{{REDACTAR}}", "parrafo": "{{REDACTAR}}"},
        "fortalezas": [{"titulo": "{{REDACTAR}}", "texto": "{{REDACTAR}}"} for _ in range(3)],
        # Sección «Cómo se ve hoy»: el argumento visual de que el diseño cumplió su ciclo.
        # Cada señal lleva un recorte (evidencia.json → evidencia/<img>.png). Ver references/diseno.md
        "diseno": {"titular": "{{REDACTAR}}", "texto": "{{REDACTAR}}",
                   "senales": [{"titulo": "{{REDACTAR}}", "texto": "{{REDACTAR}}", "img": "{{REDACTAR}}", "pie": "{{REDACTAR}}"} for _ in range(4)],
                   "comparacion": [{"hoy": "{{REDACTAR}}", "se_espera": "{{REDACTAR}}"} for _ in range(4)]},
        "prioridades": [],
        "areas": {aid: {"veredicto": "{{REDACTAR}}"} for aid in REGLAS["areas"]},
        "rubricas": rub,
        "hallazgos": hs,
        # Un solo paquete en tres frentes (servicios.json → frentes). Sin fechas ni plazos.
        "paquete": {k: {"servicios": [], "hallazgos": [], "resultado": "{{REDACTAR}}"} for k in SERVICIOS["frentes"]},
        "cierre": {"titular": "{{REDACTAR}}", "texto": "{{REDACTAR}}", "cta": "Agendar una llamada", "enlace": "{{REDACTAR}}"},
        "limitaciones": lim,
    }


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 analizar.py ../clientes/<slug>")
    raiz = Path(sys.argv[1]).resolve()
    D = Datos(raiz)
    if not D.utiles:
        sys.exit("No hay páginas recorridas con éxito. Revisa datos/paginas/*.json")
    checks = {}
    for cid in REGLAS["checks"]:
        try:
            checks[cid] = CHECKS[cid](D)
        except Exception as e:  # un check roto no tumba el análisis, pero se declara
            checks[cid] = R("na", None, f"ERROR del check: {type(e).__name__}: {e}")
    faltan = set(REGLAS["checks"]) - set(CHECKS)
    if faltan:
        print("! Checks sin implementar:", ", ".join(sorted(faltan)))
    inf = raiz / "informe.json"
    rub = json.loads(inf.read_text()).get("rubricas") if inf.exists() else None
    areas, general = puntuar(checks, rub)
    out = raiz / "analisis"
    out.mkdir(exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1))
    (out / "puntuaciones.json").write_text(json.dumps({"areas": areas, "general": general, "reglas_version": REGLAS["version"]}, ensure_ascii=False, indent=1))
    (out / "resumen.md").write_text(resumen_md(D, checks, areas, general))
    if not inf.exists():
        (raiz / "informe.borrador.json").write_text(json.dumps(borrador(D, checks, areas), ensure_ascii=False, indent=1))
    errores = [k for k, v in checks.items() if v["detalle"].startswith("ERROR")]
    print(f"✓ {len(checks)} checks · general {general['final']} ({general['etiqueta']})")
    for aid, a in sorted(areas.items(), key=lambda x: REGLAS["areas"][x[0]]["orden"]):
        print(f"  {REGLAS['areas'][aid]['nombre']:32} auto {str(a['auto']):>4} · rúbrica {str(a['rubrica']) if a['rubrica'] is not None else ('pend.' if a['pendienteRubrica'] else '—'):>5} · {a['etiqueta']}")
    n = sum(1 for c in checks.values() if c["estado"] in ("falla", "parcial"))
    print(f"  {n} checks con falla o parcial → {'informe.borrador.json' if not inf.exists() else 'informe.json ya existe (no se sobrescribe)'}")
    if errores:
        print("! Checks con error:", ", ".join(errores))


if __name__ == "__main__":
    main()
