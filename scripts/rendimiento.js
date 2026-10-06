/* ════════════════════════════════════════════════════════════════════
   rendimiento.js — velocidad real y de laboratorio con PageSpeed Insights
   Uso:  node rendimiento.js ../clientes/<slug>/config.json

   Requiere haber corrido recolectar.js (usa datos/sitio.json para elegir páginas).
   Mide: home (móvil ×2 y escritorio), y hasta 2 páginas clave más en móvil.
   Si config.competidores trae URLs, mide su home en móvil y lee señales básicas.

   API key opcional: variable PSI_API_KEY; como alternativa en macOS, llavero del
   equipo Newemage (servicio "newemage-launch", cuenta "psi-newemage"). Nunca se imprime.

   HONESTIDAD DE LA MEDIDA: una pasada de Lighthouse varía varios puntos entre
   ejecuciones. La home móvil se mide dos veces y se reporta el rango; nunca se
   presenta una diferencia menor al ruido como mejora o empeoramiento.
   ════════════════════════════════════════════════════════════════════ */
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');

const CFG_PATH = path.resolve(process.argv[2] || './config.json');
const CFG = JSON.parse(fs.readFileSync(CFG_PATH, 'utf8'));
const OUT = path.join(path.dirname(CFG_PATH), 'datos');
const sitio = JSON.parse(fs.readFileSync(path.join(OUT, 'sitio.json'), 'utf8'));

function apiKey() {
  if (process.env.PSI_API_KEY) return process.env.PSI_API_KEY;
  if (process.platform !== 'darwin') return null;
  try { return execFileSync('security', ['find-generic-password', '-s', 'newemage-launch', '-a', 'psi-newemage', '-w'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }
  catch { return null; }
}
const KEY = apiKey();
if (!KEY) console.log('! Sin API key de PageSpeed: se intenta sin clave (cupo muy bajo).');

const sleep = ms => new Promise(r => setTimeout(r, ms));
const AUDITS = ['render-blocking-resources', 'unused-javascript', 'unused-css-rules', 'modern-image-formats', 'uses-optimized-images', 'uses-responsive-images',
  'offscreen-images', 'uses-text-compression', 'uses-long-cache-ttl', 'total-byte-weight', 'dom-size', 'third-party-summary', 'bootup-time', 'mainthread-work-breakdown',
  'largest-contentful-paint-element', 'lcp-lazy-loaded', 'font-display', 'server-response-time', 'redirects', 'efficient-animated-content', 'legacy-javascript', 'duplicated-javascript', 'unminified-javascript', 'unminified-css'];

let psiBloqueado = false;
async function psi(url, strategy) {
  if (psiBloqueado) return lighthouseLocal(url, strategy);
  const q = new URLSearchParams({ url, strategy, locale: 'es' });
  for (const c of ['performance', 'accessibility', 'best-practices', 'seo']) q.append('category', c);
  if (KEY) q.set('key', KEY);
  for (let intento = 1; intento <= 3; intento++) {
    try {
      const r = await fetch('https://www.googleapis.com/pagespeedonline/v5/runPagespeed?' + q, { signal: AbortSignal.timeout(150000) });
      const j = await r.json();
      if (j.error) throw new Error(j.error.message?.slice(0, 160));
      return { ...resumir(j, url, strategy), fuente: 'pagespeed' };
    } catch (e) {
      console.log(`  ! ${strategy} ${url} intento ${intento}: ${String(e.message || e).slice(0, 140)}`);
      if (/Something went wrong|FAILED_DOCUMENT_REQUEST|ERRORED_DOCUMENT_REQUEST/.test(String(e.message)) && intento >= 2) { psiBloqueado = true; break; }
      if (intento < 3) await sleep(15000 * intento);
    }
  }
  console.log(`  → PageSpeed no pudo; se mide con Lighthouse local (${strategy})`);
  return lighthouseLocal(url, strategy);
}

// Respaldo: el mismo Lighthouse, en este equipo, con el Chrome instalado y la
// red móvil SIMULADA de Lighthouse. Pasa cuando el sitio bloquea a los
// servidores de Google (p. ej. Cloudflare). Sin datos de campo: no existen aquí.
async function lighthouseLocal(url, strategy) {
  const { default: lighthouse } = await import('lighthouse');
  const chromeLauncher = await import('chrome-launcher');
  const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless=new', '--no-first-run'] });
  try {
    const config = strategy === 'desktop' ? (await import('lighthouse/core/config/desktop-config.js')).default : undefined;
    const r = await lighthouse(url, { port: chrome.port, output: 'json', logLevel: 'error', locale: 'es',
      onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] }, config);
    if (!r?.lhr || r.lhr.runtimeError) throw new Error(r?.lhr?.runtimeError?.message || 'sin resultado');
    return { ...resumir({ lighthouseResult: r.lhr }, url, strategy), fuente: 'lighthouse-local' };
  } catch (e) {
    return { url, strategy, error: 'Ni PageSpeed ni Lighthouse local pudieron medir: ' + String(e.message || e).slice(0, 120) };
  } finally { await chrome.kill(); }
}

function campo(le) {
  if (!le || !le.metrics) return null;
  const m = le.metrics, g = k => m[k] ? { p75: m[k].percentile, categoria: m[k].category } : null;
  return { categoria: le.overall_category || null, lcp: g('LARGEST_CONTENTFUL_PAINT_MS'), inp: g('INTERACTION_TO_NEXT_PAINT'), cls: g('CUMULATIVE_LAYOUT_SHIFT_SCORE'),
    fcp: g('FIRST_CONTENTFUL_PAINT_MS'), ttfb: g('EXPERIMENTAL_TIME_TO_FIRST_BYTE') };
}

function resumir(j, url, strategy) {
  const lr = j.lighthouseResult, a = lr.audits;
  const n = id => a[id]?.numericValue ?? null;
  const oportunidades = AUDITS.filter(id => a[id] && a[id].score !== null && a[id].score < 0.9)
    .map(id => ({ id, titulo: a[id].title, valor: a[id].displayValue || null, ahorroMs: a[id].details?.overallSavingsMs || a[id].metricSavings?.LCP || null,
      ahorroKB: a[id].details?.overallSavingsBytes ? Math.round(a[id].details.overallSavingsBytes / 1024) : null, score: a[id].score }))
    .sort((x, y) => (y.ahorroMs || 0) - (x.ahorroMs || 0));
  const terceros = (a['third-party-summary']?.details?.items || []).slice(0, 8).map(i => ({ entidad: i.entity?.text || i.entity, kb: Math.round((i.transferSize || 0) / 1024), bloqueoMs: Math.round(i.blockingTime || 0) }));
  return {
    url, strategy, fecha: lr.fetchTime, lighthouse: lr.lighthouseVersion,
    puntuaciones: Object.fromEntries(Object.entries(lr.categories).map(([k, v]) => [k, Math.round((v.score ?? 0) * 100)])),
    laboratorio: { lcp: n('largest-contentful-paint'), fcp: n('first-contentful-paint'), tbt: n('total-blocking-time'), cls: n('cumulative-layout-shift'), si: n('speed-index'), tti: n('interactive'),
      pesoKB: n('total-byte-weight') ? Math.round(n('total-byte-weight') / 1024) : null, elementoLCP: a['largest-contentful-paint-element']?.details?.items?.[0]?.items?.[0]?.node?.snippet?.slice(0, 160) || null },
    campoURL: j.loadingExperience && !j.loadingExperience.origin_fallback ? campo(j.loadingExperience) : null,
    campoOrigen: campo(j.originLoadingExperience),
    oportunidades, terceros,
  };
}

async function senalesCompetidor(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(20000), headers: { 'user-agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/140 Safari/537.36' } }).catch(() => null);
  if (!r) return { error: 'no respondió' };
  const h = await r.text(); const o = new URL(r.url).origin;
  const llms = await fetch(o + '/llms.txt', { signal: AbortSignal.timeout(10000) }).then(x => x.status === 200 && x.text()).catch(() => false);
  return {
    final: r.url, https: r.url.startsWith('https'), descripcion: /<meta[^>]+name=["']description/i.test(h), og: /property=["']og:image/i.test(h),
    jsonld: (h.match(/application\/ld\+json/gi) || []).length, whatsapp: /wa\.me|api\.whatsapp/i.test(h), tel: /href=["']tel:/i.test(h),
    ga4: /G-[A-Z0-9]{6,}|gtag\/js/.test(h), gtm: /GTM-[A-Z0-9]{4,}/.test(h), metaPixel: /fbevents|fbq\(/.test(h),
    llmsTxt: !!(llms && !/<html/i.test(llms.slice(0, 300))), wordpress: /wp-content/.test(h),
    anioPie: Math.max(0, ...[...h.matchAll(/(?:©|&copy;|copyright)[^\d]{0,40}((?:19|20)\d{2})/gi)].map(m => +m[1])) || null,
  };
}

(async () => {
  const pags = sitio.paginas;
  const clave = pags.slice(1).filter(p => /contact|cotiz|servicio|producto|solucion|tienda/i.test(p.url)).slice(0, 2);
  const res = { fecha: new Date().toISOString(), conClave: !!KEY, mediciones: [] };
  const plan = [[pags[0].url, 'mobile'], [pags[0].url, 'desktop'], ...clave.map(p => [p.url, 'mobile']), [pags[0].url, 'mobile']];
  for (const [i, [u, s]] of plan.entries()) {
    console.log(`· PageSpeed ${s} ${u}`);
    res.mediciones.push(await psi(u, s));
    // PageSpeed devuelve el mismo análisis cacheado un rato: la segunda pasada de la home va al final
    if (i < plan.length - 1) await sleep(4000);
  }
  const homeMob = res.mediciones.filter(m => m.url === pags[0].url && m.strategy === 'mobile' && m.puntuaciones);
  if (homeMob.length) {
    const ps = homeMob.map(m => m.puntuaciones.performance);
    res.homeMovil = { min: Math.min(...ps), max: Math.max(...ps), pasadas: ps.length, variacion: Math.max(...ps) - Math.min(...ps), inestable: Math.max(...ps) - Math.min(...ps) > 8 };
  }
  if ((CFG.competidores || []).length) {
    res.competidores = [];
    for (const c of CFG.competidores) {
      console.log(`· Competidor ${c.nombre}: ${c.url}`);
      const m = await psi(c.url, 'mobile');
      res.competidores.push({ nombre: c.nombre, url: c.url, movil: m.puntuaciones || null, campo: m.campoOrigen || null, lcp: m.laboratorio?.lcp || null, senales: await senalesCompetidor(c.url) });
    }
    res.clienteSenales = await senalesCompetidor(sitio.home);
  }
  fs.writeFileSync(path.join(OUT, 'rendimiento.json'), JSON.stringify(res, null, 1));
  const h = res.mediciones.find(m => m.puntuaciones);
  console.log(`\n✓ rendimiento.json · home móvil ${res.homeMovil ? res.homeMovil.min + '–' + res.homeMovil.max : 's/d'} · escritorio ${res.mediciones[1]?.puntuaciones?.performance ?? 's/d'}`);
})();
