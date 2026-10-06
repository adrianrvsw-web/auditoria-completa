/* ════════════════════════════════════════════════════════════════════
   verificar.js — QA del entregable antes de mandarlo
   Uso:  node verificar.js ../clientes/<slug>

   Abre presentacion/index.html en 1440, 768 y 390 px y comprueba:
   desbordes horizontales, texto que se sale de su tarjeta, imágenes rotas,
   anclas sin destino, errores de consola, marcadores {{…}} sin sustituir,
   accesibilidad (axe, WCAG 2.1 AA) de la propia pieza, y que el visor de
   evidencia y los «ver más» respondan.
   Deja capturas completas en qa/ (fuera de presentacion/). Sale con 1 si algo falla.
   ════════════════════════════════════════════════════════════════════ */
const { chromium } = require('playwright-core');
const path = require('path'), fs = require('fs');

const RAIZ = path.resolve(process.argv[2] || '.');
const HTML = path.join(RAIZ, 'presentacion', 'index.html');
const QA = path.join(RAIZ, 'qa');
fs.mkdirSync(QA, { recursive: true });
const axeSrc = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const VPS = { desktop: [1440, 900], tablet: [768, 1024], mobile: [390, 844] };

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const problemas = [];
  for (const [vp, [w, h]] of Object.entries(VPS)) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, isMobile: vp === 'mobile', hasTouch: vp === 'mobile' });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', m => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) errs.push(m.text().slice(0, 160)); });
    page.on('pageerror', e => errs.push('JS: ' + String(e).slice(0, 160)));
    await page.goto('file://' + HTML, { waitUntil: 'load' });
    // recorrer para disparar las apariciones y cargar imágenes lazy
    await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { scrollTo({ top: y, behavior: 'instant' }); await new Promise(r => setTimeout(r, 90)); } scrollTo({ top: 0, behavior: 'instant' }); });
    await page.waitForTimeout(1600);
    const r = await page.evaluate(() => {
      const out = {};
      out.ancho = document.documentElement.scrollWidth;
      out.imgsRotas = [...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src'));
      out.anclas = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')).filter(h => h.length > 1 && !document.getElementById(h.slice(1)));
      out.marcadores = (document.body.innerText.match(/\{\{[^}]*\}\}|REDACTAR|undefined|NaN|\bnull\b/g) || []).slice(0, 5);
      out.fuera = [...document.querySelectorAll('.card, .chip, .kv span, .front__svc li, .dot, .lbl, .btn')].filter(el => {
        const r = el.getBoundingClientRect(); if (!r.width) return false;
        return el.scrollWidth > el.clientWidth + 2 || r.right > innerWidth + 1;
      }).slice(0, 6).map(el => `${el.className} «${(el.innerText || '').slice(0, 40)}»`);
      out.invisibles = [...document.querySelectorAll('.rv')].filter(x => !x.classList.contains('in')).length;
      return out;
    });
    if (r.ancho > w + 1) problemas.push(`[${vp}] desborde horizontal: ${r.ancho}px en ${w}px`);
    r.imgsRotas.forEach(x => problemas.push(`[${vp}] imagen rota: ${x}`));
    [...new Set(r.anclas)].forEach(x => problemas.push(`[${vp}] ancla sin destino: ${x}`));
    r.marcadores.forEach(x => problemas.push(`[${vp}] texto sin sustituir o valor vacío: ${x}`));
    r.fuera.forEach(x => problemas.push(`[${vp}] contenido que se sale de su caja: ${x}`));
    if (r.invisibles) problemas.push(`[${vp}] ${r.invisibles} bloque(s) que nunca aparecieron (animación .rv)`);
    errs.forEach(x => problemas.push(`[${vp}] consola: ${x}`));

    // Índice: visible y con sección activa en escritorio; panel que abre y cierra en tableta y teléfono
    const mitad = await page.evaluate(() => { const a = document.getElementById('areas'); return a ? a.offsetTop + 400 : 3000; });
    await page.evaluate(y => window.scrollTo({ top: y, behavior: 'instant' }), mitad); await page.waitForTimeout(250);
    if (w > 1100) {
      const toc = await page.evaluate(() => { const i = document.querySelector('.toc__in'); if (!i) return null; const r = i.getBoundingClientRect(); return { top: r.top, h: r.height, activo: (document.querySelector('.toc a.on') || {}).textContent || '' }; });
      if (!toc) problemas.push(`[${vp}] no hay índice lateral`);
      else { if (toc.top < 0 || toc.top > h / 2 || toc.h < 100) problemas.push(`[${vp}] el índice lateral no queda fijo a la vista (top ${Math.round(toc.top)})`);
             if (!toc.activo) problemas.push(`[${vp}] el índice no marca la sección activa`); }
      await page.screenshot({ path: path.join(QA, `qa-${vp}-indice.png`) });
    } else {
      const fab = page.locator('.toc-fab');
      if (!(await fab.isVisible())) problemas.push(`[${vp}] no aparece el botón «Índice»`);
      else {
        await fab.click(); await page.waitForTimeout(450);
        if (!(await page.locator('.toc a').first().isVisible())) problemas.push(`[${vp}] el panel del índice no abre`);
        await page.screenshot({ path: path.join(QA, `qa-${vp}-indice.png`) });
        await page.keyboard.press('Escape'); await page.waitForTimeout(450);
        if (await page.evaluate(() => document.body.classList.contains('toc-open'))) problemas.push(`[${vp}] el panel del índice no cierra con Escape`);
      }
    }
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' })); await page.waitForTimeout(600); // la barra tiene transición de color

    if (vp === 'desktop') {
      await page.evaluate(axeSrc);
      const ax = await page.evaluate(() => axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } }));
      ax.violations.filter(v => ['critical', 'serious'].includes(v.impact)).forEach(v => problemas.push(`[axe] ${v.id} (${v.impact}) ×${v.nodes.length}: ${v.nodes[0]?.target.join(' ')}`));
      // interacciones
      const ev = page.locator('.stage button.frame').first();
      if (await ev.count()) {
        await ev.click(); await page.waitForTimeout(250);
        if (!(await page.locator('.lb.on').count())) problemas.push('[desktop] el visor de evidencia no abre');
        await page.keyboard.press('Escape'); await page.waitForTimeout(150);
        if (await page.locator('.lb.on').count()) problemas.push('[desktop] el visor no se cierra con Escape');
      }
      const more = page.locator('.area details.more > summary').first();
      if (await more.count()) { await more.click(); if (!(await page.locator('.area details.more[open]').count())) problemas.push('[desktop] «ver más» no abre'); await more.click(); }
      const fb = page.locator('.filters button[data-v="falla"]').first();
      if (await fb.count()) {
        await page.locator('#anexo details.block').nth(1).evaluate(d => d.open = true);
        await fb.click();
        const visibles = await page.$$eval('#tbl-checks tbody tr', trs => trs.filter(t => !t.hidden).map(t => t.dataset.st));
        if (visibles.some(s => s !== 'falla')) problemas.push('[desktop] el filtro del anexo no filtra');
      }
    }
    // Chrome no captura más de 16 384 px de alto de una vez: por tramos
    const alto = await page.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0, n = 1; y < alto; y += 12000, n++)
      await page.screenshot({ path: path.join(QA, `qa-${vp}-${n}.png`), fullPage: true, clip: { x: 0, y, width: w, height: Math.min(12000, alto - y) } });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(QA, 'informe-qa.txt'), problemas.join('\n') || 'Sin problemas');
  if (problemas.length) { console.log(`✗ ${problemas.length} problema(s):\n  ` + problemas.join('\n  ')); process.exit(1); }
  console.log(`✓ QA limpio en 1440 / 768 / 390 · capturas en ${QA}`);
})();
