/* ════════════════════════════════════════════════════════════════════
   evidencia.js — recortes nítidos del sitio vivo para las tarjetas
   Uso:  node evidencia.js ../clientes/<slug>/evidencia.json

   evidencia.json es una lista. Cada entrada:
     nombre       archivo de salida (sin extensión) → clientes/<slug>/evidencia/<nombre>.png
     url          página
     vp           "desktop" | "mobile" | "tablet"            (por defecto desktop)
     selector     recorta ese elemento (el primero visible)   — o —
     clip         {x, y, w, h} en px CSS desde arriba de la página — o —
     nada         captura la pantalla tal cual llega el usuario (el pliegue)
     resaltar     ["selector", …] se marcan con un contorno rosa Newemage
     etiqueta     texto corto que aparece junto al primer resaltado (opcional)
     margen       px alrededor del elemento recortado (por defecto 24)
     altoMax      alto máximo del recorte en px CSS (por defecto 900)
     ocultar      ["selector", …] se ocultan antes de capturar (p. ej. banner de cookies
                  que NO es parte del hallazgo; decláralo en decisiones)
     transparente true → fondo transparente (para el logo del cliente)
     esperar      ms extra tras cargar (por defecto 1500)
     esperarTras  ms tras el recorrido de lazy-load, antes de recortar (por defecto 800;
                  sube a 4000 si hay contadores o animaciones de entrada)

   Solo lectura: no hace clic, no escribe, no envía nada.
   ════════════════════════════════════════════════════════════════════ */
const { chromium } = require('playwright-core');
const path = require('path'), fs = require('fs');

const LISTA = path.resolve(process.argv[2] || './evidencia.json');
const OUT = path.join(path.dirname(LISTA), 'evidencia');
fs.mkdirSync(OUT, { recursive: true });
const items = JSON.parse(fs.readFileSync(LISTA, 'utf8'));
const VPS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 }, tablet: { width: 768, height: 1024 } };
const UA = {
  desktop: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
  mobile: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
  tablet: 'Mozilla/5.0 (iPad; CPU OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/604.1',
};

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const filtro = process.argv[3]; // opcional: solo rehacer una entrada
  for (const it of items.filter(i => !filtro || i.nombre === filtro)) {
    const vp = it.vp || 'desktop';
    const ctx = await browser.newContext({ viewport: VPS[vp], deviceScaleFactor: 2, isMobile: vp === 'mobile', hasTouch: vp !== 'desktop', userAgent: UA[vp], locale: 'es-MX' });
    const page = await ctx.newPage();
    const destino = path.join(OUT, it.nombre + '.png');
    try {
      await page.goto(it.url, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(it.esperar ?? 1500);
      if (it.selector || it.clip || it.recorrer) { // dispara lazy-load antes de recortar abajo del pliegue
        await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight && y < 20000; y += 700) { scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } scrollTo(0, 0); });
        await page.waitForTimeout(it.esperarTras ?? 800);  // contadores y animaciones de entrada: dales tiempo (p. ej. 4000)
      }
      await page.evaluate(({ ocultar, resaltar, etiqueta }) => {
        const st = document.createElement('style');
        st.textContent = `.ne-resalta{outline:3px solid #ec4899 !important;outline-offset:4px !important;box-shadow:0 0 0 9px rgba(236,72,153,.18) !important;border-radius:4px}
          .ne-etq{position:absolute;z-index:2147483647;background:#ec4899;color:#fff;font:600 13px/1.2 Inter,Arial,sans-serif;padding:5px 9px;border-radius:6px;white-space:nowrap;pointer-events:none}`;
        document.head.appendChild(st);
        for (const s of ocultar || []) document.querySelectorAll(s).forEach(e => e.style.setProperty('display', 'none', 'important'));
        let primero = null;
        for (const s of resaltar || []) document.querySelectorAll(s).forEach(e => { e.classList.add('ne-resalta'); primero ||= e; });
        if (etiqueta && primero) {
          const r = primero.getBoundingClientRect(), d = document.createElement('div');
          d.className = 'ne-etq'; d.textContent = etiqueta;
          d.style.left = Math.max(8, r.left + scrollX) + 'px'; d.style.top = Math.max(8, r.top + scrollY - 34) + 'px';
          document.body.appendChild(d);
        }
      }, { ocultar: it.ocultar, resaltar: it.resaltar, etiqueta: it.etiqueta });
      await page.waitForTimeout(300);
      const m = it.margen ?? 24, altoMax = it.altoMax ?? 900;
      if (it.selector) {
        const loc = page.locator(it.selector).filter({ visible: true }).first();
        await loc.scrollIntoViewIfNeeded({ timeout: 5000 });
        const b = await loc.boundingBox();
        if (!b) throw new Error('selector sin caja visible');
        const sy = await page.evaluate(() => scrollY);
        const W = VPS[vp].width;
        const clip = { x: Math.max(0, b.x - m), y: Math.max(0, b.y + sy - m), width: Math.min(W - Math.max(0, b.x - m), b.width + 2 * m), height: Math.min(altoMax, b.height + 2 * m) };
        await page.evaluate(() => scrollTo(0, 0));
        await page.screenshot({ path: destino, clip, fullPage: true, omitBackground: !!it.transparente });
      } else if (it.clip) {
        const c = it.clip;
        await page.screenshot({ path: destino, clip: { x: c.x, y: c.y, width: c.w, height: Math.min(c.h, altoMax * 2) }, fullPage: true });
      } else {
        await page.screenshot({ path: destino });
      }
      console.log(`✓ ${it.nombre}.png  (${vp})`);
    } catch (e) {
      console.log(`✗ ${it.nombre}: ${String(e).slice(0, 140)}`);
    }
    await ctx.close();
  }
  await browser.close();
})();
