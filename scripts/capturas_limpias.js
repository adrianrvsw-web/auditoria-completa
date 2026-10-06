#!/usr/bin/env node
/**
 * capturas_limpias.js — repite las capturas del sitio sin ventanas emergentes ni chats
 *
 *   node capturas_limpias.js ../clientes/<slug>/config.json            # todas las páginas
 *   node capturas_limpias.js ../clientes/<slug>/config.json 01-home    # solo una
 *
 * Lee config.ocultar (selectores CSS: popup, chat, banner de cookies) y las páginas de
 * datos/sitio.json. Deja datos/capturas-limpias/<vp>-<id>.png y -full.png con los mismos
 * nombres y límites que recolectar.js. Las originales no se tocan: siguen siendo la evidencia
 * de lo que ve el visitante al llegar (p. ej. el hallazgo de la ventana emergente).
 *
 * construir.py las prefiere para la portada, «Cómo se ve hoy» y la galería. Solo lectura (GET).
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const CFG_PATH = path.resolve(process.argv[2] || './config.json');
const CFG = JSON.parse(fs.readFileSync(CFG_PATH, 'utf8'));
const ROOT = path.dirname(CFG_PATH);
const SITIO = JSON.parse(fs.readFileSync(path.join(ROOT, 'datos', 'sitio.json'), 'utf8'));
const OUT = path.join(ROOT, 'datos', 'capturas-limpias');
fs.mkdirSync(OUT, { recursive: true });
const SOLO = process.argv[3];
const OCULTAR = CFG.ocultar || [];
if (!OCULTAR.length) { console.error('config.json no tiene "ocultar": nada que quitar de las capturas'); process.exit(1); }

// mismos valores que recolectar.js
const UA = {
  desktop: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
  mobile: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
};
const VIEWPORTS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } };
const TOPE = { desktop: 7000, mobile: 9000 };

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const css = OCULTAR.map(s => `${s}{display:none!important}`).join('') + 'html,body{overflow:auto!important}';  // los popups suelen bloquear el desplazamiento
  for (const { id, url } of SITIO.paginas) {
    if (SOLO && id !== SOLO) continue;
    for (const vp of ['desktop', 'mobile']) {
      const ctx = await browser.newContext({ viewport: VIEWPORTS[vp], deviceScaleFactor: vp === 'mobile' ? 2 : 1, isMobile: vp === 'mobile', hasTouch: vp !== 'desktop', userAgent: UA[vp], locale: CFG.locale || 'es-MX' });
      const page = await ctx.newPage();
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 60000 });
        await page.waitForTimeout(2500);
        await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight && y < 25000; y += innerHeight * 0.8) { scrollTo(0, y); await new Promise(r => setTimeout(r, 180)); } scrollTo(0, 0); });
        await page.addStyleTag({ content: css });
        await page.waitForTimeout(1500);
        const base = path.join(OUT, `${vp}-${id}`);
        await page.screenshot({ path: base + '.png' });
        const alto = await page.evaluate(() => document.documentElement.scrollHeight);
        await page.screenshot({ path: base + '-full.png', fullPage: alto <= TOPE[vp], clip: alto > TOPE[vp] ? { x: 0, y: 0, width: VIEWPORTS[vp].width, height: TOPE[vp] } : undefined });
        console.log(`✓ ${vp}-${id}`);
      } catch (e) { console.log(`✗ ${vp}-${id}: ${String(e).slice(0, 120)}`); }
      await ctx.close();
    }
  }
  await browser.close();
})();
