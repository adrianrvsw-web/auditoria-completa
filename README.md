# Diagnóstico digital completo · Newemage

Skill para producir una **auditoría web de ocho áreas** con mediciones reales,
capturas, calificaciones, hallazgos con evidencia y un solo paquete de servicios:

- UX/UI y conversión de leads.
- SEO y visibilidad en buscadores con IA (GEO).
- Velocidad, técnica y seguridad.
- Accesibilidad y vigencia del contenido.

El resultado es una **página HTML interactiva** con la identidad de Newemage, un
HTML único para compartir, una carpeta para hosting, un ZIP y, opcionalmente, un
PDF. El diagnóstico no propone fechas ni plazos.

## Requisitos

| Requisito | Uso |
|---|---|
| Claude Code u otro agente compatible con `SKILL.md` | Revisión visual, selección de hallazgos y redacción |
| Node.js **22 o posterior** y npm | Recolección, capturas, PageSpeed/Lighthouse y QA |
| Python **3.12 o posterior** | Análisis, construcción y empaquetado; sin paquetes Python adicionales |
| Google Chrome instalado | Playwright usa el canal `chrome`; no se descarga un navegador con npm |
| Conexión a internet | Sitio del cliente, PageSpeed y búsquedas de la revisión manual |

El agente necesita poder ejecutar comandos, leer imágenes y escribir archivos.
La búsqueda web se utiliza para la muestra GEO; si no está disponible, esa parte
se declara como limitación. Las demás skills de Newemage son opcionales.

## Instalar en Claude Code

En macOS o Linux, clona el repositorio en el directorio de skills personales:

```bash
git clone https://github.com/adrianrvsw-web/auditoria-completa.git "$HOME/.claude/skills/auditoria-completa"
npm ci --prefix "$HOME/.claude/skills/auditoria-completa/scripts"
```

Abre una nueva sesión de Claude Code para que detecte la skill. También puedes
instalarla para un proyecto en `.claude/skills/auditoria-completa/` o colocar el
repositorio en el directorio de skills que utilice tu agente. Conserva juntos
`SKILL.md`, `references/`, `scripts/` y `assets/`.

En Windows puedes clonar en la misma ubicación relativa a tu carpeta de usuario
y ejecutar `npm ci` desde `scripts/`. Los ejemplos de terminal de este README
usan sintaxis de macOS/Linux; adapta rutas y variables a PowerShell. Para Python
puedes usar `py -3` en lugar de `python3`, comprobando que sea 3.12 o posterior.

## Cómo se pide

En Claude Code escribe:

> Haz el diagnóstico completo de https://sitio-del-cliente.com

El agente pregunta quién firma, si Newemage mantiene el sitio y, opcionalmente,
por 2–3 competidores. Después:

1. Recolecta y mide el sitio. El flujo es de **solo lectura**: no envía formularios,
   compra, crea cuentas ni inicia sesión.
2. Revisa capturas, el camino para contactar y una muestra de presencia en buscadores.
3. **Te enseña la selección** de calificaciones, hallazgos, prioridades y paquete,
   y espera tu aprobación.
4. Redacta, construye y verifica el entregable en escritorio, tableta y teléfono.
5. Deja lo listo para compartir en `clientes/<slug>/entrega/`.

## Configuración de una auditoría

Desde la raíz del repositorio:

```bash
mkdir -p clientes/empresa-ejemplo
cp config.example.json clientes/empresa-ejemplo/config.json
```

Edita la copia con los datos del cliente **antes de ejecutar la recolección**.
`example.com` es una dirección ficticia de configuración, no una auditoría de muestra.

| Campo | Descripción |
|---|---|
| `cliente` | Nombre comercial del cliente |
| `slug` | Identificador de la carpeta, por ejemplo `empresa-ejemplo` |
| `base` | URL pública que se va a auditar |
| `maxPaginas` | Tamaño máximo de la muestra; 10 por defecto |
| `relacion` | `externo` o `mantenemos`; adapta el tono si Newemage hizo o mantiene el sitio |
| `locale` | Idioma de navegación, por defecto `es-MX` |
| `paginas` | Rutas que deben entrar en la muestra, por ejemplo `["/contacto/", "/servicios/"]` |
| `competidores` | Lista opcional: `[{"nombre": "Competidor de ejemplo", "url": "https://example.org/"}]` |
| `ocultar` | Selectores CSS de capas a retirar **solo de las capturas limpias** |
| `excluir` | Fragmentos de rutas a excluir de la selección |
| `incluirIdiomas` | `true` para incluir versiones en otros idiomas; `false` por defecto |

La carpeta que contiene `config.json` determina dónde se guardan los resultados.
Las carpetas de clientes se crean localmente y están excluidas de Git.

## PageSpeed y Chrome

La clave de PageSpeed es **opcional**. Para usar la tuya, define la variable en la
terminal desde la que abres el agente o ejecutas los scripts:

```bash
export PSI_API_KEY="TU_CLAVE_DE_PAGESPEED"
```

En macOS, si la variable no existe, el script también intenta leer el llavero del
equipo Newemage (`newemage-launch` / `psi-newemage`). No necesitas ese llavero para
usar la herramienta. Sin clave se intenta PageSpeed con su cuota pública; si la
API falla, se mide con Lighthouse local. La fuente y la falta de datos de campo
se deben declarar en el diagnóstico. No se incluye ninguna clave en este repositorio.

Los scripts no cargan archivos `.env` automáticamente. Si usas uno con tu propio
cargador, mantenlo local: `.gitignore` lo excluye.

Para el PDF, `empaquetar.py` busca Chrome en el `PATH` y en las ubicaciones
habituales de macOS y Windows. Puedes indicar una ubicación distinta:

```bash
export CHROME_PATH="/ruta/al/ejecutable/de/chrome"
```

Esta variable controla el empaquetador PDF. Para recolección y QA, instala Google
Chrome en la ubicación estándar que reconoce Playwright. Si falla el PDF, el
comando devuelve un error y conserva el HTML y el ZIP ya generados.

## Ejecutar los scripts

Estos comandos se ejecutan **desde la raíz del repositorio**. La revisión y la
redacción del agente siguen siendo necesarias; los scripts no reemplazan esa parte.

```bash
node scripts/recolectar.js clientes/empresa-ejemplo/config.json
node scripts/rendimiento.js clientes/empresa-ejemplo/config.json
python3 scripts/analizar.py clientes/empresa-ejemplo
```

Después de revisar los datos y aprobar la selección, prepara `evidencia.json` e
`informe.json` siguiendo [SKILL.md](SKILL.md) y [references/informe.md](references/informe.md).

```bash
node scripts/evidencia.js clientes/empresa-ejemplo/evidencia.json
python3 scripts/analizar.py clientes/empresa-ejemplo
python3 scripts/construir.py clientes/empresa-ejemplo
node scripts/verificar.js clientes/empresa-ejemplo
python3 scripts/empaquetar.py clientes/empresa-ejemplo
```

Para generar también el PDF, añade `--pdf` al último comando. No entregues el
diagnóstico mientras el QA reporte problemas. Ningún script publica en hosting.

## Dónde queda cada cosa

| Ruta | Contenido |
|---|---|
| `SKILL.md` | Instrucciones completas para el agente |
| `config.example.json` | Configuración ficticia de partida |
| `references/` | Metodología, redacción, diseño, revisión manual y lecciones anonimizadas |
| `assets/plantilla/` | CSS y JavaScript del informe interactivo |
| `assets/logos/` | Identidad visual de Newemage |
| `scripts/reglas.json` | Checks, pesos, severidades y rúbricas |
| `scripts/servicios.json` | Servicios y frentes del paquete comercial |
| `clientes/<slug>/datos/`, `analisis/`, `evidencia/`, `qa/` | Material interno de la auditoría, solo local |
| `clientes/<slug>/presentacion/` | Informe HTML con sus recursos |
| `clientes/<slug>/entrega/` | Carpeta de hosting, ZIP, HTML único y PDF opcional |

## Personalización

- **Confirma `scripts/servicios.json`** antes de compartir un diagnóstico. Los
  servicios con `supuesto: true` son una propuesta de catálogo: ajusta nombre y
  alcance a lo que ofrece tu equipo. Conserva las claves usadas por `reglas.json`.
- Ajusta pesos y criterios en `scripts/reglas.json`; si cambias la metodología,
  incrementa su versión.
- Para otra agencia, adapta los textos de marca en `SKILL.md`, las referencias y
  `scripts/construir.py`; reemplaza los logos y revisa `scripts/evidencia.js` y
  `assets/plantilla/`. La identidad Newemage viene como configuración inicial.
- Mantén las lecciones públicas en términos genéricos. Los detalles de clientes
  deben permanecer dentro de sus carpetas locales.

## Licencia

Código y documentación bajo [licencia MIT](LICENSE). Los SVG de Newemage en
`assets/logos/` están excluidos de esa licencia; consulta
[la nota de identidad](assets/logos/README.md). La publicación no concede derechos
sobre la marca ni sus logotipos.
