# informe.json — referencia de campos

`analizar.py` genera `informe.borrador.json` la primera vez. Cópialo a `informe.json`
y rellénalo; `analizar.py` nunca sobrescribe `informe.json`. Si recolectas de nuevo,
los IDs y hallazgos automáticos pueden cambiar: compara con el borrador nuevo a mano.

```jsonc
{
  "cliente":  { "nombre": "Empresa de ejemplo", "dominio": "example.com", "sector": "Fabricante industrial",
                "relacion": "externo" },             // "mantenemos" si Newemage hizo o mantiene el sitio (cambia el tono)
  "fecha":    "28 de septiembre de 2026",
  "autor":    { "nombre": "…", "puesto": "…", "email": "…", "whatsapp": "52…" },   // firma del cierre

  "resumen":  { "titular": "… *palabra con degradado* …", "parrafo": "…" },
  "fortalezas": [ { "titulo": "…", "texto": "…" } ×3 ],
  "diseno": {                                            // sección «Cómo se ve hoy» (obligatoria) · ver diseno.md
    "titular": "Un diseño de plantilla que *ya cumplió su ciclo*",
    "subtitulo": "…",                                    // opcional; por defecto depende de cliente.relacion
    "texto": "…",
    "veredicto": {                                       // opcional, muy recomendado: bloque oscuro al inicio de 02 + acceso en la portada
      "estado": "Desactualizado", "texto": "De nueve aspectos, *cinco* se ven desactualizados…",
      "criterios": [ { "aspecto": "Portada", "estado": "desactualizado", "nota": "…" } ]   // desactualizado | mejorable | actual
    },
    "senales": [ { "titulo": "…", "texto": "…", "img": "d-tipografia.png", "pie": "Home · bloque …" } ],  // 3–8
    "comparacion": [ { "hoy": "…", "se_espera": "…" } ]                                                    // 4–5, opcional
  },
  "prioridades": [ "LEAD-01", "SEO-02", "TEC-01" ],     // 3 IDs visibles

  "areas": { "ux": { "veredicto": "…" }, … las 8 … },

  "rubricas": {                                          // UX, leads, geo, contenido
    "ux": { "propuesta": { "puntos": 1, "nota": "Home: el hero dice «20 años de innovación» pero no qué fabrican" }, … }
  },

  "hallazgos": [
    {
      "id": "LEAD-01",           // prefijo de área + número; único
      "area": "leads",           // ux · leads · seo · geo · rendimiento · tecnica · accesibilidad · contenido
      "regla": "leads.formulario", // check de reglas.json, o null si es manual
      "origen": "auto",          // auto | manual
      "visible": true,           // false → solo en el anexo
      "severidad": "critica",    // critica · alta · media · baja  (auto: la trae el borrador; no la bajes sin motivo escrito en decisiones)
      "impacto": 3, "esfuerzo": 1,  // 1–3. Impacto 3 = fila alta de la matriz; impacto 3 + esfuerzo 1 = «Arreglo rápido». El borrador lo deriva de la severidad: ajústalo
      "servicio": "landing",     // clave de servicios.json
      "titulo": "…", "que_vimos": "…", "por_que": "…", "recomendacion": "…",
      "datos": [ { "k": "Páginas", "v": "10 de 10" } ],          // chips; máx. 4
      "evidencia": [ { "img": "cotizar-login.png", "pie": "…", "marco": "browser" } ], // en evidencia/ o capturas/…; máx. 2.
                                                   // marco opcional: browser · phone · plain (si no, se deduce de la forma)
      "paginas": [ "/cotizar/" ],
      "_tecnico": { … }          // lo deja analizar.py; construir lo ignora salvo en ocultos sin redactar
    }
  ],

  "paquete": {                 // un solo paquete en tres frentes; sin fechas ni plazos. El orden de las claves
                               // es el orden en pantalla: si el diseño es la prioridad, «experiencia» va primero
    "base":        { "servicios": [ "landing", "mantenimiento" ], "hallazgos": [ "LEAD-01", … ], "resultado": "…" },
    "visibilidad": { "servicios": [ "seo", "geo" ], "hallazgos": [ … ], "resultado": "…" },
    "experiencia": { "servicios": [ "ux" ], "hallazgos": [ … ], "resultado": "…" }
  },

  "cierre": { "titular": "…", "texto": "…", "cta": "Agendar una llamada", "enlace": "mailto:…?subject=…" },
  "limitaciones": [ "…" ]
}
```

## Lo que valida `construir.py`

Error (no construye): `{{REDACTAR}}` en cualquier campo usado (los ocultos pueden
quedarse sin redactar), severidad/área/servicio desconocidos, impacto o esfuerzo fuera
de 1–3, imagen de evidencia inexistente, prioridades ≠ 3 visibles, rúbrica incompleta,
hallazgo visible fuera del paquete, menos de 3 fortalezas, falta `diseno` o tiene
menos de 3 señales o alguna sin imagen.

Aviso (construye, pero corrígelo): textos más largos que el límite, > 6 visibles en un
área, > 30 visibles en total, un hallazgo de un frente cuyo servicio no está en ese frente,
un servicio repetido en dos frentes, textos con plazos («semanas», «Mes 2», «de inmediato»),
resumen de más de 480 caracteres, hallazgos de UX, leads o contenido sin captura.

## Cómo se arma el paquete

El diagnóstico **no propone fechas, plazos ni duraciones**: presenta todo como un solo
paquete de servicios que Newemage resuelve en conjunto. Los tiempos se definen después,
en la propuesta comercial o con la skill plan-de-trabajo. Los frentes son temas, no etapas:

- **base** (Base y contacto): lo que frena contactos y lo que deja el sitio desprotegido —
  formularios, cotización, medición, actualización, seguridad, www, texto de plantilla.
- **visibilidad** (Visibilidad y velocidad): SEO, GEO, velocidad, contenido y accesibilidad.
- **experiencia** (Diseño y experiencia): lo que requiere rediseñar — UX, cotizador, sitio nuevo.

Cada servicio va **en un solo frente** (el de sus hallazgos principales) y cada hallazgo
visible, en el frente de su servicio. Si el sitio es tan viejo que optimizarlo no tiene
sentido (sin viewport, Flash, PHP sin soporte y maqueta rota), dilo: «visibilidad» puede
quedar corto y «experiencia» llevar `sitio`. Es una recomendación honesta, no una venta más grande.
