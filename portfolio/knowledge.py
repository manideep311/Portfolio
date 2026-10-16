"""Builds the tiny knowledge base behind the 'Ask my notebook' playground.

Everything comes from the CMS, so editing a project in the admin also updates
what the playground can answer. The browser does the retrieval (TF-IDF +
cosine similarity) — no external AI service is called.
"""

from .models import (
    Achievement,
    Certification,
    Education,
    Experience,
    Principle,
    Project,
    SiteProfile,
    SkillCategory,
    SocialLink,
)


def _date(value) -> str:
    return value.strftime("%b %Y") if value else "present"


def build_notes() -> list[dict]:
    notes: list[dict] = []
    profile = SiteProfile.load()

    if profile:
        notes.append(
            {
                "id": "about",
                "group": "about",
                "label": "who I am",
                "text": f"I'm {profile.name}, a {profile.role} ({profile.focus}) based in {profile.location}. {profile.headline} {profile.intro}",
                "keywords": "who are you introduction background summary role title engineer",
            }
        )
        links = ", ".join(f"{link.label} {link.url}" for link in SocialLink.objects.filter(is_visible=True))
        notes.append(
            {
                "id": "contact",
                "group": "contact",
                "label": "how to reach me",
                "text": f"Email me at {profile.email}. You can also find me on {links}. {profile.availability}.".strip(),
                "keywords": "contact email reach hire message linkedin github talk available availability job role open",
            }
        )
        for i, paragraph in enumerate(profile.about_paragraphs[:3]):
            notes.append(
                {
                    "id": f"story-{i}",
                    "group": "about",
                    "label": "my story",
                    "text": paragraph,
                    "keywords": "story personality style work team",
                }
            )

    for project in Project.objects.published():
        tech = ", ".join(project.tech_list)
        notes.append(
            {
                "id": f"project-{project.slug}",
                "group": "work",
                "label": project.title,
                "text": f"{project.title} ({project.year}): {project.summary} Built with {tech}.",
                "keywords": f"project built {project.note} {' '.join(project.contribution_list)}",
                "url": project.get_absolute_url(),
            }
        )

    for job in Experience.objects.filter(is_published=True):
        notes.append(
            {
                "id": f"job-{job.pk}",
                "group": "journey",
                "label": f"{job.role}",
                "text": f"{job.role} at {job.organization}, {job.location} ({_date(job.start_date)} – {_date(job.end_date)}). "
                + " ".join(job.highlight_list),
                "keywords": "experience internship work job company employment",
            }
        )

    for edu in Education.objects.all():
        status = "in progress" if edu.in_progress else f"graduated {_date(edu.end_date)}"
        notes.append(
            {
                "id": f"edu-{edu.pk}",
                "group": "journey",
                "label": f"{edu.degree}",
                "text": f"{edu.degree} in {edu.field} at {edu.institution}, {edu.location} — {status}. {edu.score}. {edu.focus}",
                "keywords": "education study studied degree college university school cgpa grades",
            }
        )

    certs = list(Certification.objects.all())
    if certs:
        notes.append(
            {
                "id": "certs",
                "group": "journey",
                "label": "certifications",
                "text": "Certifications: " + "; ".join(f"{c.name} ({c.issuer})" for c in certs) + ".",
                "keywords": "certificate certifications certified courses credentials ibm qualcomm microsoft azure",
            }
        )

    wins = list(Achievement.objects.all())
    if wins:
        notes.append(
            {
                "id": "wins",
                "group": "journey",
                "label": "achievements",
                "text": "Achievements & leadership: " + "; ".join(f"{a.title} — {a.detail}" for a in wins) + ".",
                "keywords": "achievements awards prize won leadership hackathon organised organized volunteer",
            }
        )

    for category in SkillCategory.objects.prefetch_related("skills"):
        names = ", ".join(skill.name for skill in category.skills.all())
        notes.append(
            {
                "id": f"skills-{category.pk}",
                "group": "toolkit",
                "label": category.title,
                "text": f"{category.title}: {names}. {category.builds}",
                "keywords": "skills tools stack technologies know use",
            }
        )

    for principle in Principle.objects.all():
        notes.append(
            {
                "id": f"principle-{principle.pk}",
                "group": "about",
                "label": principle.title,
                "text": f"{principle.title}: {principle.body}",
                "keywords": "approach philosophy how you work principles",
            }
        )

    return notes
