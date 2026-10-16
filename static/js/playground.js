// "Ask my notebook": a tiny TF-IDF retriever over notes rendered by Django
// from the CMS. Runs fully in the browser — no network calls, no LLM.

const STOP = new Set(
  'a an and are as at be but by can could did do does for from had has have he her his how i if in into is it its me my of on or our she so than that the their them then there these they this to was we were what when where which who why will with you your about any tell know some get got please'.split(
    ' ',
  ),
);

// Query expansion: a hand-written synonym list stands in for embeddings.
const SYNONYMS = {
  hire: ['available', 'role', 'contact', 'open'],
  hiring: ['available', 'role', 'open'],
  job: ['experience', 'role', 'internship'],
  work: ['project', 'experience', 'built'],
  study: ['education', 'degree'],
  studied: ['education', 'degree'],
  college: ['education', 'institution'],
  university: ['education', 'institution'],
  school: ['education'],
  degree: ['education'],
  grade: ['cgpa'],
  gpa: ['cgpa'],
  rag: ['retrieval', 'embedding', 'semantic'],
  chatbot: ['assistant', 'llm'],
  ai: ['llm', 'generative'],
  genai: ['generative', 'llm'],
  llm: ['language', 'model', 'generation'],
  vision: ['cnn', 'opencv', 'face', 'computer'],
  cv: ['vision', 'cnn'],
  camera: ['vision', 'face'],
  face: ['deepface', 'recognition'],
  deploy: ['deployment', 'deployed'],
  certificate: ['certification', 'certified'],
  award: ['prize', 'achievement'],
  won: ['prize'],
  win: ['prize'],
  recommend: ['recommendation', 'similarity'],
  movie: ['film', 'cinema', 'tmdb'],
  rocket: ['falcon', 'spacex'],
  spacex: ['falcon'],
  email: ['contact', 'mail'],
  reach: ['contact', 'email'],
  skill: ['tool', 'stack'],
  language: ['python', 'javascript', 'typescript'],
  math: ['mathematic', 'linear', 'probability', 'statistic'],
  cloud: ['aws', 'gcp', 'azure'],
  internship: ['intern', 'experience'],
  leadership: ['organised', 'representative', 'coordinator'],
};

function stem(word) {
  if (word.length > 5 && word.endsWith('ing')) return word.slice(0, -3);
  if (word.length > 4 && word.endsWith('ies')) return `${word.slice(0, -3)}y`;
  if (word.length > 4 && word.endsWith('ed')) return word.slice(0, -2);
  if (word.length > 3 && word.endsWith('s') && !word.endsWith('ss')) return word.slice(0, -1);
  return word;
}

function tokenize(text) {
  return (text.toLowerCase().normalize('NFKD').match(/[a-z0-9+#]+/g) || [])
    .filter((t) => t.length > 1 && !STOP.has(t))
    .map(stem);
}

function buildIndex(notes) {
  const docs = notes.map((note) => tokenize(`${note.label} ${note.text} ${note.keywords || ''}`));
  const df = new Map();
  docs.forEach((tokens) => new Set(tokens).forEach((t) => df.set(t, (df.get(t) || 0) + 1)));
  const n = docs.length;
  const idf = (t) => Math.log((n + 1) / ((df.get(t) || 0) + 1)) + 1;

  const vectors = docs.map((tokens) => {
    const tf = new Map();
    tokens.forEach((t) => tf.set(t, (tf.get(t) || 0) + 1));
    const vec = new Map();
    let norm = 0;
    tf.forEach((count, t) => {
      const w = (count / tokens.length) * idf(t);
      vec.set(t, w);
      norm += w * w;
    });
    return { vec, norm: Math.sqrt(norm) || 1 };
  });
  return { vectors, idf };
}

function search(index, question) {
  const base = tokenize(question);
  const weights = new Map();
  base.forEach((t) => {
    weights.set(t, (weights.get(t) || 0) + 1);
    (SYNONYMS[t] || []).forEach((s) => {
      const st = stem(s);
      weights.set(st, (weights.get(st) || 0) + 0.6);
    });
  });
  const q = new Map();
  let qNorm = 0;
  weights.forEach((w, t) => {
    const v = w * index.idf(t);
    q.set(t, v);
    qNorm += v * v;
  });
  qNorm = Math.sqrt(qNorm) || 1;

  return index.vectors
    .map(({ vec, norm }, i) => {
      let dot = 0;
      q.forEach((v, t) => {
        const d = vec.get(t);
        if (d) dot += v * d;
      });
      return { i, score: dot / (norm * qNorm) };
    })
    .sort((a, b) => b.score - a.score);
}

/* ---------- The sketch map ---------- */
const GROUPS = {
  about: { x: 92, y: 88, label: 'about me' },
  work: { x: 322, y: 92, label: 'projects' },
  toolkit: { x: 100, y: 240, label: 'toolkit' },
  journey: { x: 318, y: 238, label: 'journey' },
  contact: { x: 210, y: 168, label: 'contact' },
};
const SVG_NS = 'http://www.w3.org/2000/svg';

function el(name, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (text) node.textContent = text;
  return node;
}

function layout(notes) {
  const counters = {};
  return notes.map((note) => {
    const g = GROUPS[note.group] || GROUPS.about;
    const i = (counters[note.group] = (counters[note.group] ?? -1) + 1);
    const r = 15 * Math.sqrt(i + 0.6);
    const a = i * 2.39996 + 0.6;
    return { x: g.x + Math.cos(a) * r, y: g.y + Math.sin(a) * r * 0.8 };
  });
}

/* ---------- Mount ---------- */
export function mount(root) {
  const data = document.getElementById('notebook-notes');
  const notes = data ? JSON.parse(data.textContent || '[]') : [];
  if (!notes.length) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const index = buildIndex(notes);
  const positions = layout(notes);
  const log = root.querySelector('[data-pg-log]');
  const live = root.querySelector('[data-pg-live]');
  const form = root.querySelector('[data-pg-form]');
  const input = root.querySelector('[data-pg-input]');
  const svg = root.querySelector('[data-pg-map]');

  // Draw the static map once.
  const linkLayer = el('g');
  const dotLayer = el('g');
  const labelLayer = el('g');
  Object.values(GROUPS).forEach((g) => {
    labelLayer.appendChild(el('text', { x: g.x, y: g.y - 38, 'text-anchor': 'middle', class: 'pg-group' }, g.label));
  });
  const dots = positions.map((p) => {
    const c = el('circle', { cx: p.x.toFixed(1), cy: p.y.toFixed(1), r: 4.5, class: 'pg-dot' });
    dotLayer.appendChild(c);
    return c;
  });
  svg.append(linkLayer, dotLayer, labelLayer);
  const hitLabels = el('g');
  svg.appendChild(hitLabels);

  const addLine = (cls, text, html) => {
    const p = document.createElement('p');
    p.className = `pg__line ${cls}`;
    if (html) p.append(...html);
    else p.textContent = text;
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
    return p;
  };

  const typeInto = (node, text) =>
    new Promise((resolve) => {
      if (reduceMotion) {
        node.textContent = text;
        resolve();
        return;
      }
      const step = Math.max(1, Math.ceil(text.length / 70));
      let i = 0;
      const tick = () => {
        i = Math.min(text.length, i + step);
        node.textContent = text.slice(0, i);
        log.scrollTop = log.scrollHeight;
        if (i < text.length) requestAnimationFrame(tick);
        else resolve();
      };
      tick();
    });

  const drawResults = (top) => {
    linkLayer.replaceChildren();
    hitLabels.replaceChildren();
    dots.forEach((d) => {
      d.classList.remove('is-hit');
      d.setAttribute('r', 4.5);
    });
    if (!top.length) return;
    const total = top.reduce((s, r) => s + r.score, 0) || 1;
    const qx = top.reduce((s, r) => s + positions[r.i].x * r.score, 0) / total + 6;
    const qy = top.reduce((s, r) => s + positions[r.i].y * r.score, 0) / total - 10;

    top.forEach((r, rank) => {
      const p = positions[r.i];
      const line = el('path', {
        d: `M${qx.toFixed(1)} ${qy.toFixed(1)} Q${((qx + p.x) / 2 + 10).toFixed(1)} ${((qy + p.y) / 2 - 12).toFixed(1)} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`,
        pathLength: 1,
        class: 'pg-link',
        'stroke-width': (1.2 + r.score * 5).toFixed(2),
        style: `animation-delay:${rank * 120}ms`,
      });
      linkLayer.appendChild(line);
      dots[r.i].classList.add('is-hit');
      dots[r.i].setAttribute('r', 7 - rank);
      hitLabels.appendChild(
        el('text', { x: (p.x + 9).toFixed(1), y: (p.y + 4).toFixed(1), class: 'pg-label' }, `${notes[r.i].label} · ${r.score.toFixed(2)}`),
      );
    });
    hitLabels.appendChild(el('path', { d: starPath(qx, qy, 9), class: 'pg-query' }));
  };

  const ask = async (question) => {
    question = question.trim().slice(0, 160);
    if (!question) return;
    addLine('pg__line--q', `? ${question}`);
    const results = search(index, question);
    const top = results.filter((r) => r.score > 0.04).slice(0, 3);
    drawResults(top);

    if (!top.length) {
      const msg = "I couldn't find that in my notes. Try projects, skills, education, certifications or how to reach me.";
      const line = addLine('pg__line--a', '');
      if (live) live.textContent = msg;
      await typeInto(line, `› ${msg}`);
      return;
    }

    const best = notes[top[0].i];
    if (live) live.textContent = `${best.text} Best match: ${best.label}, similarity ${top[0].score.toFixed(2)}.`;
    const line = addLine('pg__line--a', '');
    line.setAttribute('aria-hidden', 'true');
    await typeInto(line, `› ${best.text}`);
    if (best.url) {
      const a = document.createElement('a');
      a.href = best.url;
      a.textContent = `open “${best.label}” →`;
      addLine('pg__line--sys', '', [a]);
    }

    const scores = document.createElement('div');
    scores.className = 'pg__scores';
    scores.setAttribute('aria-hidden', 'true');
    top.forEach((r) => {
      const row = document.createElement('div');
      row.className = 'pg__score';
      const label = document.createElement('span');
      label.className = 'pg__score-label';
      label.textContent = notes[r.i].label;
      const bar = document.createElement('span');
      bar.className = 'pg__bar-fill';
      const value = document.createElement('span');
      value.textContent = r.score.toFixed(2);
      row.append(label, bar, value);
      scores.appendChild(row);
      requestAnimationFrame(() => bar.style.setProperty('--s', Math.min(1, r.score / top[0].score).toFixed(3)));
    });
    log.appendChild(scores);
    log.scrollTop = log.scrollHeight;
  };

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    ask(input.value);
    input.value = '';
  });
  root.querySelectorAll('[data-pg-ask]').forEach((chip) =>
    chip.addEventListener('click', () => {
      ask(chip.textContent || '');
    }),
  );
}

function starPath(cx, cy, r) {
  const pts = [];
  for (let i = 0; i < 10; i += 1) {
    const rad = i % 2 ? r * 0.45 : r;
    const a = (Math.PI / 5) * i - Math.PI / 2;
    pts.push(`${(cx + Math.cos(a) * rad).toFixed(1)} ${(cy + Math.sin(a) * rad).toFixed(1)}`);
  }
  return `M${pts.join('L')}Z`;
}
