"""
The notebook's page order. Each section of the site is its own page, and the
site turns between them like a notebook: forwards to a later page, backwards
to an earlier one. Templates read this through the ``site`` context processor.
"""

from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class NotebookPage:
    key: str
    title: str
    url_name: str

    @property
    def url(self) -> str:
        return reverse(self.url_name)


PAGES = (
    NotebookPage("home", "Cover", "portfolio:home"),
    NotebookPage("work", "Work", "portfolio:project_list"),
    NotebookPage("about", "About", "portfolio:about"),
    NotebookPage("toolkit", "Toolkit", "portfolio:toolkit"),
    NotebookPage("journey", "Journey", "portfolio:journey"),
    NotebookPage("contact", "Contact", "portfolio:contact"),
)

# Views that live "inside" a page: a project case study sits within Work,
# the thank-you note within Contact.
_PARENT = {"project_detail": "work", "contact_thanks": "contact"}
_BY_URL_NAME = {page.url_name.split(":")[1]: page for page in PAGES}
_BY_KEY = {page.key: page for page in PAGES}


def page_context(url_name: str | None) -> dict:
    """Current page, its neighbours and its position, for a resolved URL name."""
    page = _BY_KEY.get(_PARENT.get(url_name, "")) or _BY_URL_NAME.get(url_name or "")
    if page is None:
        return {"notebook_pages": PAGES}
    index = PAGES.index(page)
    nested = url_name in _PARENT
    return {
        "notebook_pages": PAGES,
        "current_page": page,
        "page_number": index + 1,
        "page_count": len(PAGES),
        # Nested views turn back to their parent page rather than skipping past it.
        "prev_page": page if nested else (PAGES[index - 1] if index > 0 else None),
        "next_page": PAGES[index + 1] if index + 1 < len(PAGES) else None,
        # Ordering used to decide whether a navigation turns forwards or backwards.
        "page_order": f"{index}.5" if nested else str(index),
    }
