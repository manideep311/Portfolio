# Manideep Chittimodu — Field Notebook

A scrapbook-style portfolio for a Gen AI / ML engineer, built with **Django**, a
**private Django Admin CMS**, **Tailwind CSS** and a little vanilla JavaScript.

Everything on the public site — profile, projects, screenshots, skills,
experience, education, certifications, links, the résumé PDF — is edited in the
admin. No code changes needed.

```
Public site   /            hero · project gallery · about · toolkit · journey · playground · contact
              /work/       every published project
              /work/<slug>/ case study + screenshot gallery (published only)
CMS           /admin/      login required, no public sign-up
```

---

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Django 5.2 LTS | Admin, auth, permissions, CSRF and forms for free; supported to April 2028 |
| Frontend | Django templates + Tailwind CSS v4 + a hand-written CSS layer | Tailwind for layout and spacing, custom CSS for the paper, tape, polaroids and doodles |
| Interactions | CSS animations + ~10 KB of vanilla JS (ES modules) | The playground engine loads lazily, only when it scrolls near |
| Content | Database (SQLite locally, PostgreSQL in production via `DATABASE_URL`) | Managed in Django Admin |
| Media | Local `media/` in development, S3-compatible object storage in production | Uploads survive deploys |
| Static files | WhiteNoise, hashed and Brotli/gzip pre-compressed | Cached forever, no extra server needed |
| Contact | Email-only form stored privately in the database (+ optional email notification) | Messages are visible only to authorised staff |

---

## Run it locally

Requirements: Python 3.12+ (3.13 tested). Node.js is only needed if you change templates or CSS.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # DJANGO_DEBUG=1 is fine locally
python manage.py migrate             # creates db.sqlite3 and the staff groups
python manage.py seed_portfolio      # loads the résumé content (only if the DB is empty)
python manage.py createsuperuser     # your CMS login
python manage.py runserver
```

- Site: http://127.0.0.1:8000
- CMS: http://127.0.0.1:8000/admin/

### Rebuilding the CSS

The compiled stylesheet (`static/css/app.css`) is committed so the server never
needs Node. After changing templates or anything in `assets/css/`:

```bash
npm install
npm run build:css        # or: npm run watch:css while you work
```

### Tests

```bash
DJANGO_DEBUG=1 python manage.py test portfolio
```

The 72 tests cover models, upload validation (type, size and content
sniffing), image optimisation, file cleanup, publish and visibility rules,
draft previews, permissions and roles, CSRF, the honeypot, rate limiting,
email notifications, the portrait film look, the sitemap and the seed command. They also run the full
admin journey: sign in → create project → upload several screenshots →
publish → see it on the public site.

---

## Using the CMS

Sign in at `/admin/` (or your `DJANGO_ADMIN_URL`).

**Add a project**
1. *Projects → Add project.* Fill in the title (the slug fills itself), the summary, the story, your contribution, outcomes and technologies (comma-separated, in display order).
2. Under **Screenshots**, choose an image, add alt text (required) and an optional caption. "Add another Screenshot" adds more rows. Lower *display order* comes first.
3. Optionally upload a **featured image** (with alt text). Without one, the card shows the hand-drawn sketch you pick in *Fallback sketch*.
4. Under **Publishing**, set *Status = Published* and tick *Featured on homepage*. Leave *Published at* empty to publish now, or set a future date to schedule it.
5. Save. Use **View on site** or the *Public?* column to open it.

**Day-to-day**
- *Status*, *Featured* and *Display order* are editable straight from the project list. Bulk actions: publish, back to draft, feature, remove from homepage.
- Drafts and scheduled projects return **404** to visitors. Signed-in staff with "view project" permission see a yellow *Draft preview* banner.
- **Profile** is a single record: name, headline, intro, about story, availability stamp (leave empty to hide it), portrait, résumé PDF, email, and whether to show your phone number.
- Hero stats live in *Field notes*. Skills (grouped, each group with its own visual style), work experience (with links), education, certifications, achievements, principles and social links each have their own sections.

**Uploads**
- Images: JPEG, PNG or WebP only, verified by reading the file, not trusting its name. SVG, GIF and disguised files are rejected. Max `MAX_IMAGE_UPLOAD_MB` (default 8 MB). Every upload is re-encoded to WebP, EXIF-rotated, capped at `IMAGE_MAX_EDGE` (default 2000 px) and given a random filename. Width and height are stored so pages never shift.
- Portrait: by default, new portrait uploads get the **notebook film look** (warm instant-print tones, film grain, the site's paper texture and a soft vignette) so any photo sits naturally on the page. Untick *Notebook film look* in the profile before uploading to keep the photo as shot. A square head-and-shoulders crop reads best in the polaroid. Without a portrait, the polaroid shows a hand-lettered monogram.
- Résumé: PDF only (checked by its `%PDF-` signature). Max `MAX_DOCUMENT_UPLOAD_MB` (default 10 MB).
- Replacing or deleting a file removes the old one from storage.

**Contact messages and roles**

Two groups are created automatically on every `migrate`:

| Group | Can |
| --- | --- |
| *Portfolio editors* | Manage all public content. **Cannot** see contact messages. |
| *Inbox readers* | Read contact messages and mark them handled. Cannot edit content. |

Superusers can do everything. Messages can't be created or forged from the
admin. Opening one marks it read, and each message has a reply-by-email link.

---

## Configuration

All settings come from environment variables (`.env` locally). See
[`.env.example`](.env.example) for the full list. The important ones:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required when `DJANGO_DEBUG` is off. Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `1` locally only. Off = HTTPS redirect, secure cookies, HSTS |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Your domain(s) |
| `SITE_URL` | Public URL for canonical links, Open Graph and the sitemap |
| `DATABASE_URL` | PostgreSQL URL in production. Empty = SQLite |
| `AWS_*` | S3 / R2 media storage. Empty bucket = local `media/` |
| `DJANGO_ADMIN_URL` | Move the admin away from `/admin/` |
| `CONTACT_NOTIFY_EMAIL` + `EMAIL_*` | Optional email when a new message arrives |
| `TRUST_X_FORWARDED_FOR` | `1` behind a platform proxy so rate limiting sees real IPs |

**Security in place:** Django auth and permissions on every admin view; no
registration route; CSRF on all forms; a nonce-based Content-Security-Policy on
public pages; `X-Frame-Options: DENY`, `nosniff`, a strict referrer policy and
COOP; HTTPS redirect, secure cookies and HSTS when `DEBUG` is off; a honeypot
plus per-IP rate limiting on the contact form; content-sniffed uploads with
random names; a 12-character minimum password length.

---

## Deploy for free (PythonAnywhere)

PythonAnywhere's free plan runs the whole site — app, SQLite database and
uploaded images on its disk — with no card and no sleeping. Your address is
`<username>.pythonanywhere.com` (custom domains need a paid plan), and you
click **Run until 3 months from today** on the Web tab every three months.

1. Create a free **Beginner** account at pythonanywhere.com.
2. Open **Consoles → Bash** and run:
   ```bash
   git clone https://github.com/manideep311/Portfolio.git
   bash ~/Portfolio/deploy/pythonanywhere_setup.sh
   ```
   This creates the virtualenv, installs `requirements-pythonanywhere.txt`,
   writes `.env` with a fresh secret key, migrates, loads the résumé content and
   collects static files. It finishes by printing your exact paths.
3. Create your login with the `createsuperuser` command the script prints.
4. **Web → Add a new web app → Manual configuration**, same Python version. Fill
   in Source code, Working directory, Virtualenv, the two Static files rows
   (`/static/` and `/media/`) and turn on **Force HTTPS**, as printed.
5. Replace the WSGI configuration file with the three lines the script printed,
   save, and press **Reload**.

**Updating later:** push to GitHub, then in a Bash console:
```bash
bash ~/Portfolio/deploy/pythonanywhere_update.sh
```
It pulls, installs, migrates, collects static files and reloads the site.

**Backups:** download `db.sqlite3` and the `media/` folder from the Files tab
now and then. Settings live in `~/Portfolio/.env`; press Reload after editing.
On the free plan outgoing email is restricted, so new contact messages may not
be emailed to you — they are always saved in the admin.

## Deploy (Render + PostgreSQL + Cloudflare R2)

Render's filesystem is wiped on every deploy, so uploads must go to object
storage. Cloudflare R2 has no egress fees and an S3-compatible API.

**1. Media bucket (R2)**
1. Cloudflare dashboard → R2 → *Create bucket* (e.g. `manideep-portfolio`).
2. *Settings → Public access*: connect a custom domain (e.g. `media.yourdomain.com`) or enable the `r2.dev` URL.
3. *R2 → Manage API tokens → Create token* with Object Read & Write on that bucket. Note the access key ID, the secret, and the S3 endpoint `https://<account-id>.r2.cloudflarestorage.com`.

**2. Render**
1. Push this folder to a GitHub repository.
2. Render → *New → Blueprint* → select the repo. `render.yaml` creates the PostgreSQL database and the web service.
3. When prompted, fill in `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_CUSTOM_DOMAIN` (the public domain from step 1) and `SITE_URL` (your final URL). Configure R2 **before** the first deploy, so the seeded résumé PDF lands in the bucket.
4. Deploy. `build.sh` installs dependencies, runs `collectstatic` and `migrate`, and (because `SEED_ON_DEPLOY=1`) loads your résumé content once. Then set `SEED_ON_DEPLOY=0`.
5. Create your login: Render service → *Shell* → `python manage.py createsuperuser`. If Shell isn't available on your plan, run the same command locally with `DATABASE_URL` set to the Render database's *External* URL.
6. Custom domain: add it in Render, then add it to `DJANGO_ALLOWED_HOSTS` (e.g. `.onrender.com,yourdomain.com`), `DJANGO_CSRF_TRUSTED_ORIGINS` (`https://yourdomain.com`) and `SITE_URL`.

**Database migrations** run on every deploy (`build.sh`). For model changes
locally: `python manage.py makemigrations && python manage.py migrate`, then
commit the new migration files.

**Plans:** Render's free web instances sleep when idle, which makes the first
visit slow, and free databases expire. For a portfolio you send to recruiters,
use the smallest paid web instance and database.

**Other hosts**
- *Railway / Heroku-style:* `Procfile` runs migrations on release. Attach PostgreSQL and set the same env vars.
- *Fly.io / any container host:* the `Dockerfile` builds the CSS, installs Python deps, collects static files and runs migrations on start. (It couldn't be built in the environment where this project was made, so give it one local `docker build .` first.)
- *A single VPS with a persistent disk:* object storage is optional. Set `SERVE_MEDIA=1` and point `MEDIA_ROOT` at the persistent volume.

---

## Project structure

```
config/                 settings (env-driven), urls, wsgi
portfolio/
  models.py             Profile, Project, ProjectImage, skills, experience, education, …, ContactMessage
  admin.py              CMS: inlines, previews, actions, singleton profile, private inbox
  validators.py         upload type / size / content checks
  images.py             WebP re-encoding + resizing
  film.py               the portrait "notebook film" treatment (Pillow only)
  signals.py            removes replaced or deleted files from storage
  permissions.py        "Portfolio editors" and "Inbox readers" groups
  middleware.py         nonce-based Content-Security-Policy
  knowledge.py          builds the playground's notes from the CMS
  views.py, forms.py, sitemaps.py, urls.py
  templatetags/notebook.py   doodles, safe text formatting, project visuals, JSON-LD
  templates/portfolio/  pages, sections (partials/) and hand-drawn project sketches (art/)
  management/commands/seed_portfolio.py
  tests/                72 tests
templates/              base layout, 404/500, admin branding
assets/css/             Tailwind entry + scrapbook component CSS (source)
static/                 compiled CSS, JS, fonts (self-hosted), textures, icons
seed/                   portrait (and your git-ignored résumé PDF) used by seed_portfolio
deploy/                 PythonAnywhere setup and update scripts
```

## Content still needed from you

- **Real project screenshots.** Each project uses a labelled hand-drawn diagram (never presented as a screenshot). Add real screenshots per project, and a featured image if you like.
- **Source links** for Vastra, NextCinema and the Uniform Detection project. Only the Falcon 9 repository was linked in the résumé.
- **Measured outcomes** (accuracy, latency, user numbers). None were in the résumé, so none are shown.
- **Your final domain.** Set it in `SITE_URL` for canonical and Open Graph URLs.
- The phone number is stored but hidden. Tick *Show phone* in the profile if you want it public.

## Credits

Self-hosted fonts: Fraunces, Instrument Sans and Kalam (SIL Open Font
License) and Special Elite (Apache License 2.0). Licences are in
`static/fonts/licenses/`.
