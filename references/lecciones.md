# Lecciones

Lo que salió mal o costó una vuelta de más. **Qué pasó, dónde y qué hacer ahora.**
Léelo antes de la fase 1 y de la 2; añade lo nuevo al terminar cada diagnóstico.

Los casos se describen sin identificar al cliente. Conserva nombres, dominios y
detalles privados en `clientes/<slug>/`, no en las lecciones compartidas.

## Recolección

| Qué pasó | Contexto | Qué hacer |
|---|---|---|
| El dominio redirigía a `cgi-sys/suspendedpage.cgi` (hosting suspendido) | Hosting suspendido | Si la home final es una página de suspensión, mantenimiento o «próximamente», **para y avisa**: es un aviso urgente al cliente, no una auditoría |
| PageSpeed Insights devolvía «Something went wrong» siempre, con la clave funcionando en otros sitios | Sitio protegido por Cloudflare | `rendimiento.js` pasa solo a Lighthouse local tras 2 intentos. Se declara en limitaciones |
| `index.php` entraba como página distinta de la home | Sitio PHP | `recolectar.js` normaliza `/index.(php|html)` → `/` |
| Entraban la versión en inglés y la página de login | Sitio multilingüe | Se omiten idiomas secundarios (`config.incluirIdiomas: true` para forzarlos) y `ingresar/login/registro` |
| Lighthouse local imprime un stack de `SourceMap` / `trace_engine` | Medición local | Es un aviso interno, no un fallo: comprueba que la medición se haya generado |
| El detector de relleno marcaba «todo» (español) como el `TODO` de programador | Contenido en español | `TODO/FIXME` solo cuentan en mayúsculas |
| Google seguía mostrando URLs del sitio anterior que entraban en un bucle de redirecciones | Migración de sitio | **Busca siempre la marca con la búsqueda web disponible y abre 2–3 resultados viejos**: si el sitio se rehízo, las URLs antiguas suelen romperse. El recolector reporta `BUCLE_DE_REDIRECCIONES` en enlaces |
| Lighthouse local dio LCP de 5 s en una corrida y de 17 s en otra | Medición inestable | Reporta rangos o «más del doble de lo recomendado», según lo medido; nunca un número suelto de una sola corrida local |
| La selección automática llenó 6 de 10 páginas con categorías de marca iguales | Tienda en línea | `recolectar.js` toma máx. 2 páginas por plantilla (primer segmento de la ruta); en tiendas, pide a mano en `config.paginas`: tienda, un producto, una categoría, nosotros, contacto |
| «Teléfonos sin enlace» eran números de WhatsApp que sí tenían enlace | Contacto por WhatsApp | Los números enlazados a wa.me ya cuentan como enlazados |
| Los WhatsApp de contacto usaban wa.me/55… sin el 52: WhatsApp no los reconoce como mexicanos | Numeración de México | Check `leads.whatsapp_pais` (crítico). Verificar con GET a wa.me/<número>: con 52 la página muestra «+52 …» |
| Un teléfono mostraba un número y su enlace `tel:` marcaba otro | Contacto de una sucursal | Revisar a mano en contacto: texto visible contra `href="tel:…"` |
| La ventana emergente tapaba la home y su botón de cerrar no mostraba la «×» | Popup de entrada | `ux.capa_bloquea` la detecta; mira el botón de cerrar con zoom en la captura. Para los recortes de diseño, `ocultar` el popup y el chat con los selectores reales del sitio |
| Escribí «bloquea a ChatGPT, Claude, Perplexity y Gemini» cuando robots.txt solo bloqueaba PerplexityBot y los rastreadores de entrenamiento; los chips del propio hallazgo lo contradecían | Permisos de bots de IA | Antes de redactar GEO-01, lee bot por bot: buscadores vs. entrenamiento (ver revision-manual §5) |
| El equipo detectó detalles de diseño en páginas fuera de la muestra (cursos, categorías profundas) | Sitio con varias plantillas | Recorre al menos dos páginas de cada plantilla secundaria, aunque no entren en las 10 de la muestra |
| Las capturas limpias salían en negro debajo de la portada | `capturas_limpias.js` forzaba `overflow:auto` en `html` y `body`; en un sitio con WPBakery eso volvió el `body` una caja con scroll | Ya solo destraba el eje que esté bloqueado (`overflow-y: hidden`). Compara siempre el peso y el alto de la captura limpia con la original |
| Los recortes por selector habrían fallado sin aviso | El sitio define una función global `scrollY`; `r.top + scrollY` daba `NaN` | Los scripts usan `window.pageYOffset`. En sondeos propios, usa `pageYOffset` o `document.scrollingElement.scrollTop` |
| Una franja de cierre con teléfono y correo no salía en ninguna captura | Solo aparece con una animación de entrada al llegar al fondo; el recorrido volvía arriba antes de que arrancara | El recorrido ahora espera 600 ms al fondo. Antes de escribir «la página no invita a cotizar», desplázate con la rueda hasta el final y mira qué aparece |
| Un encabezado de plantilla («Este es un elemento de encabezado personalizado») estaba en el HTML pero no se veía | Su animación nunca se dispara (opacidad 0) | Repórtalo como texto que leen Google y los lectores de pantalla, no como algo visible. Comprueba la opacidad heredada antes de decir que algo «se ve» |
| Anoté mal a qué número llevaba el botón flotante de WhatsApp | Lo había apuntado en la fase 2 y lo iba a redactar de memoria | Justo antes de redactar un hallazgo de datos de contacto, vuelve a listar cada `tel:`, `sms:`, `wa.me`, mapa y correo con la zona donde está (menú, barra, pie, cuerpo) |

## Construcción y QA del entregable

| Qué pasó | Qué hacer |
|---|---|
| Captura completa del QA repetía la portada a partir de 16 384 px | Límite de Chrome; `verificar.js` ya captura por tramos (`qa-<vp>-N.png`) |
| Bloques con animación que no aparecían en el QA | `scroll-behavior: smooth` frenaba el desplazamiento del script; el QA ya se desplaza de forma instantánea. La página revela por posición, no por intersección, para que salten bien los enlaces al anexo |
| Evidencias muy anchas (cabeceras) ilegibles en la columna | `construir.py` las pasa a ancho completo si la proporción supera 3.2:1 |
| La matriz dejaba vacíos los cuadrantes de abajo | Fila alta = impacto 3. Ajusta el impacto de cada hallazgo; el borrador solo lo deriva de la severidad |
| El índice lateral no salía en la captura de página completa | Es `sticky`: en una captura completa no se ve. `verificar.js` lo comprueba con una captura de pantalla normal (`qa-<vp>-indice.png`) |
| El HTML único abría la galería con imágenes rotas | `empaquetar.py` incrusta también `data-full` (páginas completas de la galería) |
| Un recorte apaisado de móvil (cabecera) cayó en marco de teléfono y la «isla» lo tapaba | El marco de teléfono solo para capturas verticales; recortes pequeños van sin marco |
| Axe marcaba contraste en la barra superior durante su transición de color | El QA espera 600 ms tras volver arriba antes de correr axe |
| Chip «Formulario sin cuenta» en verde junto al hallazgo «para cotizar hay que tener cuenta» | Si un check pasa por un motivo y el recorrido real falla por otro, el hallazgo manual manda; los chips se redactan neutros («Formulario de contacto») |
| «Semanas 1–4», «en semanas» y las duraciones por servicio comprometen fechas antes de la propuesta | Sección 05 es «Todo, en un solo paquete» con tres frentes temáticos; `servicios.json` sin duraciones y `construir.py` avisa si un texto trae un plazo |
| Un mismo servicio aparecía en dos frentes (SEO) y se veía repetido | Cada servicio en un solo frente; `construir.py` avisa |
| El botón «Hablemos» del índice se veía como un campo de texto | La regla genérica `.toc a` pisaba los estilos del botón; los enlaces del índice van con `.toc ol a` (CSS y app.js) |
| El logo cambiaba de tamaño entre barra oscura y clara | `logo-newemage-color.svg` del Brand Kit se deforma (la «e» sale ovalada): se usa `logo-newemage-dark.svg` sobre claro, a 34 px de alto |
| Galería de páginas cortada a la derecha y tarjetas encimadas | En escritorio es cuadrícula; la barra de URL necesita `min-width: 0` para no ensanchar la tarjeta |
| La portada del diagnóstico y el sitio en vivo mostraban la ventana emergente encima de la home | `config.ocultar` + `capturas_limpias.js`: las piezas principales usan la versión sin ventana; la ventana se muestra solo en su hallazgo |
| La barra del marco decía `/contacto/` sobre una captura de otra página | El marco toma la primera de `paginas` del hallazgo | Si la evidencia viene de otra página, pon `url` en esa evidencia |
| El veredicto visual decía «Desactualizado» en un sitio que no es viejo, sino demasiado simple | Las etiquetas de estado eran fijas | `diseno.veredicto.etiquetas` renombra el estado (p. ej. «Insuficiente»); ajusta también titular, subtítulo y la cifra del hallazgo principal |
| Un arreglo acordado como «inmediato» no entraba en la lista porque su impacto era medio | La lista se calculaba solo con impacto 3 y esfuerzo 1 | Usa `inmediatos` en `informe.json` en lugar de inflar el impacto del hallazgo |
| El recorte de ortografía se cortaba en la tarjeta antes de las faltas citadas en el pie | El recorte era alto y la tarjeta limita la altura | Recorta ancho y bajo, justo lo que nombra el pie; lo que el pie cita debe verse sin abrir el visor |
| Para mostrar la paleta no había captura posible | El hallazgo era de color, repartido en seis páginas | Mide los colores calculados (texto y fondo, por página) y arma una lámina con Pillow en `evidencia/`; dilo en el pie y en limitaciones: es una ilustración, no una captura |
| `analizar.py` y `construir.py` fallaron con «Not a directory» | Les pasé `config.json`; reciben la carpeta del cliente (los de Node que recolectan reciben el `config.json`) | `analizar.py`, `construir.py`, `verificar.js` y `empaquetar.py` → `../clientes/<slug>`; `recolectar.js`, `rendimiento.js` y `capturas_limpias.js` → `…/config.json` |

## Falsos positivos que casi entran (heredados de auditoria-ux-comercial)

| Qué parecía | Qué era | Regla |
|---|---|---|
| Texto de relleno en la página | Estaba dentro de `<!-- comentarios -->` | `recolectar.js` lee `innerText` renderizado; si dudas, mira la captura |
| `<h1>` presente | Estaba vacío o fuera de pantalla | `seo.h1` ya cuenta los vacíos como ausentes; confirma en la captura |
| Contador en 0 | Arranca en 0 y sube al desplazarse | El recolector se desplaza antes de leer; revisa si un número se ve raro |
| Imágenes rotas | Estado de carga | Solo cuenta `complete && naturalWidth === 0` tras desplazarse; confirma en la captura |
| «Cero schema en todo el sitio» | Solo se revisaron 2 páginas | Afirma «en las N páginas revisadas», nunca «en todo el sitio» |

## Hallazgos que salen seguido en sitios viejos

- Meta descripción con el texto de la plantilla (Porto, Avada, «Just another WordPress site»).
- Página o aviso de COVID-19 todavía en el menú.
- Cotizar exige cuenta.
- PHP 7.x expuesto en `X-Powered-By`.
- `www.` sin DNS o sin redirección.
- Sin robots.txt ni sitemap (sitios PHP hechos a mano).
- Sin `lang` en `<html>`: afecta lectores de pantalla y buscadores.
