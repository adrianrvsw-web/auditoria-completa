---
name: auditoria-completa
description: Hace el diagnóstico digital completo de Newemage sobre el sitio de un cliente — UX/UI, conversión de leads, SEO, visibilidad en IA (GEO), velocidad, técnica y seguridad, accesibilidad y vigencia del contenido — con mediciones reales (Chrome, PageSpeed/Lighthouse, axe), calificación por área, hallazgos con evidencia, matriz impacto × esfuerzo y un solo paquete de servicios de Newemage que lo resuelve todo, sin fechas ni plazos, entregado como una página HTML interactiva. Úsala cuando el usuario dé la URL de un cliente y pida una auditoría completa, un diagnóstico del sitio, una revisión integral, "auditoría 360", "revisa todo el sitio de X", un reporte para ofrecer servicios, o evaluar un sitio desactualizado. Palabras clave - auditoría completa, diagnóstico digital, auditoría web, auditoría seo, geo, conversión, leads, velocidad, pagespeed, accesibilidad, revisión técnica, sitio desactualizado, propuesta de servicios.
---

# Diagnóstico digital completo · Newemage

Produce **una página HTML interactiva** que un cliente con el que ya hay relación
abre, entiende en dos minutos y termina en una conversación de proyecto. Cubre ocho
áreas con mediciones reales y termina proponiendo **un solo paquete de servicios** de
Newemage que resuelve todo lo encontrado, organizado en tres frentes. **Sin fechas, plazos
ni duraciones**: los tiempos se definen después, en la propuesta.

**Las capturas son las protagonistas.** La portada monta la home del cliente en
navegador y teléfono; la sección «Cómo se ve hoy» deja recorrer el sitio por dentro y
muestra las señales de que el diseño cumplió su ciclo; cada hallazgo abre con su
evidencia grande y enmarcada. Un índice lateral fijo (panel «Índice» en teléfono)
permite saltar a cualquier sección o área.

Resuelve la raíz de la skill a partir de la ubicación de este `SKILL.md`, nunca
a partir de una ruta personal ni del directorio actual del usuario. Los clientes
van en `clientes/<slug>/` dentro de esa raíz; los scripts se lanzan desde `scripts/`.
La carpeta `clientes/` es local y está excluida de Git. La instalación y los
requisitos están en `README.md`.

---

## Las reglas que no se negocian

1. **Cero invención.** Ningún porcentaje de mejora, benchmark ni promesa («+30 % de
   ventas»). Solo lo medido o lo que se ve en una captura. Lo no medible se declara en
   *limitaciones*.
2. **Solo lectura.** Nunca enviar formularios, crear cuentas, comprar ni iniciar sesión.
   Solo GET/HEAD. Nada de credenciales, cookies ni nombres de usuario en el entregable.
3. **La severidad y la puntuación salen de `scripts/reglas.json`**, no de la opinión del
   momento. Claude redacta, agrupa, descarta falsos positivos y califica las rúbricas
   con una observación concreta por criterio.
4. **El cliente no es el enemigo.** Es un cliente con el que ya trabajamos: se abre con
   lo que funciona, se habla de oportunidades y de evolución, nunca de errores ni culpas.
5. **Legible o no sirve.** 18–28 hallazgos visibles en total, ≤ 6 por área, textos
   cortos (los límites los vigila `construir.py`). Lo demás va al anexo.
6. **Verificar antes de afirmar.** Todo hallazgo automático se confirma en la captura o
   en el navegador antes de hacerlo visible. Ver `references/lecciones.md`.

---

## Flujo

### Fase 0 · Encuadre

Del usuario necesitas **la URL**. Pregunta solo si no está claro:
- quién firma el diagnóstico (nombre, puesto, correo, WhatsApp) — va en el cierre;
- **si Newemage hizo o mantiene el sitio** → `"relacion": "mantenemos"` en `config.json`. Cambia
  el tono: revisión periódica y siguiente etapa, nunca culpas (ver `redaccion.md`);
- 2–3 competidores (opcional; si no los da, no se inventan).

Primera vez en el equipo: instala las dependencias con `npm ci` desde `scripts/`.
Requiere Node.js 22 o posterior, Python 3.12 o posterior y Google Chrome instalado.
PageSpeed admite la variable de entorno opcional `PSI_API_KEY`; en macOS también
admite el llavero del equipo Newemage. Sin clave se intenta la API pública y, si
falla, Lighthouse local. No leas ni muestres la clave en la conversación. No des
por hecho que existen credenciales ni otras skills del equipo.

```bash
# Desde la raíz de la skill instalada:
mkdir -p clientes/<slug>
cp config.example.json clientes/<slug>/config.json
# config.json: cliente, slug, base, maxPaginas (10 por defecto), relacion (externo|mantenemos),
#   paginas [rutas que deben entrar sí o sí], competidores [{nombre,url}]
# Sustituye los datos ficticios por los del cliente antes de recolectar.
```

Lee `references/lecciones.md` antes de seguir.

### Fase 1 · Recolección automática (≈ 8–12 min, puede ir en segundo plano)

```bash
cd scripts
node recolectar.js ../clientes/<slug>/config.json   # recorrido, capturas, axe, robots, sitemap, enlaces
node rendimiento.js ../clientes/<slug>/config.json  # PageSpeed (o Lighthouse local si Google está bloqueado)
python3 analizar.py ../clientes/<slug>              # 70 checks → puntuaciones → resumen + borrador
```

Si el sitio abre una **ventana emergente, chat o banner de cookies** que tapa el contenido,
declara sus selectores en `config.json` → `"ocultar": ["#popup", "#chat"]` y corre
`node capturas_limpias.js ../clientes/<slug>/config.json`. La portada, «Cómo se ve hoy» y la
galería usan esas capturas limpias; las originales quedan como evidencia del hallazgo.

Si el sitio redirige a una página de hosting suspendido, de mantenimiento o de
«próximamente», **para y avísale al usuario**: eso es el hallazgo, no hay auditoría.

### Fase 2 · Revisión experta

Lee `analisis/resumen.md` completo y `references/revision-manual.md`. Luego:

- **Mira las capturas** (`datos/capturas/`): home en escritorio, tableta y teléfono,
  contacto/cotización y al menos una página de producto o servicio.
- **Recorre el camino del contacto como cliente**: ¿cuántos pasos para pedir
  información? ¿exige cuenta? ¿qué dice el botón? Sin enviar nada.
- **Muestra GEO**: usa la búsqueda web disponible para buscar la marca y «<categoría>
  en <ciudad>». Anota si aparece y si la información es correcta. Es una muestra,
  se declara como tal. Si no tienes búsqueda web, decláralo en limitaciones;
  no infieras presencia en IA a partir de las señales técnicas.
- **Descarta falsos positivos** del borrador (casos típicos en `lecciones.md`).
- **Califica las rúbricas** (UX, Leads, GEO, Contenido): 0/1/2 con una nota que diga
  página y qué se vio.
- **Añade hallazgos manuales** (`origen: "manual"`, `regla: null`) para lo que ningún
  script ve: encimados, estética anticuada, textos confusos, fricción en cotizar.

### Fase 3 · Selección y aprobación — **para aquí**

Presenta al usuario, en una tabla por área: calificación, hallazgos que serán visibles
(ID, título, severidad, servicio), las señales de diseño elegidas, las 3 prioridades y la propuesta de paquete
(qué servicios en cada frente). **Espera su aprobación antes de redactar y construir.**
El equipo conoce al cliente: puede pedir suavizar, quitar o añadir.

### Fase 4 · Evidencia y diseño

Lee `references/diseno.md`. Dos tipos de recorte:

- **Señales de diseño** (4–6, prefijo `d-`): secciones completas que muestran que el
  diseño está desactualizado. Son obligatorias: sin ellas no se construye.
- **Evidencia de hallazgos**: una o dos imágenes por hallazgo visible. Todo hallazgo de
  UX, leads o contenido debería llevar captura (`construir.py` avisa si falta); lo
  técnico puede ir con chips de datos. El marco (navegador, teléfono o sin marco) se
  elige solo por la forma de la imagen; se fuerza con `"marco"` en la evidencia.

Declara los recortes en `clientes/<slug>/evidencia.json` y:

```bash
node evidencia.js ../clientes/<slug>/evidencia.json   # PNG nítidos con el problema resaltado
```

Revisa cada PNG a ojo. También se pueden citar capturas de `datos/capturas/` directamente.

### Fase 5 · Redacción

Copia `informe.borrador.json` a `informe.json` y rellena todo `{{REDACTAR}}` siguiendo
`references/redaccion.md`. Estructura completa en `references/informe.md`.

### Fase 6 · Construcción y QA

```bash
python3 analizar.py ../clientes/<slug>      # recalcula con las rúbricas ya calificadas
python3 construir.py ../clientes/<slug>     # valida y genera presentacion/index.html
node verificar.js ../clientes/<slug>        # 1440/768/390, axe, anclas, visor, filtros
```

**No entregues mientras `verificar.js` reporte algo.** Además de desbordes, anclas,
imágenes y axe, comprueba el índice lateral (fijo y con sección activa) y el panel
«Índice» en tableta y teléfono. Mira a ojo `qa/qa-*-indice.png` y los tramos
`qa/qa-<vp>-N.png` antes de dar por terminado.

### Fase 7 · Entrega

```bash
python3 empaquetar.py ../clientes/<slug> [--pdf]
```

Deja en `clientes/<slug>/entrega/` la carpeta para hosting, el zip, un **HTML único**
(todo incrustado, se manda por correo) y opcionalmente el PDF. **No subas nada a ningún
servidor sin confirmación explícita.** Si están instaladas, ofrece al usuario:
- armar el plan de trabajo con la skill **plan-de-trabajo** a partir del paquete (ahí sí van fechas, fuera del diagnóstico);
- profundizar el rediseño con **auditoria-ux-comercial** (prototipos navegables).

### Fase 8 · Lecciones

Añade a `references/lecciones.md` los falsos positivos, correcciones del equipo y
hallazgos que convenga buscar siempre usando ejemplos genéricos, sin nombres,
dominios ni información identificable de clientes. Guarda el detalle privado de
cada caso dentro de `clientes/<slug>/`. Si algo se repite en dos clientes, corrígelo en
el script o en `reglas.json`, no solo en la lección.

---

## Estructura

```
auditoria-completa/
├─ SKILL.md · README.md · LICENSE · .gitignore · config.example.json
├─ references/        redaccion · revision-manual · metodologia · informe · lecciones
├─ assets/plantilla/  estilos.css + app.js (identidad Newemage, se incrustan al construir)
├─ assets/logos/      logos Newemage (copia del Brand Kit, no editar el original)
├─ scripts/           recolectar.js · rendimiento.js · analizar.py · evidencia.js
│                     capturas_limpias.js · construir.py · verificar.js · empaquetar.py
│                     reglas.json (checks, pesos, rúbricas) · servicios.json (catálogo)
└─ clientes/<slug>/
   ├─ config.json  evidencia.json  informe.json
   ├─ datos/       lo recolectado (capturas, capturas-limpias, crudo, sitio.json, paginas/, rendimiento.json)
   ├─ analisis/    checks.json · puntuaciones.json · resumen.md
   ├─ evidencia/   recortes PNG originales (no viajan)
   ├─ presentacion/  ← el entregable (index.html + assets/)
   ├─ qa/          capturas e informe del QA
   └─ entrega/     carpeta, zip, HTML único, PDF
```

## Referencias

| Archivo | Cuándo leerlo |
|---|---|
| `references/lecciones.md` | **Antes de la fase 1 y de la 2**: falsos positivos y trampas conocidas |
| `references/revision-manual.md` | Fase 2: qué mirar a mano, cómo calificar las rúbricas, muestra GEO |
| `references/diseno.md` | Fase 4: señales de diseño desactualizado, recortes y cómo redactar «Cómo se ve hoy» |
| `references/redaccion.md` | Fase 5: tono, estructura de cada hallazgo, lo prohibido, ejemplos |
| `references/informe.md` | Fase 5: todos los campos de `informe.json` |
| `references/metodologia.md` | Para explicar la calificación o ajustar `reglas.json` y `servicios.json` |
