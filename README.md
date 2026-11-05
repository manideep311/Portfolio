# Manideep Chittimodu — Field Notebook

[![CI](https://github.com/manideep311/Portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/manideep311/Portfolio/actions/workflows/ci.yml)

A scrapbook-style portfolio for a Gen AI / ML engineer, run from a private Django Admin CMS.

- **Live site:** <https://manideep311.pythonanywhere.com>
- **Admin:** `/admin/` is private; login required, no public sign-up.

Built with **Django 5.2**, **Tailwind CSS v4** and a little vanilla JavaScript.

## Highlights

- Notebook-style navigation: separate pages with a page-turn transition, sized to fit the screen.
- Django Admin CMS with a draft/published workflow and inline screenshot uploads per project.
- Upload validation by content sniffing (not just file extensions), with images re-encoded to WebP.
- Nonce-based Content Security Policy on every public page.
- 89 automated tests, run by GitHub Actions on every push and pull request.
- Lighthouse 100 on desktop and 97 on mobile at the last audit.
- axe-core: 0 violations on every page and leaf at 1440×900 and 390×844 (checked 1 November 2026).

Everything on the public site — profile, projects, screenshots, skills,
experience, education, certifications, links, the résumé PDF — is edited in the
admin. No code changes needed.

```
Public site   /              cover
              /work/         every published project, featured ones first
              /work/<slug>/  case study + screenshot gallery (published only)
              /about/  /toolkit/  /journey/  /contact/
CMS           /admin/        login required, no public sign-up
```

Each section is its own page, and the site turns between them like a notebook: the
page lifts from the spiral binding and flips over (cross-document View Transitions;
browsers without support just load the next page). Dense pages are split into
**leaves** that turn one at a time, so on a laptop or desktop screen nothing scrolls.
Arrow keys, swipes, the pager and the dog-eared corner all turn the page. On phones
the leaves stack and the page scrolls normally.

---

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Django 5.2 LTS | Admin, auth, permissions, CSRF and forms for free; supported to April 2028 |
| Frontend | Django templates + Tailwind CSS v4 + a hand-written CSS layer | Tailwind for layout and spacing, custom CSS for the paper, tape, polaroids and doodles |
| Interactions | CSS animations + a few KB of vanilla JS (ES modules) | Reveals, parallax, the polaroid flip and the screenshot lightbox; no framework |
| Content | SQLite (the live site on PythonAnywhere too); PostgreSQL works via `DATABASE_URL` if you move | Managed in Django Admin |
| Media | Local `media/` folder, served by PythonAnywhere; S3-compatible storage is optional via `AWS_*` | PythonAnywhere's disk persists between deploys |
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
python manage.py createcachetable    # the table the contact-form rate limit uses
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

The 89 tests cover models, upload validation (type, size and content
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
4. Under **Publishing**, set *Status = Published* and tick *Shown first on the Work page* if it should lead. Leave *Published at* empty to publish now, or set a future date to schedule it.
5. Save. Use **View on site** or the *Public?* column to open it.

**Day-to-day**
- *Status*, *Featured* and *Display order* are editable straight from the project list. Bulk actions: publish, back to draft, show first on the Work page, stop showing first.
- Drafts and scheduled projects return **404** to visitors. Signed-in staff with "view project" permission see a yellow *Draft preview* banner.
- **Profile** is a single record: name, headline, intro, about story, availability stamp (leave empty to hide it), portrait, résumé PDF, email, and whether to show your phone number.
- Skills (grouped, each group with its own visual style), work experience (with links), education, certifications, achievements, working principles (shown in About next to the work-loop sketch) and social links each have their own sections.

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
| `DATABASE_URL` | Optional PostgreSQL URL. Empty = SQLite (what the live site uses) |
| `AWS_*` | Optional S3 / R2 media storage. Empty bucket = local `media/` (what the live site uses) |
| `DJANGO_ADMIN_URL` | Move the admin away from `/admin/` |
| `CONTACT_NOTIFY_EMAIL` + `EMAIL_*` | Optional email when a new message arrives |
| `CLIENT_IP_HEADER` | Where the contact rate limit finds the visitor's IP: empty = `REMOTE_ADDR`, `X-Real-IP` on PythonAnywhere (the setup script sets it), `X-Forwarded-For` behind other proxies (only its rightmost entry, which your proxy added, is used) |

**Security in place:** Django auth and permissions on every admin view; no
registration route; CSRF on all forms; a nonce-based Content-Security-Policy on
public pages; `X-Frame-Options: DENY`, `nosniff`, a strict referrer policy and
COOP; HTTPS redirect, secure cookies and HSTS when `DEBUG` is off; a honeypot
plus per-IP rate limiting on the contact form; content-sniffed uploads with
random names; a 12-character minimum password length.

---

## Deploy

### Free: PythonAnywhere

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
It pulls, installs, migrates, creates the rate-limit cache table if it's
missing, collects static files and reloads the site. Because the script pulls
a new copy of itself, run `git -C ~/Portfolio pull` first when an update
changes the script.

**Backups:** download `db.sqlite3` and the `media/` folder from the Files tab
now and then. Settings live in `~/Portfolio/.env`; press Reload after editing.
On the free plan outgoing email is restricted, so new contact messages may not
be emailed to you — they are always saved in the admin.

### Moving to another host

The live site runs on PythonAnywhere with SQLite and local media. The settings
also support other hosts: set `DATABASE_URL` for PostgreSQL, the `AWS_*`
variables for S3-compatible media storage (needed wherever the filesystem is
wiped on each deploy), and `CLIENT_IP_HEADER` for that host's proxy. Run
`migrate`, `createcachetable` and `collectstatic` on every deploy.

**Database migrations:** for model changes locally, run
`python manage.py makemigrations && python manage.py migrate`, then commit the
new migration files. The PythonAnywhere update script applies them.

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
  views.py, forms.py, sitemaps.py, urls.py
  templatetags/notebook.py   doodles, safe text formatting, project visuals, JSON-LD
  templates/portfolio/  pages, sections (partials/) and hand-drawn project sketches (art/)
  management/commands/seed_portfolio.py
  tests/                89 tests
templates/              base layout, 404/500, admin branding
assets/css/             Tailwind entry + scrapbook component CSS (source)
static/                 compiled CSS, JS, fonts (self-hosted), textures, icons
seed/                   portrait (and your git-ignored résumé PDF) used by seed_portfolio
deploy/                 PythonAnywhere setup and update scripts
```

## Credits

Self-hosted fonts: Fraunces, Instrument Sans and Kalam (SIL Open Font
License) and Special Elite (Apache License 2.0). Licences are in
`static/fonts/licenses/`.
