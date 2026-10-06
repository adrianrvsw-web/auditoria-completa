# Metodología y ajustes

## Qué mide cada script

| Script | Fuente | Qué obtiene |
|---|---|---|
| `recolectar.js` | Chrome (playwright-core) | Hasta `maxPaginas` páginas elegidas por prioridad (home, contacto, servicios/productos, nosotros, blog). Por página y pantalla: SEO on-page, formularios, canales de contacto, CTAs sobre el pliegue, imágenes, texto pequeño, desbordes, elementos fijos, capa que tapa, objetivos táctiles, tecnología, IDs de medición, año del pie, texto de relleno o caducado, enlaces, red (peso, terceros, píxeles, chat, consentimiento, contenido mixto), consola y axe-core. Nivel sitio: redirecciones de las 4 variantes del dominio, cabeceras, TLS, robots.txt (y bots de IA), sitemaps, llms.txt, 404, WordPress expuesto y enlaces rotos. También el HTML sin JavaScript |
| `rendimiento.js` | PageSpeed Insights API → respaldo Lighthouse local | Home móvil ×2 (rango), home escritorio, 2 páginas clave en móvil; puntuaciones de las 4 categorías, métricas de laboratorio, datos de campo (CrUX) si existen, oportunidades y terceros. Competidores: velocidad móvil y señales básicas |
| `analizar.py` | reglas.json | 70 checks deterministas → estado (ok/parcial/falla/na), valor 0–1, severidad, evidencia |

## Cómo se calcula la puntuación

1. Cada check vale `peso × valor` (valor 0–1; los parciales dan crédito proporcional).
   Los `na` no cuentan.
2. Puntuación automática del área = suma ponderada / suma de pesos × 100.
3. Rúbrica del área = puntos / (2 × criterios) × 100.
4. Final del área = mezcla definida en `reglas.json` (p. ej. UX 35 % auto + 65 % rúbrica).
5. General = promedio de las áreas ponderado por su `peso` (leads 20, UX/SEO/velocidad 15,
   GEO/técnica 10, accesibilidad/contenido 7.5).
6. Etiquetas: ≥ 85 Bien · ≥ 70 Aceptable · ≥ 50 Por mejorar · < 50 Crítico.

La misma función (`puntuar` en `analizar.py`) la usan el análisis y la construcción: la
cifra del resumen interno y la del entregable no pueden diferir.

## Honestidad de la medida de velocidad

- Una pasada de Lighthouse varía varios puntos. La home móvil se mide dos veces y se
  reporta el **rango**; si varía más de 8 puntos, `limitaciones` lo declara.
- Si PageSpeed Insights no puede analizar el sitio (típico con Cloudflare o bloqueos de
  bots), se mide con Lighthouse local, con la misma simulación de red móvil, y se declara.
  Los números locales dependen de la conexión del equipo: no compares un informe hecho
  con PSI con otro hecho en local.
- Los datos de campo (usuarios reales, CrUX) solo existen si el sitio tiene tráfico
  suficiente. Sin ellos, el check `rend.campo` queda `na` y no penaliza.

## Ajustar reglas y servicios

- **`scripts/reglas.json`**: pesos, severidades base, esfuerzo, servicio que resuelve cada
  check, textos de los criterios de rúbrica y la mezcla auto/rúbrica por área. Si cambias
  pesos, **sube `version`**: queda registrada en `analisis/puntuaciones.json`.
- **`scripts/servicios.json`**: nombre y descripción de los servicios que aparecen en el
  paquete, y los tres frentes. Sin duraciones: el diagnóstico no compromete plazos. Los marcados `supuesto: true` se
  infirieron de las herramientas del equipo: **confírmalos con el equipo comercial**.
   Los de origen «planeador» se incluyen aquí como catálogo inicial; no hace falta
   instalar el Planeador ni acceder a sus archivos.
- Un check nuevo necesita: entrada en `reglas.json` + función `@check` en `analizar.py`
  (+ el dato en `recolectar.js` si no existe) + etiqueta corta en `CHIPS` de
  `construir.py` si debe salir como chip.

## Relación con las demás herramientas

Son integraciones opcionales del equipo Newemage, no dependencias de esta skill.
Si no están disponibles, el diagnóstico y el paquete se pueden entregar igualmente.

| Herramienta | Relación |
|---|---|
| auditoria-ux-comercial | Es la versión de venta **profunda de UX** (5 oportunidades con prototipos) para prospectos. Este diagnóstico es **amplio** (8 áreas) para clientes actuales. Se puede ofrecer como siguiente paso del frente «Diseño y experiencia» |
| Optimización (newemage-launch) | Implementa buena parte de los frentes «Base» y «Visibilidad» en WordPress: velocidad LiteSpeed, SEO por página, favicon, formularios. Comparte la API key de PageSpeed y el criterio de ruido |
| rank-math-audit | Implementa el servicio `seo` en WordPress con Rank Math |
| webp-optimizer | Resuelve `rend.imagenes` |
| plan-de-trabajo | Convierte el paquete aprobado en un plan con fechas (las fechas van ahí, nunca en el diagnóstico) para el Planeador |
| user-journey-map / wireframe-kit | Entregables del frente «Diseño y experiencia» |
