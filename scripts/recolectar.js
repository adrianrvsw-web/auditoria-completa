/* ════════════════════════════════════════════════════════════════════
   recolectar.js — recorrido de SOLO LECTURA del sitio de un cliente
   Uso:  node recolectar.js ../clientes/<slug>/config.json

   Qué deja en clientes/<slug>/datos/:
     sitio.json            nivel sitio: redirecciones, cabeceras, TLS, robots,
                           sitemap, llms.txt, 404, WordPress expuesto, enlaces
     paginas/NN-slug.json  por página: SEO, formularios, contacto, CTAs,
                           medición, tecnología, axe, imágenes, red, móvil
     capturas/             desktop/mobile (pliegue y completa), tablet solo home
     crudo/NN-slug.html    HTML servido sin JavaScript (lo que ve un rastreador)

   Reglas duras (no se relajan):
   · Nunca envía formularios, nunca hace clic en compras ni crea cuentas.
   · Solo GET/HEAD. Ninguna petición que cambie algo en el servidor.
   · No guarda cookies, tokens ni nombres de usuario de nadie.
   ════════════════════════════════════════════════════════════════════ */
const { chromium } = require('playwright-core');
const path = require('path'), fs = require('fs'), tls = require('tls');

const CFG_PATH = path.resolve(process.argv[2] || './config.json');
const CFG = JSON.parse(fs.readFileSync(CFG_PATH, 'utf8'));
const ROOT = path.dirname(CFG_PATH);
const OUT = path.join(ROOT, 'datos');
for (const d of ['paginas', 'capturas', 'crudo']) fs.mkdirSync(path.join(OUT, d), { recursive: true });

const MAX = CFG.maxPaginas || 10;
const UA = {
  desktop: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
  mobile: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
  tablet: 'Mozilla/5.0 (iPad; CPU OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/604.1',
};
const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
};
const AI_BOTS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'anthropic-ai',
  'PerplexityBot', 'Google-Extended', 'Applebot-Extended', 'CCBot', 'Bytespider', 'meta-externalagent'];
const SKIP_EXT = /\.(pdf|zip|rar|jpe?g|png|gif|webp|svg|avif|mp4|mp3|docx?|xlsx?|pptx?|css|js|xml|txt|ico)$/i;
const SKIP_PATH = /\/(wp-admin|wp-login|wp-json|feed|tag|author|page\/\d+|cart|carrito|checkout|my-account|mi-cuenta|login|cdn-cgi)(\/|$)|\/(ingresar|acceso|signin|sign-in|registro|register)(\.php|\.html?)?$|[?&](s|p|replytocom|add-to-cart)=/i;
// Versiones en otro idioma: se audita el idioma principal (config.incluirIdiomas para forzarlas)
const SKIP_LANG = /[\/_-](en|eng|english|fr|pt|de|it)(\/|$|\.)/i;

const log = (...a) => console.log(...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const hostSinWww = h => h.replace(/^www\./, '');

// ── HTTP de solo lectura ────────────────────────────────────────────
async function get(url, { method = 'GET', redirect = 'follow', timeout = 20000, ua = UA.desktop } = {}) {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), timeout);
  try {
    const r = await fetch(url, { method, redirect, signal: ctl.signal, headers: { 'user-agent': ua, 'accept-language': 'es-MX,es;q=0.9' } });
    const headers = Object.fromEntries(r.headers.entries());
    const body = method === 'HEAD' || redirect === 'manual' ? '' : await r.text();
    return { ok: true, status: r.status, url: r.url, headers, body };
  } catch (e) {
    return { ok: false, status: 0, error: String(e.cause?.code || (/redirect count/i.test(e.cause?.message || '') ? 'BUCLE_DE_REDIRECCIONES' : '') || e.cause?.message || e.name || e).slice(0, 80) };
  } finally { clearTimeout(t); }
}

async function cadena(url) { // sigue redirecciones a mano para ver cada salto
  const saltos = []; let u = url;
  for (let i = 0; i < 8; i++) {
    const r = await get(u, { redirect: 'manual', timeout: 15000 });
    saltos.push({ url: u, status: r.status, error: r.error });
    if (!r.ok || r.status < 300 || r.status >= 400 || !r.headers.location) break;
    u = new URL(r.headers.location, u).href;
  }
  return { desde: url, final: saltos.at(-1)?.url, statusFinal: saltos.at(-1)?.status, saltos };
}

function certificado(host) {
  return new Promise(res => {
    const s = tls.connect({ host, port: 443, servername: host, timeout: 10000 }, () => {
      const c = s.getPeerCertificate();
      res({ validoHasta: c.valid_to, emisor: c.issuer?.O || c.issuer?.CN, protocolo: s.getProtocol(), autorizado: s.authorized });
      s.end();
    });
    s.on('error', e => res({ error: String(e.code || e) }));
    s.on('timeout', () => { res({ error: 'timeout' }); s.destroy(); });
  });
}

function robotsParse(txt) {
  const grupos = []; let g = null, prevUA = false;
  for (const raw of txt.split(/\r?\n/)) {
    const l = raw.replace(/#.*/, '').trim(); if (!l) continue;
    const m = l.match(/^([a-z-]+)\s*:\s*(.*)$/i); if (!m) continue;
    const k = m[1].toLowerCase(), v = m[2].trim();
    if (k === 'user-agent') { if (!prevUA || !g) { g = { agentes: [], disallow: [], allow: [] }; grupos.push(g); } g.agentes.push(v.toLowerCase()); prevUA = true; continue; }
    prevUA = false;
    if (!g) continue;
    if (k === 'disallow') g.disallow.push(v);
    if (k === 'allow') g.allow.push(v);
  }
  const sitemaps = [...txt.matchAll(/^\s*sitemap\s*:\s*(\S+)/gim)].map(m => m[1]);
  const bloqueaTodo = agente => {
    const a = agente.toLowerCase();
    const grupo = grupos.find(x => x.agentes.includes(a)) || grupos.find(x => x.agentes.includes('*'));
    if (!grupo) return false;
    return grupo.disallow.includes('/') && !grupo.allow.includes('/');
  };
  return { grupos, sitemaps, bloqueaTodo };
}

async function leerSitemaps(candidatas) {
  const urls = [], vistos = new Set(), cola = [...candidatas], encontrados = [];
  while (cola.length && vistos.size < 25) {
    const sm = cola.shift(); if (vistos.has(sm)) continue; vistos.add(sm);
    const r = await get(sm, { timeout: 20000 });
    if (!r.ok || r.status !== 200 || !/<(urlset|sitemapindex)/i.test(r.body)) continue;
    encontrados.push(sm);
    if (/<sitemapindex/i.test(r.body)) {
      for (const m of r.body.matchAll(/<sitemap>[\s\S]*?<loc>\s*(?:<!\[CDATA\[)?([^<\]]+)/gi)) cola.push(m[1].trim());
    } else {
      for (const m of r.body.matchAll(/<url>([\s\S]*?)<\/url>/gi)) {
        const loc = (m[1].match(/<loc>\s*(?:<!\[CDATA\[)?([^<\]]+)/i) || [])[1];
        const lastmod = (m[1].match(/<lastmod>\s*([^<]+)/i) || [])[1];
        if (loc) urls.push({ loc: loc.trim(), lastmod: lastmod?.trim() || null, sitemap: sm });
        if (urls.length > 3000) break;
      }
    }
  }
  return { encontrados, urls };
}

function slugDe(u, i) {
  const p = new URL(u).pathname.replace(/\/+$/, '').split('/').filter(Boolean).pop() || 'home';
  return String(i).padStart(2, '0') + '-' + p.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40);
}

function prioridad(u, orden) {
  const p = decodeURIComponent(new URL(u).pathname.toLowerCase());
  if (/contact|cotiza|quote|presupuesto|agenda/.test(p)) return 100;
  if (/servicio|service|producto|product|solucion|solution|catalogo|tienda|shop|linea/.test(p)) return 90 - Math.min(orden, 9) / 10;
  if (/nosotros|about|quienes|empresa|conoce|historia/.test(p)) return 80;
  if (/blog|noticia|news|articulo|recursos|prensa/.test(p)) return 70;
  if (/privacidad|privacy|aviso|terminos|legal|cookies/.test(p)) return 5;
  return 50 - Math.min(orden, 40);
}

// ── Lo que se lee DENTRO de cada página (se ejecuta en el navegador) ──
function extraer(vp) {
  const t = el => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
  const vw = innerWidth, vh = innerHeight;
  const visible = el => { const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05; };
  const meta = n => document.querySelector(`meta[name="${n}" i],meta[property="${n}" i]`)?.content ?? null;
  const host = location.hostname.replace(/^www\./, '');
  const esInterno = h => { try { const u = new URL(h, location.href); return u.hostname.replace(/^www\./, '') === host; } catch { return false; } };

  // JSON-LD: tipos y datos de entidad
  const ld = [], tipos = new Set(); let org = null;
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const j = JSON.parse(s.textContent);
      const walk = o => { if (!o || typeof o !== 'object') return; if (Array.isArray(o)) return o.forEach(walk);
        const ty = [].concat(o['@type'] || []); ty.forEach(x => tipos.add(x));
        if (!org && ty.some(x => /Organization|LocalBusiness|Corporation|Store|Restaurant|MedicalBusiness|ProfessionalService/i.test(x)))
          org = { tipo: ty.join(','), nombre: !!o.name, telefono: !!o.telephone, direccion: !!o.address, logo: !!o.logo, sameAs: [].concat(o.sameAs || []).length, url: !!o.url };
        Object.values(o).forEach(walk); };
      walk(j); ld.push('ok');
    } catch { ld.push('invalido'); }
  }

  // Formularios
  const labelDe = el => {
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l && t(l)) return { txt: t(l), real: true }; }
    const cl = el.closest('label'); if (cl && t(cl)) return { txt: t(cl), real: true };
    if (el.getAttribute('aria-label')) return { txt: el.getAttribute('aria-label'), real: true };
    const lb = el.getAttribute('aria-labelledby'); if (lb) { const x = document.getElementById(lb); if (x) return { txt: t(x), real: true }; }
    return { txt: el.placeholder || el.name || '', real: false };
  };
  const formularios = [...document.querySelectorAll('form')].map(f => {
    const campos = [...f.querySelectorAll('input,textarea,select')]
      .filter(e => !['hidden', 'submit', 'button', 'reset', 'image'].includes((e.type || '').toLowerCase()) && visible(e))
      .map(e => { const l = labelDe(e); return { tipo: e.tagName === 'INPUT' ? (e.type || 'text') : e.tagName.toLowerCase(), etiqueta: l.txt.slice(0, 60), etiquetaReal: l.real,
        obligatorio: e.required || e.getAttribute('aria-required') === 'true' || /\*/.test(l.txt), autocomplete: e.getAttribute('autocomplete') || null }; });
    const tipos_ = campos.map(c => c.tipo);
    let clase = 'contacto';
    if (tipos_.includes('password')) clase = 'login';
    else if (tipos_.includes('search') || (campos.length === 1 && /buscar|search|^s$|^q$/i.test(f.querySelector('input:not([type=hidden])')?.name + ' ' + campos[0]?.etiqueta))) clase = 'busqueda';
    else if (campos.length <= 2 && tipos_.includes('email') && !tipos_.includes('textarea')) clase = 'newsletter';
    const zona = f.parentElement?.parentElement || f;
    const txtZona = t(zona).toLowerCase();
    const r = f.getBoundingClientRect();
    return {
      clase, visible: visible(f), campos, nCampos: campos.length,
      obligatorios: campos.filter(c => c.obligatorio).length,
      soloPlaceholder: campos.filter(c => !c.etiquetaReal).length,
      boton: t(f.querySelector('button[type=submit],input[type=submit],button:not([type]),.elementor-button,[type=submit]')).slice(0, 40) || f.querySelector('input[type=submit]')?.value || null,
      captcha: !!f.querySelector('.g-recaptcha,[class*=recaptcha],.h-captcha,.cf-turnstile,iframe[src*="recaptcha"],iframe[src*="hcaptcha"]') || !!document.querySelector('.grecaptcha-badge'),
      avisoPrivacidad: /privacidad|privacy|datos personales/.test(txtZona) || !!zona.querySelector('a[href*="privacidad"],a[href*="privacy"],a[href*="aviso"]'),
      casillaAcepto: !!f.querySelector('input[type=checkbox]') && /acept|privacidad|t[ée]rminos/.test(t(f).toLowerCase()),
      plugin: /wpcf7/.test(f.className) ? 'Contact Form 7' : /elementor/.test(f.className) ? 'Elementor' : /gform/.test(f.id + f.className) ? 'Gravity Forms' : /wpforms/.test(f.className) ? 'WPForms' : /hs-form|hbspt/.test(f.className) ? 'HubSpot' : null,
      yTop: Math.round(r.top + scrollY),
    };
  });
  const iframesForm = [...document.querySelectorAll('iframe')].map(i => i.src).filter(s => /typeform|jotform|forms\.gle|docs\.google\.com\/forms|hsforms|forms\.office|calendly|tally\.so/.test(s));

  // Canales de contacto
  const hrefs = [...document.querySelectorAll('a[href]')].map(a => ({ a, h: a.getAttribute('href') || '' }));
  const tels = [...new Set(hrefs.filter(x => /^tel:/i.test(x.h)).map(x => x.h.replace(/\D/g, '').slice(-10)))];
  const whats = hrefs.filter(x => /wa\.me|api\.whatsapp|web\.whatsapp|whatsapp:\/\//i.test(x.h));
  const whatsNums = whats.map(x => (x.h.match(/(?:wa\.me\/|phone=)\+?(\d+)/i) || [])[1]).filter(Boolean);
  const whatsFlotante = whats.some(x => { let e = x.a; for (let i = 0; i < 5 && e; i++, e = e.parentElement) if (getComputedStyle(e).position === 'fixed') return true; return false; });
  const cuerpo = t(document.body);
  const telsTexto = [...new Set((cuerpo.match(/(?:\+?52[\s.-]?)?(?:\(?\d{2,3}\)?[\s.-]?)\d{3,4}[\s.-]?\d{4}\b/g) || [])
    .map(x => x.replace(/\D/g, '').slice(-10)).filter(x => x.length === 10))];
  const redes = {};
  for (const [k, re] of Object.entries({ facebook: /facebook\.com/, instagram: /instagram\.com/, linkedin: /linkedin\.com/, youtube: /youtube\.com|youtu\.be/, tiktok: /tiktok\.com/, x: /twitter\.com|\/\/x\.com/, googleplus: /plus\.google\.com/, pinterest: /pinterest\./ }))
    { const m = hrefs.find(x => re.test(x.h)); if (m) redes[k] = m.h; }

  // CTAs visibles
  const reFuerte = /contact|cotiz|presupuesto|agend|solicit|llam|whats|escr[ií]b|habl|quote|demo|compr|ped(ir|ido)|reserv|asesor|inscr|registr|comienza|empieza|prueba/i;
  const esBoton = e => { const s = getComputedStyle(e); const bg = s.backgroundColor;
    return e.tagName === 'BUTTON' || e.type === 'submit' || /btn|button|cta/i.test(e.className?.baseVal ?? e.className ?? '') ||
      (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg) && parseFloat(s.paddingLeft) >= 8) || (parseFloat(s.borderWidth) >= 1 && parseFloat(s.borderRadius) >= 4 && parseFloat(s.paddingLeft) >= 10); };
  const ctas = [...document.querySelectorAll('a,button,input[type=submit],[role=button]')]
    .filter(e => visible(e) && esBoton(e) && (t(e) || e.value) && (t(e) || e.value).length <= 50 && !e.closest('form[role=search]'))
    .map(e => { const r = e.getBoundingClientRect(); const txt = (t(e) || e.value).slice(0, 50);
      return { txt, fuerte: reFuerte.test(txt + ' ' + (e.getAttribute('href') || '')), pliegue: r.top < vh && r.bottom > 0 && r.top >= -5, y: Math.round(r.top + scrollY) }; });

  // Imágenes
  const imgs = [...document.images].map(im => { const r = im.getBoundingClientRect(); const src = im.currentSrc || im.src || '';
    return { src: src.slice(0, 300), alt: im.getAttribute('alt'), nw: im.naturalWidth, nh: im.naturalHeight, dw: Math.round(r.width), dh: Math.round(r.height),
      rota: !!src && im.complete && im.naturalWidth === 0, lazy: im.loading === 'lazy' || /lazy/.test(im.className), ext: (src.split('?')[0].match(/\.(\w{3,4})$/) || [])[1]?.toLowerCase() || null }; });

  // Texto pequeño y tipografía
  let chars = 0, charsPeq = 0; const muestraPeq = [], familias = {};
  for (const el of document.querySelectorAll('p,li,span,a,td,label,small,div')) {
    const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (own.length < 3 || !visible(el)) continue;
    const s = getComputedStyle(el), fs = parseFloat(s.fontSize);
    chars += own.length; if (fs < 12) { charsPeq += own.length; if (muestraPeq.length < 5) muestraPeq.push(`${fs}px «${own.slice(0, 40)}»`); }
    const fam = s.fontFamily.split(',')[0].replace(/["']/g, '').trim(); familias[fam] = (familias[fam] || 0) + own.length;
  }
  const h1Style = document.querySelector('h1') ? getComputedStyle(document.querySelector('h1')) : null;

  // Desbordes y elementos fijos (sobre todo en móvil)
  const anchoDoc = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  const desbordan = anchoDoc > vw + 2 ? [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.right > vw + 2 && r.width > 0 && visible(e) && getComputedStyle(e).position !== 'fixed'; })
    .slice(0, 400).filter((e, _, arr) => !arr.includes(e.parentElement)).slice(0, 5).map(e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : ''} (${Math.round(e.getBoundingClientRect().right)}px)`) : [];
  let areaFija = 0; const fijos = [];
  for (const e of document.querySelectorAll('body *')) {
    const s = getComputedStyle(e); if (!['fixed', 'sticky'].includes(s.position) || !visible(e)) continue;
    const r = e.getBoundingClientRect(); if (r.bottom <= 0 || r.top >= vh) continue;
    const a = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    if (a > vw * vh * 0.02 && !fijos.some(f => f.el.contains(e))) { fijos.push({ el: e, txt: t(e).slice(0, 60), pct: Math.round(a * 100 / (vw * vh)) }); areaFija += a; }
  }
  const centro = document.elementFromPoint(vw / 2, vh / 2);
  let tapa = null; for (let e = centro; e && e !== document.body; e = e.parentElement) {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    if ((s.position === 'fixed' || e.tagName === 'DIALOG') && r.width > vw * .5 && r.height > vh * .3) { tapa = { txt: t(e).slice(0, 120), cubre: Math.round(r.width * r.height * 100 / (vw * vh)) }; break; } }
  const objetivosChicos = vp === 'mobile' ? [...document.querySelectorAll('a,button,input,select,[role=button]')].filter(e => {
    if (!visible(e)) return false; const r = e.getBoundingClientRect(); if (r.width === 0) return false;
    if (e.tagName === 'A' && e.closest('p,li') && t(e.closest('p,li')).length > t(e).length + 20) return false; // enlace dentro de texto: excepción WCAG
    return (r.width < 24 || r.height < 24); }).map(e => (t(e) || e.getAttribute('aria-label') || e.tagName).slice(0, 30)) : null;

  // Tecnología
  const html = document.documentElement.outerHTML;
  const gen = [...document.querySelectorAll('meta[name=generator]')].map(m => m.content);
  const verWP = (gen.join(' ').match(/WordPress\s+([\d.]+)/) || html.match(/wp-(?:emoji-release|includes\/[^"']+)\.m?i?n?\.?js\?ver=([\d.]+)/) || [])[1] || null;
  const tech = {
    generador: gen, wordpress: /wp-content|wp-includes/.test(html), versionWP: verWP,
    elementor: /elementor/.test(html), wpbakery: /vc_row|js_composer/.test(html), divi: /et_pb_/.test(html), avada: /fusion-builder|avada/i.test(html),
    revslider: /revslider|rev_slider|rs-module/.test(html), woocommerce: /woocommerce/.test(html),
    wix: /wixstatic|wix\.com/.test(html), squarespace: /squarespace/.test(html), shopify: /cdn\.shopify|Shopify\.theme/.test(html),
    webflow: !!document.documentElement.getAttribute('data-wf-site'), joomla: gen.some(g => /joomla/i.test(g)), drupal: /drupal/i.test(gen.join(' ') + (window.Drupal ? 'drupal' : '')),
    godaddy: /img1\.wsimg\.com|godaddy/i.test(html), vtex: /vtex/i.test(html), prestashop: typeof window.prestashop !== 'undefined',
    jquery: window.jQuery?.fn?.jquery || null, jqueryMigrate: /jquery-migrate/.test(html),
    bootstrap: window.bootstrap?.Tooltip?.VERSION || window.jQuery?.fn?.tooltip?.Constructor?.VERSION || null,
    seoPlugin: /rank-math|rankmath/i.test(html) ? 'Rank Math' : /yoast/i.test(html) ? 'Yoast' : /siteseo/i.test(html) ? 'SiteSEO' : /aioseo|all in one seo/i.test(html) ? 'All in One SEO' : null,
    flash: !!document.querySelector('object[type*=flash],embed[src$=".swf"],object[data$=".swf"]'),
    tipografias: Object.entries(familias).sort((a, b) => b[1] - a[1]).slice(0, 4).map(x => x[0]),
    tipografiaH1: h1Style?.fontFamily.split(',')[0].replace(/["']/g, '') || null,
  };
  const scriptsTxt = [...document.scripts].map(s => (s.src || '') + ' ' + (s.src ? '' : s.textContent.slice(0, 4000))).join('\n');
  const idsMedicion = {
    ga4: [...new Set(scriptsTxt.match(/\bG-[A-Z0-9]{6,12}\b/g) || [])],
    ua: [...new Set(scriptsTxt.match(/\bUA-\d{4,10}-\d{1,3}\b/g) || [])],
    gtm: [...new Set(scriptsTxt.match(/\bGTM-[A-Z0-9]{4,9}\b/g) || [])],
    ads: [...new Set(scriptsTxt.match(/\bAW-\d{6,12}\b/g) || [])],
    metaPixel: /fbq\(\s*['"]init/.test(scriptsTxt),
  };

  // Vigencia: año del pie y fechas publicadas
  const pie = document.querySelector('footer') || [...document.querySelectorAll('body > *')].slice(-3).at(-1);
  const txtPie = t(pie) + ' ' + cuerpo.slice(-600);
  const anios = [...txtPie.matchAll(/(?:©|copyright|derechos reservados|todos los derechos)[^\d]{0,40}((?:19|20)\d{2})(?:\s*[-–]\s*((?:19|20)\d{2}))?/gi)].flatMap(m => [m[1], m[2]].filter(Boolean).map(Number));
  const fechas = [...document.querySelectorAll('time[datetime]')].map(x => x.getAttribute('datetime')).concat([meta('article:published_time'), meta('article:modified_time')].filter(Boolean)).slice(0, 12);

  // Enlaces
  const internos = new Set(), externos = new Set(), anclasRotas = [];
  for (const { a, h } of hrefs) {
    if (!h || /^(mailto|tel|javascript|sms|whatsapp):/i.test(h)) continue;
    if (h.startsWith('#')) { if (h.length > 1 && !document.getElementById(decodeURIComponent(h.slice(1))) && !document.getElementsByName(h.slice(1)).length) anclasRotas.push(h); continue; }
    try { const u = new URL(h, location.href); u.hash = ''; (esInterno(u.href) ? internos : externos).add(u.href); } catch {}
  }

  const nav = performance.getEntriesByType('navigation')[0];
  const main = document.querySelector('main,[role=main],article') || document.body;
  return {
    titulo: document.title, descripcion: meta('description'), canonical: document.querySelector('link[rel=canonical]')?.href || null,
    robots: meta('robots'), lang: document.documentElement.lang || null, viewportMeta: meta('viewport'),
    og: { titulo: meta('og:title'), descripcion: meta('og:description'), imagen: meta('og:image'), tipo: meta('og:type') }, twitter: meta('twitter:card'),
    hreflang: [...document.querySelectorAll('link[rel=alternate][hreflang]')].map(l => l.hreflang),
    favicon: !!document.querySelector('link[rel~=icon]'), appleIcon: !!document.querySelector('link[rel=apple-touch-icon]'),
    h1: [...document.querySelectorAll('h1')].filter(visible).map(t).slice(0, 5), h1Total: document.querySelectorAll('h1').length,
    h2: [...document.querySelectorAll('h2')].filter(visible).map(t).filter(Boolean).slice(0, 20),
    saltosEncabezado: (() => { let prev = 0, n = 0; for (const h of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) { const l = +h.tagName[1]; if (prev && l > prev + 1) n++; prev = l; } return n; })(),
    jsonld: { bloques: ld.length, invalidos: ld.filter(x => x === 'invalido').length, tipos: [...tipos], organizacion: org },
    microdatos: document.querySelectorAll('[itemtype]').length,
    palabras: (t(main).match(/\S+/g) || []).length, palabrasTotal: (cuerpo.match(/\S+/g) || []).length,
    // Relleno de plantilla VISIBLE (innerText, no comentarios del HTML: ver lecciones)
    textoRelleno: [...new Set((cuerpo.match(/lorem ipsum[^.]{0,30}|dolor sit amet|texto de ejemplo|contenido de prueba|sample page|p[aá]gina de ejemplo|hello world|hola,? mundo|just another wordpress site|otro sitio realizado con wordpress|responsive html5? template|your (company|title|text) here|tu (t[ií]tulo|texto) aqu[ií]/gi) || []).concat(cuerpo.match(/\b(TODO|FIXME|XXX)\b/g) || []).map(x => x.slice(0, 50)))].slice(0, 6), // TODO solo en mayúsculas: «todo» es español
    textoCaducado: [...new Set((cuerpo.match(/covid[- ]?19|coronavirus|contingencia sanitaria|sana distancia|google\+|flash player|internet explorer/gi) || []).map(x => x.toLowerCase()))],
    formularios, iframesForm,
    contacto: { tels, telsTexto, telsSinEnlace: telsTexto.filter(x => !tels.includes(x) && !whatsNums.some(w => w.endsWith(x))), whatsapp: whats.length, whatsFlotante,
      whatsNums, whatsSinPais: whatsNums.filter(w => w.length === 10),  // wa.me exige clave de país (52…): sin ella WhatsApp no reconoce el número
      mailto: hrefs.filter(x => /^mailto:/i.test(x.h)).length, mapa: hrefs.some(x => /google\.[a-z.]+\/maps|goo\.gl\/maps|maps\.app\.goo\.gl/.test(x.h)) || !!document.querySelector('iframe[src*="google.com/maps"]'), redes },
    ctas: { total: ctas.length, fuertes: ctas.filter(c => c.fuerte).length, pliegue: ctas.filter(c => c.pliegue).map(c => c.txt), pliegueFuertes: ctas.filter(c => c.pliegue && c.fuerte).map(c => c.txt), lista: ctas.slice(0, 25).map(c => c.txt) },
    imagenes: { total: imgs.length, sinAlt: imgs.filter(i => i.alt === null).length, altVacio: imgs.filter(i => i.alt === '').length, rotas: imgs.filter(i => i.rota).map(i => i.src),
      sobredimensionadas: imgs.filter(i => i.dw > 0 && i.nw > 800 && i.nw > i.dw * 2.5).map(i => ({ src: i.src, natural: i.nw + '×' + i.nh, mostrada: i.dw + '×' + i.dh })).slice(0, 10),
      formatos: imgs.reduce((o, i) => (i.ext && (o[i.ext] = (o[i.ext] || 0) + 1), o), {}), lazy: imgs.filter(i => i.lazy).length },
    textoPequeno: { pct: chars ? Math.round(charsPeq * 100 / chars) : 0, muestra: muestraPeq },
    desborde: { anchoDoc, excede: anchoDoc > vw + 2, elementos: desbordan },
    fijos: { pctPantalla: Math.round(areaFija * 100 / (vw * vh)), lista: fijos.map(f => ({ txt: f.txt, pct: f.pct })) },
    capaCentro: tapa, objetivosChicos: objetivosChicos ? { total: objetivosChicos.length, muestra: objetivosChicos.slice(0, 8) } : null,
    tecnologia: tech, idsMedicion,
    vigencia: { aniosPie: anios, anioPie: anios.length ? Math.max(...anios) : null, fechas },
    enlaces: { internos: [...internos].slice(0, 300), externos: [...externos].slice(0, 150), anclasRotas: [...new Set(anclasRotas)].slice(0, 10) },
    iframes: [...document.querySelectorAll('iframe')].map(i => (i.src || '').slice(0, 120)).filter(Boolean).slice(0, 10),
    video: document.querySelectorAll('video, iframe[src*=youtube], iframe[src*=vimeo]').length,
    tiempos: nav ? { ttfb: Math.round(nav.responseStart), dcl: Math.round(nav.domContentLoadedEventEnd), load: Math.round(nav.loadEventEnd), bytesHTML: nav.transferSize } : null,
    nav: [...document.querySelectorAll('header a, nav a')].map(a => ({ txt: t(a).slice(0, 40), href: a.href })).filter(x => x.txt).slice(0, 40),
    menuMovil: [...document.querySelectorAll('header button, header a, header [role=button], nav button, [class*=hamburger], [class*=burger], [class*=toggle], [class*=collapse-nav], [aria-expanded], [aria-controls*=menu i], [aria-label*=menu i]')]
      .some(e => visible(e) && (/hamburger|burger|toggle|collapse|menu-btn|nav-btn|mobile-menu|offcanvas/i.test((e.className?.baseVal ?? e.className ?? '') + ' ' + (e.getAttribute('aria-label') || '')) || e.hasAttribute('aria-expanded') || /^[☰≡]$/.test(t(e)))),
  };
}

const MEDICION = [
  ['GA4', /googletagmanager\.com\/gtag\/js\?id=G-|google-analytics\.com\/g\/collect|analytics\.google\.com\/g\/collect/],
  ['Universal Analytics (obsoleto)', /google-analytics\.com\/(analytics|ga)\.js|google-analytics\.com\/(r\/)?collect\?v=1|gtag\/js\?id=UA-/],
  ['Google Tag Manager', /googletagmanager\.com\/gtm\.js/],
  ['Google Ads', /googleadservices\.com|gtag\/js\?id=AW-|googleads\.g\.doubleclick\.net/],
  ['Meta Pixel', /connect\.facebook\.net\/[^/]+\/fbevents|facebook\.com\/tr[/?]/],
  ['LinkedIn Insight', /snap\.licdn\.com|px\.ads\.linkedin/], ['TikTok Pixel', /analytics\.tiktok\.com/],
  ['Hotjar', /hotjar\.com/], ['Microsoft Clarity', /clarity\.ms/], ['HubSpot', /js\.hs-scripts|js\.hs-analytics|js\.hsforms/], ['Matomo', /matomo|piwik/],
];
const CHAT = [['Tawk.to', /tawk\.to/], ['Crisp', /crisp\.chat/], ['Intercom', /intercom/], ['Zendesk', /zdassets|zopim/], ['Tidio', /tidio/],
  ['LiveChat', /livechatinc/], ['JivoChat', /jivosite|jivo/], ['Drift', /drift\.com|driftt/], ['HubSpot Chat', /usemessages/], ['Joinchat (WhatsApp)', /joinchat/], ['Click to Chat (WhatsApp)', /ht-ctc|click-to-chat/], ['GetButton (WhatsApp)', /getbutton\.io/], ['Elfsight', /elfsight/]];
const CONSENT = [['Cookiebot', /cookiebot/], ['OneTrust', /onetrust|cookielaw/], ['CookieYes', /cookieyes|cookie-law-info/], ['Complianz', /complianz/], ['Borlabs', /borlabs/], ['iubenda', /iubenda/], ['Termly', /termly/]];

async function recorrerPagina(browser, url, id, vp, axeSrc) {
  const ctx = await browser.newContext({ viewport: VIEWPORTS[vp], deviceScaleFactor: vp === 'mobile' ? 2 : 1, isMobile: vp === 'mobile', hasTouch: vp !== 'desktop',
    userAgent: UA[vp], locale: CFG.locale || 'es-MX', bypassCSP: true, ignoreHTTPSErrors: false });
  const page = await ctx.newPage();
  const red = [], consola = [], fallidas = [];
  page.on('console', m => { if (m.type() === 'error') consola.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => consola.push('JS: ' + String(e).slice(0, 200)));
  page.on('requestfailed', r => fallidas.push({ url: r.url().slice(0, 200), error: r.failure()?.errorText }));
  page.on('requestfinished', async r => {
    try { const res = await r.response(); const s = await r.sizes();
      red.push({ url: r.url().slice(0, 300), tipo: r.resourceType(), status: res?.status(), bytes: s.responseBodySize + s.responseHeadersSize, ct: (res?.headers()['content-type'] || '').split(';')[0] });
    } catch {}
  });
  let status = null, final = url, error = null;
  try {
    const resp = await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    status = resp?.status(); final = page.url();
    await page.waitForTimeout(2500);
    // desplazarse para disparar lazy-load y animaciones de entrada; luego volver arriba
    await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight && y < 25000; y += innerHeight * 0.8) { scrollTo(0, y); await new Promise(r => setTimeout(r, 180)); } scrollTo(0, 0); });
    await page.waitForTimeout(1500);
  } catch (e) { error = String(e).slice(0, 200); }

  const r = { url, final, status, vp, error };
  if (!error) {
    const base = path.join(OUT, 'capturas', `${vp}-${id}`);
    try { await page.screenshot({ path: base + '.png' }); } catch {}
    try {
      const alto = await page.evaluate(() => document.documentElement.scrollHeight);
      const tope = vp === 'mobile' ? 9000 : 7000;
      await page.screenshot({ path: base + '-full.png', fullPage: alto <= tope, clip: alto > tope ? { x: 0, y: 0, width: VIEWPORTS[vp].width, height: tope } : undefined });
      r.altoPagina = alto;
    } catch {}
    r.dom = await page.evaluate(extraer, vp).catch(e => ({ error: String(e).slice(0, 200) }));
    if (axeSrc) {
      try {
        await page.evaluate(axeSrc);
        const ax = await page.evaluate(() => window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] }, resultTypes: ['violations'] }));
        r.axe = ax.violations.map(v => ({ id: v.id, impacto: v.impact, ayuda: v.help, nodos: v.nodes.length, muestra: v.nodes.slice(0, 3).map(n => n.target.join(' ')).map(s => s.slice(0, 120)) }));
      } catch (e) { r.axe = { error: String(e).slice(0, 150) }; }
    }
  }
  const host = hostSinWww(new URL(url).hostname);
  const todo = red.map(x => x.url).join('\n') + '\n' + (r.dom?.tecnologia ? '' : '');
  r.red = {
    peticiones: red.length, bytes: red.reduce((s, x) => s + (x.bytes || 0), 0),
    porTipo: red.reduce((o, x) => { o[x.tipo] = o[x.tipo] || { n: 0, bytes: 0 }; o[x.tipo].n++; o[x.tipo].bytes += x.bytes || 0; return o; }, {}),
    terceros: [...new Set(red.map(x => { try { return new URL(x.url).hostname; } catch { return null; } }).filter(h => h && !hostSinWww(h).endsWith(host)))],
    masPesadas: red.filter(x => x.bytes > 150 * 1024).sort((a, b) => b.bytes - a.bytes).slice(0, 8).map(x => ({ url: x.url, kb: Math.round(x.bytes / 1024), tipo: x.tipo })),
    imagenesLegado: red.filter(x => x.tipo === 'image' && /image\/(jpeg|png|gif|bmp)/.test(x.ct) && x.bytes > 100 * 1024).map(x => ({ url: x.url, kb: Math.round(x.bytes / 1024) })).slice(0, 15),
    mixto: final.startsWith('https:') ? red.filter(x => x.url.startsWith('http:')).map(x => x.url).slice(0, 10) : [],
    errores4xx5xx: red.filter(x => x.status >= 400).map(x => ({ url: x.url, status: x.status })).slice(0, 15),
    fallidas: fallidas.filter(f => !/ERR_ABORTED/.test(f.error || '')).slice(0, 10),
  };
  r.medicion = MEDICION.filter(([, re]) => red.some(x => re.test(x.url))).map(([n]) => n);
  r.chat = CHAT.filter(([, re]) => red.some(x => re.test(x.url)) || re.test(JSON.stringify(r.dom?.iframes || ''))).map(([n]) => n);
  r.consentimiento = CONSENT.filter(([, re]) => red.some(x => re.test(x.url))).map(([n]) => n);
  r.consola = [...new Set(consola)].slice(0, 15);
  await ctx.close();
  return r;
}

function analizarCrudo(html) {
  const sinScripts = html.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ').replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ');
  const texto = sinScripts.replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9]+;/gi, ' ').replace(/\s+/g, ' ').trim();
  return {
    bytes: Buffer.byteLength(html), palabras: (texto.match(/\S+/g) || []).length,
    titulo: (html.match(/<title[^>]*>([^<]*)/i) || [])[1]?.trim() || null,
    descripcion: /<meta[^>]+name=["']description["'][^>]*content=["'][^"']+/i.test(html) || /<meta[^>]+content=["'][^"']+["'][^>]*name=["']description/i.test(html),
    h1: (html.match(/<h1[\s>]/gi) || []).length, enlaces: (html.match(/<a\s[^>]*href=/gi) || []).length,
    jsonld: (html.match(/application\/ld\+json/gi) || []).length,
  };
}

async function revisarEnlaces(lista, esInterno) {
  const res = [], cola = [...lista];
  const trabajador = async () => {
    while (cola.length) {
      const u = cola.shift();
      let r = await get(u, { method: 'HEAD', timeout: 12000 });
      if (!r.ok || r.status === 405 || r.status === 403 || r.status === 501 || r.status === 404) r = await get(u, { timeout: 15000 });
      res.push({ url: u, status: r.status, error: r.error || null, interno: esInterno });
      await sleep(80);
    }
  };
  await Promise.all(Array.from({ length: 6 }, trabajador));
  return res;
}

(async () => {
  const t0 = Date.now();
  // ── 1 · Nivel sitio ──
  log('· Resolviendo dominio…');
  const inicio = await get(CFG.base);
  if (!inicio.ok) { console.error('No se pudo abrir ' + CFG.base + ': ' + inicio.error); process.exit(1); }
  if (/suspendedpage|cgi-sys\/|defaultwebpage|parked|sedoparking|coming-?soon|under-?construction|mantenimiento|maintenance/i.test(inicio.url + ' ' + inicio.body.slice(0, 3000).replace(/<[^>]+>/g, ' ').slice(0, 800))
      && inicio.body.length < 60000) {
    console.error(`\n⚠ ${CFG.base} termina en ${inicio.url}: parece un sitio SUSPENDIDO, en mantenimiento o sin publicar.\n  No se audita: avisa al equipo, es urgente para el cliente.`);
    process.exit(2);
  }
  const finalHome = inicio.url, origen = new URL(finalHome).origin, host = new URL(finalHome).hostname, desnudo = hostSinWww(host);
  const sitio = { cliente: CFG.cliente, base: CFG.base, home: finalHome, origen, fecha: new Date().toISOString() };
  sitio.variantes = await Promise.all([`http://${desnudo}/`, `http://www.${desnudo}/`, `https://${desnudo}/`, `https://www.${desnudo}/`].map(cadena));
  sitio.cabeceras = inicio.headers;
  sitio.tls = await certificado(host);

  log('· robots.txt, sitemap, llms.txt, 404…');
  const rb = await get(origen + '/robots.txt');
  const robotsOk = rb.ok && rb.status === 200 && !/<html/i.test(rb.body.slice(0, 300));
  const rp = robotsParse(robotsOk ? rb.body : '');
  sitio.robots = { existe: robotsOk, status: rb.status, texto: robotsOk ? rb.body.slice(0, 4000) : null, sitemaps: rp.sitemaps, bloqueaTodo: robotsOk && rp.bloqueaTodo('*'),
    botsIA: Object.fromEntries(AI_BOTS.map(b => [b, robotsOk && rp.bloqueaTodo(b) ? 'bloqueado' : 'permitido'])) };
  const sm = await leerSitemaps([...rp.sitemaps, origen + '/sitemap.xml', origen + '/sitemap_index.xml', origen + '/wp-sitemap.xml']);
  const fechasSm = sm.urls.map(u => u.lastmod && Date.parse(u.lastmod)).filter(Boolean).sort((a, b) => a - b);
  sitio.sitemap = { encontrados: sm.encontrados, urls: sm.urls.length, lastmodMasReciente: fechasSm.length ? new Date(fechasSm.at(-1)).toISOString().slice(0, 10) : null,
    lastmodMasAntiguo: fechasSm.length ? new Date(fechasSm[0]).toISOString().slice(0, 10) : null, conLastmod: fechasSm.length,
    muestra: sm.urls.slice(0, 60).map(u => u.loc) };
  const blogUrls = sm.urls.filter(u => /post-sitemap|posts-post|\/(blog|noticias|news|articulos)\//i.test(u.sitemap + ' ' + u.loc) && u.lastmod).sort((a, b) => Date.parse(b.lastmod) - Date.parse(a.lastmod));
  sitio.blog = blogUrls.length ? { entradas: blogUrls.length, ultima: blogUrls[0].lastmod.slice(0, 10), ultimaUrl: blogUrls[0].loc } : null;
  const llms = await get(origen + '/llms.txt');
  sitio.llmsTxt = { existe: llms.ok && llms.status === 200 && !/<html|<!doctype/i.test(llms.body.slice(0, 500)), status: llms.status };
  const p404 = await get(origen + '/pagina-que-no-existe-' + Date.now());
  sitio.error404 = { status: p404.status, soft404: p404.status === 200 };
  const fav = await get(origen + '/favicon.ico', { method: 'HEAD' });
  sitio.faviconIco = fav.status;

  // ── 2 · Descubrir páginas ──
  log('· Descubriendo páginas…');
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const axeSrc = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
  const ctx0 = await browser.newContext({ viewport: VIEWPORTS.desktop, userAgent: UA.desktop, locale: CFG.locale || 'es-MX' });
  const p0 = await ctx0.newPage();
  let navLinks = [];
  try {
    await p0.goto(finalHome, { waitUntil: 'load', timeout: 60000 }); await p0.waitForTimeout(2000);
    navLinks = await p0.evaluate(() => [...document.querySelectorAll('header a[href], nav a[href], [role=navigation] a[href], footer a[href]')].map(a => a.href));
  } catch (e) { log('  ! no se pudo leer la navegación: ' + String(e).slice(0, 100)); }
  await ctx0.close();
  const norm = u => { try { const x = new URL(u, finalHome); x.hash = ''; if (hostSinWww(x.hostname) !== desnudo) return null; x.hostname = host; x.protocol = new URL(finalHome).protocol;
    x.pathname = x.pathname.replace(/\/index\.(php|html?|asp)$/i, '/');
    if (SKIP_EXT.test(x.pathname) || SKIP_PATH.test(x.pathname + x.search)) return null;
    if (!CFG.incluirIdiomas && SKIP_LANG.test(x.pathname) && !SKIP_LANG.test(new URL(finalHome).pathname)) return null;
    return x.href.replace(/\/$/, '') || x.href; } catch { return null; } };
  const homeN = norm(finalHome) || finalHome.replace(/\/$/, '');
  const cand = new Map();
  navLinks.map(norm).filter(Boolean).forEach((u, i) => { if (u !== homeN && !cand.has(u)) cand.set(u, prioridad(u, i)); });
  sm.urls.map(u => norm(u.loc)).filter(Boolean).forEach(u => { if (u !== homeN && !cand.has(u)) cand.set(u, Math.min(prioridad(u, 40), 12)); });
  for (const extra of CFG.paginas || []) { const u = norm(new URL(extra, finalHome).href); if (u) cand.set(u, 200); }
  for (const ex of CFG.excluir || []) for (const k of [...cand.keys()]) if (k.includes(ex)) cand.delete(k);
  // Diversidad: como máximo 2 páginas por plantilla (primer segmento de la ruta: /categoria-producto/, /producto/…),
  // salvo las pedidas a mano en config.paginas. Evita que una tienda llene la muestra con categorías iguales.
  const plantilla = u => new URL(u).pathname.split('/').filter(Boolean).slice(0, 1).join('/') || '/';
  const porPlantilla = {}, elegidas = [homeN];
  for (const [u, pr] of [...cand.entries()].sort((a, b) => b[1] - a[1])) {
    if (elegidas.length >= MAX) break;
    const t = plantilla(u), segs = new URL(u).pathname.split('/').filter(Boolean).length;
    if (pr < 200 && segs > 1 && (porPlantilla[t] || 0) >= 2) continue;
    porPlantilla[t] = (porPlantilla[t] || 0) + 1; elegidas.push(u);
  }
  if (sitio.blog && !elegidas.includes(norm(sitio.blog.ultimaUrl)) && elegidas.length >= MAX) elegidas[elegidas.length - 1] = norm(sitio.blog.ultimaUrl) || elegidas.at(-1);
  sitio.candidatas = cand.size; sitio.paginas = elegidas.map((u, i) => ({ id: slugDe(u, i + 1), url: u }));
  log(`  ${elegidas.length} páginas elegidas de ${cand.size + 1} candidatas`);

  // ── 3 · Recorrer cada página ──
  const internos = new Set(), externos = new Set();
  for (const [i, { id, url }] of sitio.paginas.entries()) {
    log(`· [${i + 1}/${sitio.paginas.length}] ${url}`);
    const vps = i === 0 ? ['desktop', 'mobile', 'tablet'] : ['desktop', 'mobile'];
    const pag = { id, url, vistas: {} };
    for (const vp of vps) pag.vistas[vp] = await recorrerPagina(browser, url, id, vp, vp === 'desktop' ? axeSrc : null);
    const crudo = await get(url);
    if (crudo.ok) { fs.writeFileSync(path.join(OUT, 'crudo', id + '.html'), crudo.body); pag.crudo = { status: crudo.status, ...analizarCrudo(crudo.body) }; }
    pag.cabeceras = crudo.headers || null;
    const d = pag.vistas.desktop.dom;
    (d?.enlaces?.internos || []).forEach(u => internos.add(u)); (d?.enlaces?.externos || []).forEach(u => externos.add(u));
    fs.writeFileSync(path.join(OUT, 'paginas', id + '.json'), JSON.stringify(pag, null, 1));
  }
  await browser.close();

  // ── 4 · WordPress expuesto (solo si es WordPress) ──
  const primera = JSON.parse(fs.readFileSync(path.join(OUT, 'paginas', sitio.paginas[0].id + '.json'), 'utf8'));
  if (primera.vistas.desktop.dom?.tecnologia?.wordpress) {
    log('· Revisión pública de WordPress…');
    const us = await get(origen + '/wp-json/wp/v2/users');
    let nUsuarios = 0; try { nUsuarios = us.status === 200 ? JSON.parse(us.body).length : 0; } catch {}
    const xr = await get(origen + '/xmlrpc.php');
    const vc = await get('https://api.wordpress.org/core/version-check/1.7/');
    let ultimaWP = null; try { ultimaWP = JSON.parse(vc.body).offers[0].current || JSON.parse(vc.body).offers[0].version; } catch {}
    const readme = await get(origen + '/readme.html', { method: 'HEAD' });
    sitio.wordpress = { usuariosExpuestos: nUsuarios, xmlrpcActivo: xr.status === 200 || /XML-RPC server accepts POST/i.test(xr.body || '') || xr.status === 405, readmeExpuesto: readme.status === 200, ultimaVersionWP: ultimaWP };
  }

  // ── 5 · Enlaces rotos ──
  const intLista = [...internos].filter(u => !SKIP_PATH.test(u)).slice(0, 220);
  const extLista = [...externos].filter(u => !/facebook\.com\/sharer|twitter\.com\/intent|linkedin\.com\/share|wa\.me|whatsapp|pinterest\.com\/pin\/create/.test(u)).slice(0, 80);
  log(`· Revisando ${intLista.length} enlaces internos y ${extLista.length} externos…`);
  const enl = [...await revisarEnlaces(intLista, true), ...await revisarEnlaces(extLista, false)];
  sitio.enlaces = {
    internosRevisados: intLista.length, externosRevisados: extLista.length,
    rotosInternos: enl.filter(e => e.interno && (e.status >= 400 || e.status === 0)).map(e => ({ url: e.url, status: e.status || e.error })),
    rotosExternos: enl.filter(e => !e.interno && ([404, 410].includes(e.status) || /ENOTFOUND|ECONNREFUSED|CERT/.test(e.error || ''))).map(e => ({ url: e.url, status: e.status || e.error })),
  };
  sitio.duracionSeg = Math.round((Date.now() - t0) / 1000);
  fs.writeFileSync(path.join(OUT, 'sitio.json'), JSON.stringify(sitio, null, 1));
  log(`\n✓ Listo en ${sitio.duracionSeg}s → ${OUT}`);
})();
