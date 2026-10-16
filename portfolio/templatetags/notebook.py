import json

from django import template
from django.templatetags.static import static
from django.utils.html import conditional_escape, format_html, format_html_join
from django.utils.safestring import mark_safe

register = template.Library()

# Hand-drawn ink marks. pathLength=1 lets CSS draw any stroke with one rule.
DOODLES = {
    "arrow-curve": ("0 0 130 84", ["M6 70c18 6 46 4 64-10s30-34 46-48", "M98 9.5 117 10l-5 18"]),
    "arrow-loop": (
        "0 0 170 96",
        ["M7 78c22 8 46 2 56-14 9-15-6-28-14-16-9 14 16 26 44 16 26-9 44-26 60-48", "M136 14.5l18.5 1.5-4 17.5"],
    ),
    "arrow-down": ("0 0 64 118", ["M33 6c-9 22 9 44-3 70-3 7-2 18 1 28", "M18 90l13.5 16L44 89"]),
    "arrow-left": ("0 0 140 70", ["M132 14C104 6 76 12 56 30S24 56 10 58", "M24 44 9.5 58.5 28 64"]),
    "arrow-swoop": ("0 0 220 120", ["M8 20c40-14 92-6 120 26s54 52 80 56", "M188 92l21 10-16 15"]),
    "underline": ("0 0 260 22", ["M4 14c40-6 96-9 150-7 38 2 70 3 102-3"]),
    "underline-double": ("0 0 260 30", ["M4 11c46-5 108-8 164-5 32 2 58 2 88-2", "M22 22c42-4 104-5 170-2"]),
    "scribble": ("0 0 200 24", ["M4 16c10-10 18 6 28-2s16-10 26 0 18 8 28-2 18-8 28 2 18 6 28-2 16-8 26 0 14 4 26-4"]),
    "star": ("0 0 44 44", ["M22 4l4.6 12.6 13.2.4-10.4 8.2 3.9 12.8L22.2 30.4 11 38.4l4-12.9L4.4 17.2l13.3-.6z"]),
    "sparkle": ("0 0 34 34", ["M17 3c1 8 3 12 14 14-10 2-13 5-14 14-1-9-4-12-14-14 10-2 13-6 14-14z"]),
    "spiral": (
        "0 0 44 44",
        ["M22 22c2-2 5 0 4 3-1 4-8 4-9-1-1-6 6-10 12-7 7 4 6 14-2 17-9 3-17-3-16-12 1-10 11-15 20-12"],
    ),
    "check": ("0 0 40 34", ["M4 17c4 2 8 7 11 13 6-12 13-21 22-27"]),
    "circle": ("0 0 220 90", ["M36 14c44-12 140-10 170 14 18 18-14 48-92 52-62 3-104-14-104-36 0-18 34-32 104-36"]),
    "asterisk": ("0 0 30 30", ["M15 3v24M4.5 9l21 12M25.5 9l-21 12"]),
    "burst": ("0 0 48 48", ["M24 4v9M24 35v9M4 24h9M35 24h9M10 10l6 6M32 32l6 6M38 10l-6 6M16 32l-6 6"]),
    "heart": (
        "0 0 40 36",
        ["M20 32C8 24 3 17 4 11c1-6 8-9 13-5 2 1 3 3 3 5 0-2 1-4 3-5 5-4 12-1 13 5 1 6-4 13-16 21z"],
    ),
}


# Underlines stretch to whatever they sit under (near-horizontal strokes stay even).
STRETCHY = {"underline", "underline-double", "scribble"}


@register.simple_tag
def doodle(name, cls="", draw=False, weight=2.6, fill=False, style=""):
    """Inline, decorative hand-drawn SVG: {% doodle "arrow-curve" cls="..." draw=True %}"""
    view_box, paths = DOODLES[name]
    stretch = name in STRETCHY
    extra = ' fill="currentColor"' if fill else ""
    # `extra` only ever holds the constant attribute strings above.
    path_html = format_html_join("", '<path d="{}" pathLength="1"{}></path>', ((d, mark_safe(extra)) for d in paths))  # noqa: S308
    classes = " ".join(c for c in ["doodle", cls, "draw" if draw else ""] if c)
    style_attr = format_html(' style="{}"', style) if style else ""
    aspect = mark_safe(' preserveAspectRatio="none"') if stretch else ""  # noqa: S308 (constant)
    return format_html(
        '<svg class="{}" viewBox="{}"{} fill="none" stroke="currentColor" stroke-width="{}" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true" focusable="false"{}>{}</svg>',
        classes,
        view_box,
        aspect,
        weight,
        style_attr,
        path_html,
    )


def _paragraph_html(lines: list[str]) -> str:
    return "<p>" + "<br>".join(conditional_escape(line) for line in lines) + "</p>"


def _list_html(items: list[str]) -> str:
    lis = "".join(f"<li>{conditional_escape(item)}</li>" for item in items)
    return f'<ul class="bullets" role="list">{lis}</ul>'


@register.filter(is_safe=True)
def simple_format(text):
    """Paragraphs separated by blank lines; lines starting with '- ' become lists. HTML is escaped."""
    if not text:
        return ""
    html_parts: list[str] = []
    for block in str(text).replace("\r\n", "\n").split("\n\n"):
        paragraph: list[str] = []
        items: list[str] = []
        for line in block.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("- ", "• ", "* ")):
                if paragraph:
                    html_parts.append(_paragraph_html(paragraph))
                    paragraph = []
                items.append(stripped[2:].strip())
            else:
                if items:
                    html_parts.append(_list_html(items))
                    items = []
                paragraph.append(stripped)
        if paragraph:
            html_parts.append(_paragraph_html(paragraph))
        if items:
            html_parts.append(_list_html(items))
    # Every fragment above was built from conditionally escaped text.
    return mark_safe("".join(html_parts))  # noqa: S308


@register.inclusion_tag("portfolio/partials/project_visual.html")
def project_visual(project, uid="p", eager=False, sizes="(min-width: 64rem) 40vw, 92vw"):
    """The featured image if one was uploaded, otherwise the project's hand-drawn sketch."""
    return {"project": project, "uid": f"{uid}-{project.pk}", "eager": eager, "sizes": sizes}


@register.simple_tag
def person_jsonld(profile, social_links, site_url, nonce=""):
    if not profile:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": profile.name,
        "jobTitle": profile.role,
        "description": profile.seo_description or profile.headline,
        "email": f"mailto:{profile.email}",
        "url": site_url + "/",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": profile.location.split(",")[0] if profile.location else "",
        },
        "sameAs": [link.url for link in social_links],
    }
    if profile.portrait:
        data["image"] = (
            profile.portrait.url if profile.portrait.url.startswith("http") else site_url + profile.portrait.url
        )
    payload = (
        json.dumps(data, ensure_ascii=False).replace("<", "\\u003C").replace(">", "\\u003E").replace("&", "\\u0026")
    )
    # json.dumps output with <, > and & escaped cannot break out of the script element.
    return format_html('<script type="application/ld+json" nonce="{}">{}</script>', nonce, mark_safe(payload))  # noqa: S308


@register.filter
def initials(value):
    return "".join(part[0] for part in str(value).split()[:2]).upper()


@register.simple_tag
def absolute_static(site_url, path):
    url = static(path)
    return url if url.startswith("http") else f"{site_url}{url}"


@register.filter
def month_year(value):
    return value.strftime("%b %Y") if value else "Present"


@register.filter
def year(value):
    return value.strftime("%Y") if value else "now"
