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

/* ---------- Page turns: arrow keys, swipes, old #section links ---------- */
const OLD_SECTION_LINKS = {
  '#work': '/work/',
  '#about': '/about/',
  '#toolkit': '/toolkit/',
  '#journey': '/journey/',
  '#contact': '/contact/',
};

/* Leaves: a dense page is split into leaves that turn one at a time on screens
   big enough to show a leaf without scrolling. Smaller screens stack them. */
const FIT_QUERY = '(min-width: 64rem) and (min-height: 37.5rem)';
const canTypeTransitions = typeof ViewTransition !== 'undefined' && 'types' in ViewTransition.prototype;

function initLeaves() {
  const root = document.documentElement;
  const sheet = document.querySelector('[data-sheet]');
  const parts = [...document.querySelectorAll('[data-leaf]')];
  const count = parts.reduce((max, el) => Math.max(max, Number(el.dataset.leaf) || 1), 1);
  const status = document.querySelector('[data-leaf-status]');
  const fit = window.matchMedia(FIT_QUERY);
  const fromHash = () => {
    if (location.hash === '#last') return count;
    const match = location.hash.match(/^#leaf-(\d+)$/);
    return match ? Math.min(count, Math.max(1, Number(match[1]))) : 1;
  };
  let current = fromHash();

  const leafed = () => fit.matches && count > 1;
  const render = () => {
    const on = leafed();
    root.classList.toggle('is-leafed', on);
    parts.forEach((el) => el.toggleAttribute('data-leaf-hidden', on && Number(el.dataset.leaf) !== current));
    if (status) status.textContent = on ? ` · leaf ${current} of ${count}` : '';
    if (sheet) sheet.scrollTop = 0;
    window.notebookFit?.();
  };
  const remember = () => {
    const url = location.pathname + location.search + (current > 1 ? `#leaf-${current}` : '');
    history.replaceState(history.state, '', url);
  };

  render();
  if (location.hash === '#last' || /^#leaf-/.test(location.hash)) remember();
  fit.addEventListener('change', render);
  // Once the real fonts are in, shrink a leaf that no longer fits; refit on resize.
  const shrinkIfNeeded = () => window.notebookFit?.(true);
  document.fonts?.addEventListener('loadingdone', shrinkIfNeeded);
  document.fonts?.ready.then(shrinkIfNeeded);
  window.addEventListener(
    'load',
    () => {
      shrinkIfNeeded();
      // Cached fonts can swap in after load without a loading event; check once more.
      setTimeout(shrinkIfNeeded, 400);
    },
    { once: true },
  );
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => window.notebookFit?.(), 120);
  });

  // Returns true when the turn stayed on this page (another leaf exists that way).
  return function turnLeaf(direction) {
    const target = current + (direction === 'next' ? 1 : -1);
    if (!leafed() || target < 1 || target > count) return false;
    const update = () => {
      current = target;
      render();
      remember();
      document.getElementById('main')?.focus({ preventScroll: true });
    };
    if (document.startViewTransition && canTypeTransitions && !reduceMotion) {
      document.startViewTransition({ update, types: [direction === 'next' ? 'forward' : 'backward'] });
    } else {
      update();
    }
    return true;
  };
}

function initPageTurns() {
  // Links shared before the site had separate pages pointed at /#section.
  if (location.pathname === '/' && OLD_SECTION_LINKS[location.hash]) {
    location.replace(OLD_SECTION_LINKS[location.hash]);
    return;
  }

  const turnLeaf = initLeaves();
  const prev = document.querySelector('[data-turn="prev"]');
  const next = document.querySelector('[data-turn="next"]');

  // Turn the next leaf if there is one, otherwise follow the link to the next page.
  next?.addEventListener('click', (e) => {
    if (turnLeaf('next')) e.preventDefault();
  });
  document.querySelector('[data-turn-ear]')?.addEventListener('click', (e) => {
    if (turnLeaf('next')) e.preventDefault();
  });
  // Turning back from a page's first leaf lands on the previous page's last leaf.
  prev?.addEventListener('click', (e) => {
    if (turnLeaf('prev')) {
      e.preventDefault();
    } else if (document.documentElement.classList.contains('is-leafed') || window.matchMedia(FIT_QUERY).matches) {
      e.preventDefault();
      location.href = prev.href.split('#')[0] + '#last';
    }
  });

  const go = (link) => link && link.click();
  document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.target.closest('input, textarea, select, [contenteditable], dialog[open]')) return;
    if (e.key === 'ArrowRight') go(next);
    else if (e.key === 'ArrowLeft') go(prev);
  });

  // Swipe sideways on touch screens to turn the page.
  const sheet = document.querySelector('[data-sheet]');
  if (!sheet) return;
  let start = null;
  sheet.addEventListener(
    'touchstart',
    (e) => {
      const t = e.touches[0];
      start = e.touches.length === 1 && !e.target.closest('input, textarea, [data-no-swipe]') ? { x: t.clientX, y: t.clientY } : null;
    },
    { passive: true },
  );
  sheet.addEventListener(
    'touchend',
    (e) => {
      if (!start) return;
      const t = e.changedTouches[0];
      const dx = t.clientX - start.x;
      const dy = t.clientY - start.y;
      start = null;
      if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.6) return;
      go(dx < 0 ? next : prev);
    },
    { passive: true },
  );
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

/* ---------- Hero: pointer parallax (desktop only) ---------- */
function initHeroPointer() {
  const hero = document.querySelector('[data-hero]');
  if (!hero) return;
  hero.querySelectorAll('[data-depth]').forEach((el) => el.style.setProperty('--depth', el.dataset.depth));
  if (reduceMotion || !finePointer) return;

  let rect = hero.getBoundingClientRect();
  let frame = 0;
  let px = 0;
  let py = 0;

  const measure = () => {
    rect = hero.getBoundingClientRect();
  };
  window.addEventListener('resize', measure, { passive: true });
  window.addEventListener('scroll', measure, { passive: true });

  const render = () => {
    frame = 0;
    const mx = ((px - rect.left) / rect.width - 0.5) * 2;
    const my = ((py - rect.top) / rect.height - 0.5) * 2;
    hero.style.setProperty('--mx', (-mx * 4).toFixed(2));
    hero.style.setProperty('--my', (-my * 3).toFixed(2));
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

initPageTurns();
initReveals();
initMenu();
initHeroPointer();
initFlip();
initTilt();
initCopy();
initLightbox();
