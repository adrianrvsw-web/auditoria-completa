/* Diagnóstico digital · Newemage — interacciones. Sin dependencias.
   El contenido ya está en el HTML: si este archivo falla, la pieza se lee igual. */
(() => {
  const $ = (s, c = document) => c.querySelector(s), $$ = (s, c = document) => [...c.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const nav = $('.nav'), barra = $('.progress'), fab = $('.toc-fab');

  // Índice: el enlace activo es la última sección cuyo inicio ya pasó bajo la barra
  const enlaces = $$('.toc ol a[href^="#"]');
  const destinos = enlaces.map(a => [a, document.getElementById(a.getAttribute('href').slice(1))]).filter(x => x[1]);
  const marcar = () => {
    const y = (nav ? nav.offsetHeight : 64) + 90;
    let activo = null, activoSub = null;
    for (const [a, el] of destinos) {
      if (el.getBoundingClientRect().top - y > 0) continue;
      if (a.closest('.toc__sub')) activoSub = a; else { activo = a; activoSub = null; }
    }
    enlaces.forEach(a => a.classList.toggle('on', a === activo || a === activoSub));
  };

  // Aparición por POSICIÓN (no por intersección): también aparece lo que quedó
  // arriba al saltar con un enlace del índice o al desplazarse muy rápido.
  const llenar = r => {
    if (r.dataset.hecho) return; r.dataset.hecho = 1;
    const n = $('.ring__num', r), v = +r.dataset.v || 0;
    if (n && !reduce) { let t0; const f = t => { t0 ??= t; const k = Math.min(1, (t - t0) / 1200); n.textContent = Math.round(v * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(f); }; requestAnimationFrame(f); }
  };
  let pend = $$('.rv');
  const revelar = () => {
    if (!pend.length) return;
    const lim = innerHeight * 0.94;
    pend = pend.filter(el => {
      if (el.getBoundingClientRect().top >= lim) return true;
      el.classList.add('in'); $$('.ring', el).forEach(llenar); if (el.classList.contains('ring')) llenar(el);
      return false;
    });
  };

  const alDesplazar = () => {
    const y = scrollY, alto = document.documentElement.scrollHeight - innerHeight;
    nav && nav.classList.toggle('solid', y > 40);
    if (barra) barra.style.transform = `scaleX(${alto > 0 ? Math.min(1, y / alto) : 0})`;
    fab && fab.classList.toggle('show', y > innerHeight * 0.6);
    revelar(); marcar();
  };
  addEventListener('scroll', alDesplazar, { passive: true }); addEventListener('resize', alDesplazar); alDesplazar();

  // Índice en teléfono: panel inferior
  const abrir = v => { document.body.classList.toggle('toc-open', v); fab && fab.setAttribute('aria-expanded', String(v)); if (v) { const x = $('.toc ol a.on') || $('.toc ol a'); x && x.focus({ preventScroll: true }); } };
  fab && fab.addEventListener('click', () => abrir(!document.body.classList.contains('toc-open')));
  $('.toc__close') && $('.toc__close').addEventListener('click', () => { abrir(false); fab && fab.focus(); });
  $('.toc-scrim') && $('.toc-scrim').addEventListener('click', () => abrir(false));
  enlaces.forEach(a => a.addEventListener('click', () => abrir(false)));

  // Visor de evidencia (normal o página completa desplazable)
  const lb = $('.lb');
  if (lb) {
    const img = $('img', lb), cap = $('p', lb), box = $('.lb__box', lb); let volver = null;
    const cerrar = () => { lb.classList.remove('on', 'tall'); document.body.style.overflow = ''; volver && volver.focus(); };
    $$('button.frame').forEach(b => b.addEventListener('click', () => {
      const mini = $('img', b); volver = b;
      img.hidden = false; img.src = b.dataset.full || mini.src; img.alt = mini.alt; cap.textContent = b.dataset.cap || '';
      lb.classList.toggle('tall', 'tall' in b.dataset); lb.classList.add('on'); box.scrollTop = 0;
      document.body.style.overflow = 'hidden'; $('.lb__x', lb).focus();
    }));
    $('.lb__x', lb).addEventListener('click', cerrar);
    lb.addEventListener('click', e => { if (e.target === lb) cerrar(); });
    addEventListener('keydown', e => { if (e.key !== 'Escape') return; if (lb.classList.contains('on')) cerrar(); else if (document.body.classList.contains('toc-open')) abrir(false); });
  }

  // Ir a un hallazgo oculto dentro de «ver más»: abrirlo primero
  addEventListener('click', e => {
    const a = e.target.closest('a[href^="#h-"]'); if (!a) return;
    const t = document.getElementById(a.getAttribute('href').slice(1)); if (!t) return;
    const d = t.closest('details'); if (d && !d.open) d.open = true;
  });

  // Filtros del anexo (área y resultado se combinan)
  $$('.filters').forEach(f => {
    const id = f.dataset.for, tabla = document.getElementById(id); if (!tabla) return;
    f.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      $$(`.filters[data-for="${id}"] button[data-k="${b.dataset.k}"]`).forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      const act = k => ($(`.filters[data-for="${id}"] button[data-k="${k}"][aria-pressed="true"]`) || { dataset: {} }).dataset.v;
      const area = act('area') || 'todas', st = act('st') || 'todos';
      $$('tbody tr', tabla).forEach(tr => { tr.hidden = !((area === 'todas' || tr.dataset.area === area) && (st === 'todos' || tr.dataset.st === st)); });
    });
  });

  // Imprimir / guardar como PDF: todo abierto y visible
  addEventListener('beforeprint', () => { $$('details').forEach(d => { d.dataset.was = d.open; d.open = true; }); $$('.rv').forEach(x => x.classList.add('in')); });
  addEventListener('afterprint', () => $$('details').forEach(d => { d.open = d.dataset.was === 'true'; }));
})();
