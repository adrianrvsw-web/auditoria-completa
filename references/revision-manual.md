# Revisión experta (fase 2)

Los scripts miden; la revisión experta **ve**. La mitad de lo que vende este diagnóstico
—que el sitio se ve viejo, que cotizar cuesta, que no transmite el tamaño de la empresa—
no lo detecta ningún check. Pero todo lo que se diga aquí necesita una captura o una
página concreta detrás.

## 1 · Orden de lectura

1. `analisis/resumen.md` completo: datos clave, páginas elegidas y los 70 checks.
2. Capturas del pliegue: `desktop-01-*.png`, `mobile-01-*.png`, `tablet-01-*.png`.
3. Capturas completas (`-full.png`) de home, contacto/cotización y una página de producto
   o servicio. Léelas por partes si son largas.
4. `datos/paginas/<id>.json` solo cuando un check necesite contexto (formularios,
   CTAs, capa que tapa, axe).

## 2 · Verificar los hallazgos automáticos

Antes de dejar un hallazgo automático como visible, confírmalo:

| Check | Cómo confirmarlo |
|---|---|
| `leads.formulario` en falla | Abre la página de contacto: ¿hay un formulario dentro de un iframe, un widget de HubSpot o un Calendly que no se detectó? |
| `leads.cta_home` | Mira el pliegue en ambas capturas: ¿hay un botón claro que el script no clasificó como «fuerte»? |
| `ux.capa_bloquea` | ¿La capa es un aviso de cookies legítimo y pequeño o de verdad tapa? |
| `ux.objetivos_tactiles` | Es ruidoso: solo hazlo visible si en la captura móvil se ven enlaces apiñados |
| `seo.h1` | Un H1 vacío o escondido cuenta como ausente; confírmalo en la captura |
| `tec.errores_js` | ¿El error rompe algo visible (menú, slider, formulario)? Si no, severidad baja y oculto |
| `a11y.*` | Visible como mucho 1–2 hallazgos; el detalle va en «revisiones» del área |
| `rend.*` | Si hay rango (medición inestable), di el rango, nunca un número suelto |

## 3 · Rúbricas: cómo calificar

Escala por criterio: **0** no se cumple · **1** a medias · **2** se cumple. La nota dice
**página y qué se vio** (se publica en el anexo, así que redáctala para el cliente).

### UX · anclas de calificación

| Criterio | 0 | 1 | 2 |
|---|---|---|---|
| propuesta | El hero es un slider genérico o solo el logo | Se intuye el giro, no el para quién | Se entiende qué hacen y para quién sin desplazarse |
| jerarquia | Todo pesa igual o compite | Hay orden pero con ruido | Títulos, textos y botones se distinguen de un vistazo |
| actualidad | Estética de >6 años: sombras duras, iconos clip-art, sliders, tipografías de sistema | Correcta pero fechada | Se percibe actual |
| consistencia | Cada página parece de otro sitio | Variaciones menores | Mismo sistema en todas |
| navegacion | >9 opciones o nombres internos («Área de clientes», «Covid-19») | Mejorable | Claro y breve |
| movil | Elementos encimados o que se salen | Usable con molestias | Pensado para el teléfono |
| imagenes | Stock genérico o pixelado | Mixto | Propias y de calidad |
| confianza | Nada visible | Hay pero escondido | Clientes, certificaciones o casos a la vista |

### Leads

| Criterio | Pregunta que te haces |
|---|---|
| camino | Desde una página de producto, ¿en cuántos toques llego a pedir precio? |
| friccion | ¿Me pide cuenta, captcha agresivo, 12 campos, o me manda a un PDF? |
| botones | ¿Dice «Solicitar cotización» o «Enviar»? |
| despues | ¿Dice cuándo me responden o qué sigue? |
| prueba | ¿Hay logos de clientes, testimonios o casos cerca del formulario? |

### GEO

| Criterio | Cómo |
|---|---|
| respuestas | ¿Hay textos que respondan preguntas reales (qué es, para qué sirve, cuánto dura, dónde entregan)? |
| autoridad | ¿Se ve quién está detrás: años, certificaciones con número, equipo, datos verificables? |
| marca | **Muestra**: busca con WebSearch «<marca>», «<marca> <producto>» y «<categoría> en <ciudad o país>». 2 = aparece arriba con información correcta; 1 = aparece con datos viejos o solo en directorios; 0 = no aparece. Declara la muestra en `limitaciones` |

### Contenido

Vigente (fechas, avisos, páginas de COVID), claridad (jerga vs beneficio), profundidad
(¿puedo decidir con lo que hay?), ortografía (lee al menos 3 páginas), recursos (fichas,
catálogos, FAQ).

## 3b · Diseño

Mientras miras las capturas, marca las señales de diseño desactualizado de
`references/diseno.md`. Alimentan la rúbrica de UX (`actualidad`, `consistencia`,
`imagenes`) y la sección «Cómo se ve hoy».

## 4 · Hallazgos manuales

Añádelos al final de `hallazgos` con `origen: "manual"`, `regla: null`, un `id` que siga la
numeración del área (`UX-05`), severidad según este criterio (no hay regla automática):

- **crítica**: impide contactar o comprar, o daña la confianza de forma evidente;
- **alta**: afecta a la mayoría de visitantes en el camino principal;
- **media**: afecta a una parte del recorrido o a la percepción;
- **baja**: detalle.

Casi siempre tienen evidencia visual: decláralos en `evidencia.json`.

## 5 · Qué buscar siempre (en minutos)

- Cotizar o descargar una ficha **exige cuenta**.
- Páginas o avisos caducados en el menú (COVID-19, promociones, eventos pasados).
- Encimados en la cabecera móvil (logo contra botón, menú cortado).
- Formularios sin aviso de privacidad (LFPDPPP) o que no dicen qué pasa al enviar.
- Teléfonos como texto sin enlace, WhatsApp escondido o solo en el pie.
- Descripciones de Google con texto de plantilla («Porto», «Just another WordPress site»).
- `www.` que no responde, o http que no redirige.
- Versión en otro idioma con contenido más viejo o distinto.
- **URLs viejas que Google sigue mostrando** (de un sitio anterior): ábrelas. Si terminan en error o en bucle de redirecciones, es un hallazgo SEO alto y un arreglo rápido.
- **Estructura de direcciones**: niveles de más (`/categoria-producto/otros-productos/…`), slugs numéricos (`/cursos/87672/`), copias (`/home-2/`). Recomendar estructura corta **siempre con 301**.
- **Vitrinas de la home** en tiendas: ¿una sola fila de productos? Proponer carruseles por categoría, marca, novedades y más vendidos.
- **Plantillas secundarias** (cursos, eventos, landings): ¿tienen el menú del sitio? ¿acordeones o cajas vacías? ¿eventos pasados que siguen invitando a reservar? Revisa al menos dos páginas de cada plantilla.
- **robots.txt y bots de IA**: distingue buscadores (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, PerplexityBot) de rastreadores de entrenamiento (GPTBot, ClaudeBot, Google-Extended). No escribas «bloquea a ChatGPT» si solo bloquea GPTBot: mira los chips del hallazgo.
