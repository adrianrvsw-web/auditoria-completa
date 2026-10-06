# Redacción del diagnóstico

Quien lo lee es **el dueño o el gerente de un cliente con el que ya trabajamos**. No es
técnico, tiene poco tiempo y su sitio lleva años sin cambios. Tiene que terminar de leer
pensando «esto tiene solución y ellos saben cómo», no «me están diciendo que todo está mal».

## Tono

- **De tú a tú, con respeto**: se usa *usted* implícito (impersonal o «su sitio») salvo
  que el equipo diga que con ese cliente se tutea.
- **Oportunidad, no error.** «El sitio no muestra…», «hoy la página…», «conviene…».
  Nunca «mal», «pésimo», «error grave», «descuido», «abandonado».
- **Evolución, no culpa.** Un sitio de 2019 cumplió su función; lo que cambió es el
  estándar (teléfono, IA, velocidad). Dilo así cuando aplique.
- **Consecuencia de negocio, no técnica.** Al cliente no le importa el `<h1>`: le
  importa que Google no entienda de qué trata la página y no la muestre.

## Estructura de cada hallazgo visible

| Campo | Qué es | Máx. | Cómo |
|---|---|---|---|
| `titulo` | El síntoma, en lenguaje de cliente | 90 | Empieza por lo que pasa, no por la solución. «Para cotizar hay que tener cuenta» |
| `que_vimos` | El hecho observable, con dónde | 340 | Página, pantalla y dato. Nada que no esté en la captura o en la medición |
| `por_que` | La consecuencia para el negocio | 280 | Qué pierde: contactos, confianza, visibilidad, tiempo del equipo |
| `recomendacion` | La acción concreta | 280 | Verbo en infinitivo o imperativo suave. Qué hacer, no cómo se programa |

- `**negrita**` para el dato clave (una vez por campo como mucho).
- Cifras siempre con su fuente implícita en el propio texto: «PageSpeed le da 58 de 100
  en teléfono», «10 de 10 páginas», «PHP 7.2, sin parches desde 2020».
- **Sin plazos ni compromisos de tiempo**: nada de «en semanas», «Semanas 1–4», «de
  inmediato», «un ajuste de horas», duraciones de servicio ni fechas de entrega. El
  diagnóstico ofrece resolver todo en un paquete; los tiempos se hablan en la propuesta.
  `construir.py` avisa si detecta un plazo.
- **Prohibido**: porcentajes de mejora prometidos, «Google penaliza» sin matiz, «hackear»,
  «vulnerable» sin decir a qué; siglas sin explicar (LCP, CLS, schema) — usa el glosario
  o una palabra llana.

### Traducciones útiles

| En vez de | Escribe |
|---|---|
| Meta description | La descripción que aparece bajo el título en Google |
| H1 ausente | La página no tiene un título principal que Google reconozca |
| Schema / datos estructurados | Información de la empresa en un formato que Google y las IA leen sin adivinar |
| LCP 5.3 s | El contenido principal tarda 5 segundos en aparecer en un teléfono |
| Soft 404 | Las direcciones que no existen no avisan que no existen |
| robots.txt / sitemap | Los archivos que le dicen a Google qué páginas hay |
| X-Powered-By PHP/7.2 | El servidor usa una versión de PHP que dejó de recibir parches de seguridad en 2020 |
| Contraste insuficiente | Textos claros sobre fondos claros que cuesta leer |
| Universal Analytics | La analítica anterior de Google, que dejó de funcionar en 2023 |

### Antes y después

> ✗ **Meta descriptions duplicadas con texto de plantilla.** Las 10 páginas tienen la meta
> description «Porto - Responsive HTML5 Template», lo que afecta negativamente el SEO.

> ✓ **En Google, el sitio se presenta como «una plantilla HTML».**
> *Qué vimos*: las 10 páginas revisadas llevan como descripción **«Porto - Responsive HTML5
> Template»**, el texto de ejemplo de la plantilla con la que se construyó el sitio.
> *Por qué importa*: es lo que Google puede mostrar bajo el nombre de la empresa cuando
> alguien la busca; quien compara proveedores ve un texto que no dice qué ofrece.
> *Qué recomendamos*: escribir una descripción propia para cada página, con lo que ofrece
> y para quién.

## Las piezas fijas

- **`resumen.titular`** (hero, ≤ 70 caracteres): la tesis del diagnóstico. Una idea, sin
  números. `*énfasis*` pinta una palabra con el degradado. Ej.: «Una empresa líder con un
  sitio que *ya no la representa*».
- **`resumen.parrafo`** (≤ 480): qué se revisó, cuál es el estado general en una frase y
  qué se gana atendiéndolo. Se lee en 20 segundos.
- **`fortalezas`** (3): **generales y verdaderas**, nunca específicas de un defecto. Salen de
  lo que sí cumple (checks en ✓, rúbricas en 2). Ej.: «Contacto a la vista», «Sitio seguro»,
  «Trayectoria bien contada».
- **`areas.<id>.veredicto`** (1 frase, ≤ 160): el estado del área en lenguaje llano. Sale
  en el tablero y en la cabecera del área.
- **`prioridades`** (3 IDs): mayor impacto en contactos y confianza; idealmente de áreas
  distintas y al menos un arreglo rápido.
- **`paquete.<frente>.resultado`** (1 frase): qué tendrá el cliente cuando ese frente
  esté resuelto, sin cifras inventadas ni plazos. «Sabrá cuántos contactos llegan del sitio y de dónde».
- **`cierre`**: titular corto con `*énfasis*`, dos frases que propongan el siguiente paso
  concreto (una llamada para revisar el diagnóstico y armar el paquete a su medida) y el enlace (`mailto:` o `https://wa.me/`).
- **`limitaciones`**: el borrador trae las automáticas. Añade las de la revisión manual
  («la muestra en buscadores con IA fue de 4 consultas el 28 de septiembre»).

## Cuando el sitio es nuestro (`cliente.relacion: "mantenemos"`)

Si Newemage hizo o mantiene el sitio, el diagnóstico no puede leerse como una confesión ni
como un ataque al trabajo previo. Reglas:

- **Marco de revisión periódica**: el sitio «creció con la empresa» y «pide su siguiente
  etapa»; nunca «se quedó atrás», «cumplió su ciclo» ni «descuidado». `construir.py` ya cambia
  el subtítulo de las señales de diseño.
- **Sin atribuir autoría**: no decir quién subió, cambió o dejó algo. Describir el estado
  («los enlaces no incluyen la clave de país»), no la causa («alguien olvidó…»). Si un dato
  objetivo ubica el origen en el contenido (p. ej. la fecha en la ruta de una imagen), puede
  mencionarse como hecho, sin juicio.
- **Mantenimiento rutinario, fuera de lo visible**: actualizaciones menores de CMS, cabeceras de
  seguridad y detalles de servidor que corresponden a nuestro mantenimiento van con
  `visible: false` (quedan en el anexo). Lo que afecta al cliente de verdad (contacto roto,
  velocidad) se muestra siempre: ocultarlo sería peor.
- **Cierre**: «ya conocemos el sitio por dentro, podemos empezar sobre lo que ya funciona».

## Hallazgos ocultos (`visible: false`)

No hace falta redactarlos: el anexo usa el título del check y su detalle técnico. Si se
redactan, el anexo usa lo redactado. Úsalo para lo real pero menor (favicon, HSTS, llms.txt).

**Un falso positivo no se oculta: se borra de `hallazgos`.** Oculto seguiría apareciendo en el
anexo como «otro detalle» con un dato incorrecto. Si el check en sí está mal, corrígelo en
`analizar.py` o `recolectar.js`.
