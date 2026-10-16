// Lightweight interactions for the notebook. No framework, no dependencies.
// Everything here is progressive enhancement: the page works without it.

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

/* ---------- Scroll reveals + self-drawing strokes ---------- */
function initReveals() {
  const targets = document.querySelectorAll('.reveal, .draw');
  if (!('IntersectionObserver' in window) || reduceMotion) {
    targets.forEach((el) => el.classList.add('is-in'));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      }
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.12 },
  );
  targets.forEach((el) => io.observe(el));
}

/* ---------- Section tracking: tabs + address bar ---------- */
function initSectionTracking() {
  const sections = document.querySelectorAll('[data-section]');
  const links = new Map([...document.querySelectorAll('[data-nav-link]')].map((a) => [a.dataset.navLink, a]));
  const address = document.querySelector('[data-address]');
  if (!sections.length || !('IntersectionObserver' in window)) return;

  const setActive = (id) => {
    links.forEach((link, key) => {
      if (key === id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    if (address) address.textContent = id || 'hello';
  };

  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) setActive(entry.target.dataset.section);
      }
    },
    { rootMargin: '-45% 0px -50% 0px' },
  );
  sections.forEach((s) => io.observe(s));

  const hero = document.querySelector('[data-hero]');
  if (hero) {
    new IntersectionObserver(([entry]) => entry.isIntersecting && setActive(null), {
      rootMargin: '-45% 0px -50% 0px',
    }).observe(hero);
  }
}

/* ---------- Mobile menu (disclosure) ---------- */
function initMenu() {
  const button = document.querySelector('[data-menu-btn]');
  const nav = document.querySelector('[data-nav]');
  if (!button || !nav) return;

  const close = (focusButton = false) => {
    button.setAttribute('aria-expanded', 'false');
    nav.removeAttribute('data-open');
    if (focusButton) button.focus();
  };
  button.addEventListener('click', () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(open));
    nav.toggleAttribute('data-open', open);
    if (open) nav.querySelector('a')?.focus();
  });
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a')) close();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.hasAttribute('data-open')) close(true);
  });
  document.addEventListener('click', (e) => {
    if (nav.hasAttribute('data-open') && !nav.contains(e.target) && !button.contains(e.target)) close();
  });
}

/* ---------- Hero: pointer parallax + doodle eyes (desktop only) ---------- */
function initHeroPointer() {
  const hero = document.querySelector('[data-hero]');
  if (!hero) return;
  hero.querySelectorAll('[data-depth]').forEach((el) => el.style.setProperty('--depth', el.dataset.depth));
  if (reduceMotion || !finePointer) return;

  const pupils = [...hero.querySelectorAll('[data-pupil]')];
  const bot = hero.querySelector('.bot__svg');
  let rect = hero.getBoundingClientRect();
  let botRect = bot?.getBoundingClientRect();
  let frame = 0;
  let px = 0;
  let py = 0;

  const measure = () => {
    rect = hero.getBoundingClientRect();
    botRect = bot?.getBoundingClientRect();
  };
  window.addEventListener('resize', measure, { passive: true });
  window.addEventListener('scroll', measure, { passive: true });

  const render = () => {
    frame = 0;
    const mx = ((px - rect.left) / rect.width - 0.5) * 2;
    const my = ((py - rect.top) / rect.height - 0.5) * 2;
    hero.style.setProperty('--mx', (-mx * 4).toFixed(2));
    hero.style.setProperty('--my', (-my * 3).toFixed(2));

    if (botRect && pupils.length) {
      const cx = botRect.left + botRect.width / 2;
      const cy = botRect.top + botRect.height * 0.38;
      const angle = Math.atan2(py - cy, px - cx);
      const dist = Math.min(1, Math.hypot(px - cx, py - cy) / 260);
      const dx = Math.cos(angle) * 4.5 * dist;
      const dy = Math.sin(angle) * 4.5 * dist;
      pupils.forEach((p) => p.setAttribute('transform', `translate(${dx.toFixed(2)} ${dy.toFixed(2)})`));
    }
  };

  window.addEventListener(
    'pointermove',
    (e) => {
      px = e.clientX;
      py = e.clientY;
      if (!frame) frame = requestAnimationFrame(render);
    },
    { passive: true },
  );
}

/* ---------- Doodle robot speech ---------- */
function initBot() {
  const button = document.querySelector('[data-bot-btn]');
  const say = document.querySelector('[data-bot-say]');
  const data = document.getElementById('bot-lines');
  if (!button || !say || !data) return;
  const lines = JSON.parse(data.textContent || '[]');
  let i = 0;
  button.addEventListener('click', () => {
    if (!lines.length) return;
    say.textContent = lines[i % lines.length];
    i += 1;
  });
}

/* ---------- Polaroid flip ---------- */
function initFlip() {
  const portrait = document.querySelector('[data-portrait]');
  if (!portrait) return;
  const button = portrait.querySelector('[data-flip]');
  const card = portrait.querySelector('[data-flip-card]');
  const toggle = () => {
    const flipped = !portrait.hasAttribute('data-flipped');
    portrait.toggleAttribute('data-flipped', flipped);
    button.setAttribute('aria-pressed', String(flipped));
  };
  button.addEventListener('click', toggle);
  card.addEventListener('click', toggle);
}

/* ---------- Gentle card tilt (desktop) ---------- */
function initTilt() {
  if (reduceMotion || !finePointer) return;
  document.querySelectorAll('[data-tilt]').forEach((el) => {
    let rect = null;
    let frame = 0;
    let x = 0;
    let y = 0;
    const update = () => {
      frame = 0;
      if (!rect) return;
      const rx = ((y - rect.top) / rect.height - 0.5) * -7;
      const ry = ((x - rect.left) / rect.width - 0.5) * 9;
      el.style.setProperty('--rx', `${rx.toFixed(2)}deg`);
      el.style.setProperty('--ry', `${ry.toFixed(2)}deg`);
    };
    el.addEventListener('pointerenter', () => {
      rect = el.getBoundingClientRect();
    });
    el.addEventListener('pointermove', (e) => {
      x = e.clientX;
      y = e.clientY;
      if (!frame) frame = requestAnimationFrame(update);
    });
    el.addEventListener('pointerleave', () => {
      rect = null;
      el.style.setProperty('--rx', '0deg');
      el.style.setProperty('--ry', '0deg');
    });
  });
}

/* ---------- Copy email ---------- */
function initCopy() {
  document.querySelectorAll('[data-copy]').forEach((button) => {
    const status = button.parentElement.querySelector('[data-copy-status]');
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        if (status) status.textContent = 'copied ✓';
      } catch {
        if (status) status.textContent = 'select & copy it above';
      }
      setTimeout(() => status && (status.textContent = ''), 2600);
    });
  });
}

/* ---------- Screenshot lightbox ---------- */
function initLightbox() {
  const dialog = document.querySelector('[data-lightbox-dialog]');
  const links = [...document.querySelectorAll('[data-lightbox]')];
  if (!dialog || !links.length || typeof dialog.showModal !== 'function') return;
  const img = dialog.querySelector('[data-lightbox-img]');
  const caption = dialog.querySelector('[data-lightbox-caption]');
  let index = 0;
  let opener = null;

  const show = (i) => {
    index = (i + links.length) % links.length;
    const link = links[index];
    const thumb = link.querySelector('img');
    img.src = link.href;
    img.alt = thumb?.alt || '';
    caption.textContent = `${link.dataset.caption || ''} (${index + 1}/${links.length})`;
  };
  links.forEach((link, i) =>
    link.addEventListener('click', (e) => {
      e.preventDefault();
      opener = link;
      show(i);
      dialog.showModal();
    }),
  );
  dialog.querySelector('[data-lightbox-prev]').addEventListener('click', () => show(index - 1));
  dialog.querySelector('[data-lightbox-next]').addEventListener('click', () => show(index + 1));
  dialog.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') show(index - 1);
    if (e.key === 'ArrowRight') show(index + 1);
  });
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => opener?.focus());
}

/* ---------- Playground: load only when it is about to be seen ---------- */
function initPlayground() {
  const root = document.querySelector('[data-playground]');
  if (!root) return;
  let loaded = false;
  const load = () => {
    if (loaded) return;
    loaded = true;
    import(root.dataset.src).then((m) => m.mount(root));
  };
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          io.disconnect();
          load();
        }
      },
      { rootMargin: '600px 0px' },
    );
    io.observe(root);
  }
  root.addEventListener('focusin', load, { once: true });
  root.addEventListener('pointerenter', load, { once: true });
}

initReveals();
initSectionTracking();
initMenu();
initHeroPointer();
initBot();
initFlip();
initTilt();
initCopy();
initLightbox();
initPlayground();
