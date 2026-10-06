# Sección «Cómo se ve hoy» (diseño)

Es el argumento visual del diagnóstico: el cliente **ve** su sitio y entiende, sin que
nadie se lo explique, que el diseño cumplió su ciclo. Va justo después de «En dos
minutos», antes de las calificaciones, porque es lo que más convence y lo que abre la
conversación de rediseño.

**Si el diseño es la prioridad (lo habitual en sitios desactualizados), se nota en todo el
documento**: titular del resumen, prioridad n.º 1 (un hallazgo manual crítico de diseño con
dos capturas), veredicto visual y el frente «Diseño y experiencia» primero en el paquete. Los
arreglos rápidos (WhatsApp, ventanas, enlaces) no ocupan prioridades: salen solos bajo ellas
como «arreglos inmediatos».

La construye `construir.py` con cinco bloques:

| Bloque | De dónde sale | Qué hace |
|---|---|---|
| Veredicto visual | `informe.diseno.veredicto` (8–10 aspectos) | Bloque oscuro: estado general, barra por estados y cada aspecto con su etiqueta (Desactualizado / Mejorable / Actual). También aparece como acceso en la portada |
| Sitio en vivo | `datos/capturas/desktop-01-*-full.png` y `mobile-01-*-full.png` | Navegador y teléfono que se **recorren por dentro**: la home completa tal cual |
| Señales (3–6) | `informe.diseno.senales` + recortes en `evidencia/` | Cada señal: recorte, título y dos líneas. Toque para ampliar |
| Hoy / lo que se espera | `informe.diseno.comparacion` (4–5 pares) | Dos columnas: lo que hay contra el estándar actual |
| Galería | todas las páginas recorridas | Miniatura de cada página; al tocarla se abre **completa** y desplazable |

La portada también monta la home en navegador y teléfono: la primera imagen que ve el
cliente es su propio sitio.

## Qué buscar: señales de un diseño que ya cumplió su ciclo

Revisa las capturas completas de escritorio y teléfono y marca las que **se vean**:

| Señal | Cómo se reconoce |
|---|---|
| Tipografía de época | Condensadas en mayúsculas (Oswald, Bebas), fuentes de sistema, muchos pesos mezclados |
| Texto justificado y gris claro | Ríos blancos entre palabras, bajo contraste |
| Íconos de librería | Font Awesome genérico, íconos en rombos o círculos, estilos mezclados |
| Sliders y carruseles en la portada | Varias diapositivas que compiten; flechas y puntos |
| Contadores animados | «+500000» que suben al desplazarse, sin contexto |
| Fotos genéricas o tratadas | Stock, filtros grises, pixeladas, estiradas |
| Información dentro de imágenes | Volantes, banners con texto, tablas como imagen |
| Bloques de plantilla | Formas diagonales, «shape dividers», espacios vacíos, alineaciones rotas |
| Sombras duras, degradados de época, bordes biselados | Botones con relieve, cajas con sombra negra |
| Cabeceras y estilos distintos entre páginas | Cada página parece otro sitio |
| Pie de página denso | Texto diminuto, menú completo repetido, contraste bajo |
| Avisos caducados | COVID, promociones vencidas, «nuevo» de hace años |
| Móvil como versión encogida | Elementos encimados, menús cortados, textos minúsculos, cabecera de varios pisos |
| Falta de aire | Secciones pegadas, tarjetas con botones a distinta altura, sin márgenes constantes |
| Íconos y componentes desparejos | Íconos de distinto tamaño en una fila, botones de estilos distintos |
| Botones planos sobre texturas | Rectángulo blanco sin radio sobre fondo con burbujas, copos o degradados de época |
| Plantillas que parecen otro sitio | Cursos, eventos o landings sin el menú ni la tipografía del sitio |

Elige **las 4–8 más evidentes**, de secciones distintas del sitio (portada, teléfono, ficha,
tienda, nosotros…). Una señal sin recorte no entra.

## Veredicto visual

Califica 8–10 aspectos con una observación concreta cada uno: portada, botones y componentes,
fotografía, fichas o páginas de servicio, tipografía, teléfono, consistencia, color, pie. El
estado general es el que domina. Sé honesto: si algo está bien, va como «actual».

## Recortes

Decláralos en `evidencia.json` con prefijo `d-` (p. ej. `d-tipografia`):

- `selector` de la sección completa (`section#Productos`) con `margen: 0` y `altoMax` de 600–700;
- si hay contadores o animaciones, `esperarTras: 4000`–`5000`;
- sin `resaltar`: aquí se muestra la composición completa, no un detalle.

## Redacción

- **`diseno.titular`**: una tesis con `*énfasis*`. «Un diseño de plantilla que *ya cumplió su ciclo*».
- **`diseno.texto`** (≤ 380): de dónde viene el diseño, qué transmite hoy frente a lo que la
  empresa es, y que lo que sigue son capturas reales. Sin culpas: el diseño fue correcto en
  su momento.
- **Cada señal**: título descriptivo («Productos en gris y sin nombre»), dos líneas con lo que
  se ve y por qué hoy juega en contra, y un pie que diga página y sección.
- **Comparación**: frases cortas y paralelas. «Hoy» describe, «se espera» propone sin
  prometer cifras.

Prohibido: «feo», «anticuado» a secas, comparar con un competidor por nombre, o afirmar
algo que la captura no muestra.
