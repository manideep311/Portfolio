"""Load Manideep's résumé content into the CMS.

    python manage.py seed_portfolio           # only if the database is empty
    python manage.py seed_portfolio --reset   # replace all public content

Contact messages and user accounts are never touched. After seeding, every
word on the site is editable in the admin.
"""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from portfolio.models import (
    Achievement,
    Certification,
    Education,
    Experience,
    ExperienceLink,
    FieldNote,
    Principle,
    Project,
    SiteProfile,
    Skill,
    SkillCategory,
    SocialLink,
)

# Optional and git-ignored: drop your current résumé here before seeding a fresh install.
RESUME_PATH = Path(settings.BASE_DIR) / "seed" / "Manideep_Chittimodu_Resume.pdf"
PORTRAIT_PATH = Path(settings.BASE_DIR) / "seed" / "portrait.jpg"
PORTRAIT_ALT = (
    "Manideep Chittimodu in a navy blazer and white shirt, hands in pockets, standing against a textured wall"
)

PROFILE = {
    "name": "Manideep Chittimodu",
    "role": "Gen AI / ML Engineer",
    "focus": "NLP, LLMs & Applied Machine Learning",
    "headline": "I build NLP, deep-learning and generative-AI systems end to end, then ship them behind a real interface.",
    "intro": (
        "From a CNN-based computer-vision security system to an LLM assistant grounded in live product data, "
        "I own the whole loop: data, features, training, evaluation and deployment."
    ),
    "education_line": "B.Tech in AI & Data Science · M.Tech in Computer Science, in progress",
    "location": "Hyderabad, India",
    "availability": "Open to Gen AI / ML roles",
    "email": "chittimodhu.manideep@gmail.com",
    "phone": "",
    "show_phone": False,
    "seo_description": (
        "Manideep Chittimodu is a Gen AI / ML engineer in Hyderabad who builds NLP, deep-learning and "
        "generative-AI systems end to end — from RAG assistants to computer-vision pipelines."
    ),
    "about": "\n\n".join(
        [
            "I studied Artificial Intelligence and Data Science at Vignan Institute of Technology and Science in "
            "Hyderabad, where supervised and unsupervised learning, NLP, and the linear algebra, probability and "
            "statistics underneath them were the core of the degree rather than an add-on. I'm now doing my M.Tech "
            "in Computer Science there.",
            "What I care about most is the part after the notebook. A model only counts once someone can use it, so "
            "I build the interface around it too — APIs, auth, databases, dashboards. That's how Vastra's assistant "
            "ended up answering from live product data, and how a CNN prototype became a deployed entry-point system "
            "with real-time logs.",
            "I follow new work in generative AI closely and use LLMs in my own workflow every day. I write clean, "
            "documented code, I'm comfortable working alone or in a team, and I'm happiest when there's a new method "
            "to research and try.",
            "Outside the lab I organised Byte Crunchers, a 24-hour hackathon with 1000+ applicants, represented my "
            "department at AIDAYS 2024, and coordinated NSS activities at VGNT.",
        ]
    ),
}

SOCIAL_LINKS = [
    ("LinkedIn", "https://www.linkedin.com/in/manideep311/", SocialLink.Kind.LINKEDIN),
    ("GitHub", "https://github.com/manideep311", SocialLink.Kind.GITHUB),
]

FIELD_NOTES = [
    ("4", "ML & AI projects built end to end"),
    ("6", "certifications — IBM, Qualcomm, Microsoft & more"),
    ("1st", "prize, IP2K24 Project Expo"),
    ("1000+", "applicants at the 24-hr hackathon I organised"),
]

PRINCIPLES = [
    (
        "Retrieve, then generate",
        "An assistant should answer from your data, not from thin air. Vastra retrieves the right products with "
        "embedding search before a model writes a word.",
    ),
    (
        "Own the whole loop",
        "Collecting the dataset, cleaning it, engineering features, training, evaluating, deploying — then logging "
        "what happens in the real world.",
    ),
    (
        "Explainable over magical",
        "For NextCinema I wrote a similarity score you can read line by line instead of a black box nobody can question.",
    ),
    (
        "Math underneath",
        "Linear algebra, probability and statistics were the core of my degree, so models are tools I can reason about.",
    ),
]

PROJECTS = [
    {
        "title": "Vastra",
        "slug": "vastra",
        "year": "2025",
        "tagline": "A B2B marketplace whose assistant answers from the catalogue, not from guesswork.",
        "summary": (
            "Buyers ask questions in plain language. Vastra retrieves the relevant products from live product data "
            "with embedding-based semantic search, then a Hugging Face model writes the answer from what was "
            "retrieved — retrieval plus LLM generation."
        ),
        "description": (
            "Vastra is a B2B textile marketplace with an AI assistant built into it. Instead of letting a language "
            "model improvise, every answer starts with retrieval: the buyer's question is embedded, matched against "
            "live product data with semantic search, and only then handed to a Hugging Face model to write the reply.\n\n"
            "Around the assistant sits a complete marketplace with two very different users:\n"
            "- Buyers browse, ask the assistant, and build carts.\n"
            "- Suppliers manage their catalogue and get AI-assisted bulk-quote suggestions.\n\n"
            "Buyer and supplier sessions are fully isolated, and the same business rules are enforced in the UI, "
            "the cart and the API so nothing can slip through one layer."
        ),
        "contribution": (
            "Built the AI assistant: embeddings, semantic search over live product data and grounded LLM replies.\n"
            "Added AI-assisted bulk-quote suggestions for suppliers.\n"
            "Delivered the surrounding B2B marketplace with fully isolated buyer and supplier sessions.\n"
            "Enforced business rules consistently across the UI, the cart and the API."
        ),
        "outcomes": "Live on the web\nRetrieval-augmented, grounded answers\nTwo isolated user roles",
        "technologies": "Node.js, Express, React, MongoDB, Hugging Face API, Embeddings",
        "note": "retrieval first, generation second",
        "art": Project.Art.VASTRA,
        "accent": "#B5462E",
        "live_url": "https://vastra-manideep.vercel.app/",
    },
    {
        "title": "AI Uniform Detection & Authentication",
        "slug": "uniform-detection",
        "year": "2025",
        "tagline": "A computer-vision checkpoint that knows who walked in — and whether they're in uniform.",
        "summary": (
            "A CNN classifier and a face-recognition pipeline built with OpenCV and DeepFace that recognise faces, "
            "ID cards and uniforms at entry points, then log attendance in real time."
        ),
        "description": (
            "Checking identity and dress code at an entrance is repetitive work that is easy to get wrong. This "
            "system does it with computer vision: a camera at the entry point, a CNN classifier for uniforms and ID "
            "cards, and a face-recognition pipeline built on OpenCV and DeepFace.\n\n"
            "I owned the project end to end:\n"
            "- Collected and preprocessed the dataset.\n"
            "- Trained and evaluated the CNN classifier.\n"
            "- Deployed the pipeline with real-time attendance logging to SQLite.\n"
            "- Added dress-code compliance reporting on top of the logs."
        ),
        "contribution": (
            "Built the CNN classifier and the face-recognition pipeline.\n"
            "Owned dataset collection, preprocessing, training and evaluation.\n"
            "Deployed it with real-time attendance logging and dress-code compliance reporting."
        ),
        "outcomes": "Deployed end to end\nReal-time attendance logs\nDress-code compliance reports",
        "technologies": "Python, OpenCV, DeepFace, CNN, SQLite",
        "note": "dataset → model → deployed",
        "art": Project.Art.UNIFORM,
        "accent": "#2F6F4E",
    },
    {
        "title": "NextCinema",
        "slug": "nextcinema",
        "year": "2025",
        "tagline": "Film recommendations that can explain themselves.",
        "summary": (
            "A movie discovery app on the TMDB API with a custom similarity-scoring recommendation model — genre, "
            "cast, director, rating and popularity — designed to be interpretable rather than a black box."
        ),
        "description": (
            "Most recommenders can't tell you why they picked something. NextCinema can. I designed a custom "
            "similarity score that compares films on genre, cast, director, rating and popularity, so every "
            "suggestion can be traced back to the signals that produced it.\n\n"
            "The app is built with Next.js and TypeScript on top of the TMDB API:\n"
            "- Self-hosted JWT session auth.\n"
            "- Guest browsing for anyone, personalisation for signed-in accounts.\n"
            "- Account data stored in MongoDB, with Framer Motion for the interface."
        ),
        "contribution": (
            "Designed the explainable similarity-scoring recommendation model.\n"
            "Implemented self-hosted JWT session auth and guest browsing.\n"
            "Built account-gated personalisation on MongoDB."
        ),
        "outcomes": "Live on the web\nEvery recommendation is explainable\nGuest and signed-in modes",
        "technologies": "Next.js, TypeScript, MongoDB, TMDB API, Framer Motion",
        "note": "no black boxes",
        "art": Project.Art.CINEMA,
        "accent": "#A8322D",
        "live_url": "https://manideep2.vercel.app/",
    },
    {
        "title": "Falcon 9 Landing Prediction",
        "slug": "falcon-9",
        "year": "2025",
        "tagline": "Will the first stage come back? A classifier that predicts it.",
        "summary": (
            "My IBM Applied Data Science Capstone: launch data from the SpaceX REST API plus scraped records, explored "
            "with SQL and visual EDA, turned into features, and used to train classifiers that predict first-stage "
            "landing success."
        ),
        "description": (
            "Reusing a rocket's first stage changes the economics of a launch, so predicting whether it will land is "
            "a genuinely useful question. This capstone answers it with a full data-science pipeline:\n"
            "- Ingested launch data from the SpaceX REST API and scraped historical records.\n"
            "- Cleaned and explored it with SQL and visual EDA.\n"
            "- Engineered features and trained Scikit-learn classification models.\n"
            "- Compared the models and presented the results in an interactive Plotly Dash dashboard."
        ),
        "contribution": (
            "Ingested the SpaceX REST API and scraped launch records.\n"
            "Ran SQL and visual EDA, then engineered features.\n"
            "Trained and evaluated Scikit-learn classification models.\n"
            "Presented the results in an interactive Plotly Dash dashboard."
        ),
        "outcomes": "Full data-science pipeline\nSupervised classifiers compared\nInteractive dashboard",
        "technologies": "Python, Pandas, SQL, Scikit-learn, Plotly Dash",
        "note": "API → SQL → features → model",
        "art": Project.Art.FALCON,
        "accent": "#D9622B",
        "github_url": "https://github.com/manideep311/Applied-Data-Science-Capstone-IBM/blob/main/README.md#rocket-applied-data-science-capstone",
        "extra_link_label": "Capstone credential",
        "extra_link_url": "https://coursera.org/share/6dcf061a7a27d8fddcf3664da1d64942",
    },
]

EXPERIENCE = [
    {
        "role": "Web Development Intern",
        "organization": "Prodigy InfoTech",
        "location": "Mumbai",
        "start_date": date(2025, 9, 1),
        "end_date": date(2025, 12, 31),
        "highlights": (
            "Built responsive web pages and front-end features with modern web technologies.\n"
            "Sharpened debugging, problem-solving and clean-code habits on practical development tasks.\n"
            "Worked in a professional Agile environment, to best practices and deadlines.\n"
            "Completed the 3-month internship and received a Letter of Recommendation for outstanding performance."
        ),
        "links": [
            (
                "Internship certificate",
                "https://drive.google.com/file/d/11yAmtSeSu4Ml3HPfBof56eDNLL5IHRx9/view?usp=drive_link",
            ),
            (
                "Letter of Recommendation",
                "https://drive.google.com/file/d/1uN-HzGIKFvE2dnA_WXY5aRtDj4rp_B0S/view?usp=drive_link",
            ),
        ],
    }
]

EDUCATION = [
    {
        "degree": "M.Tech",
        "field": "Computer Science",
        "institution": "Vignan Institute of Technology and Science",
        "location": "Hyderabad",
        "start_date": date(2025, 9, 1),
        "end_date": None,
        "score": "CGPA 8.8 / 10",
        "focus": "",
    },
    {
        "degree": "B.Tech",
        "field": "Artificial Intelligence & Data Science",
        "institution": "Vignan Institute of Technology and Science",
        "location": "Hyderabad",
        "start_date": date(2021, 9, 1),
        "end_date": date(2025, 6, 30),
        "score": "CGPA 7.2 / 10",
        "focus": "Supervised & unsupervised learning, NLP, linear algebra, probability and statistics.",
    },
]

CERTIFICATIONS = [
    ("RAG and Agentic AI", "IBM / Coursera", "https://coursera.org/share/dc20dd06b3f2f3ecab20dbdd0ff49d95"),
    (
        "IBM Data Science Professional Certificate",
        "IBM / Coursera",
        "https://coursera.org/share/683414efb9f86525f321e85dac0a0f6c",
    ),
    (
        "AI Upskilling: Hands-On Development from Model to App",
        "Qualcomm Technologies",
        "https://www.credly.com/badges/8a1ab48a-1b9a-4370-85a9-24398b7407e3/public_url",
    ),
    (
        "End-to-End Machine Learning",
        "Udemy",
        "https://www.udemy.com/certificate/UC-7fdf47de-9522-4c27-b933-41f3e8df2882/",
    ),
    (
        "Microsoft Certified: Azure Fundamentals (AZ-900)",
        "Microsoft",
        "https://www.credly.com/badges/9b50956c-7a29-48ca-ad07-f35693e949d7/public_url",
    ),
    (
        "Cloud Computing (Elite)",
        "NPTEL / IIT",
        "https://drive.google.com/file/d/1-hY7JdGXlqj_XOIgp_d0psWrlcrdX-mB/view?usp=drive_link",
    ),
]

ACHIEVEMENTS = [
    ("1st Prize", "IP2K24 Project Expo — VGNT"),
    ("Hackathon organiser", "“Byte Crunchers”, a 24-hour hackathon with 1000+ applicants"),
    ("Department Representative", "AIDAYS 2024"),
    ("Social Media Head", "AI & DS Department"),
    ("NSS Department Co-ordinator", "VGNT"),
]

SKILLS = [
    {
        "title": "Generative AI & NLP",
        "builds": "Assistants that answer from your own data — retrieval, prompts, agents.",
        "seen_in": "Vastra",
        "icon": SkillCategory.Icon.SPARK,
        "style": SkillCategory.Style.STICKERS,
        "skills": [
            "LLMs & GPT (OpenAI API)",
            "LangChain",
            "RAG pipelines",
            "Vector embeddings",
            "Prompt engineering",
            "Hugging Face",
            "NLP",
            "AI agents",
        ],
    },
    {
        "title": "Machine Learning",
        "builds": "Models that are trained, evaluated honestly and can be explained.",
        "seen_in": "Uniform Detection, NextCinema, Falcon 9",
        "icon": SkillCategory.Icon.BRAIN,
        "style": SkillCategory.Style.TAGS,
        "skills": [
            "TensorFlow",
            "PyTorch",
            "Scikit-learn",
            "Supervised & unsupervised learning",
            "CNNs",
            "Deep learning",
            "Fine-tuning",
            "Model evaluation",
            "Feature engineering",
        ],
    },
    {
        "title": "Languages",
        "builds": "From notebooks to typed production front ends.",
        "seen_in": "Every project",
        "icon": SkillCategory.Icon.BRACES,
        "style": SkillCategory.Style.KEYS,
        "skills": ["Python", "JavaScript", "TypeScript", "SQL", "Dart"],
        "minor": ["C", "Java"],
    },
    {
        "title": "Data & MLOps",
        "builds": "Pipelines from a raw API to a dashboard, and models that actually deploy.",
        "seen_in": "Falcon 9, Uniform Detection",
        "icon": SkillCategory.Icon.PIPE,
        "style": SkillCategory.Style.PIPELINE,
        "skills": [
            "Pandas",
            "NumPy",
            "SQL",
            "ETL / data pipelines",
            "Plotly Dash",
            "Jupyter",
            "Model deployment",
            "Git",
            "Docker",
            "CI/CD",
        ],
    },
    {
        "title": "Dev & Cloud",
        "builds": "The real interface around the model — APIs, auth, databases.",
        "seen_in": "Vastra, NextCinema",
        "icon": SkillCategory.Icon.CLOUD,
        "style": SkillCategory.Style.LUGGAGE,
        "skills": ["FastAPI", "Node.js", "React.js", "Next.js", "PostgreSQL", "MongoDB", "AWS", "GCP"],
    },
    {
        "title": "Mathematics",
        "builds": "The reasoning underneath: why a model works, and when it won't.",
        "seen_in": "B.Tech core",
        "icon": SkillCategory.Icon.SIGMA,
        "style": SkillCategory.Style.FORMULA,
        "skills": ["Linear algebra", "Probability", "Statistics"],
    },
]

CONTENT_MODELS = [
    ExperienceLink,
    Experience,
    Education,
    Certification,
    Achievement,
    FieldNote,
    Principle,
    Skill,
    SkillCategory,
    SocialLink,
    Project,  # cascades to ProjectImage
    SiteProfile,
]


class Command(BaseCommand):
    help = "Load the résumé content into the CMS (runs only on an empty database unless --reset)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete existing public content first. Contact messages are kept."
        )

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            for model in CONTENT_MODELS:
                model.objects.all().delete()
        elif SiteProfile.objects.exists():
            self.stdout.write(
                self.style.WARNING("Content already exists — nothing changed. Use --reset to replace it.")
            )
            return

        profile = SiteProfile(**PROFILE)
        if RESUME_PATH.exists():
            with RESUME_PATH.open("rb") as handle:
                profile.resume.save(RESUME_PATH.name, File(handle), save=False)
        if PORTRAIT_PATH.exists():
            # Assigned (not saved) so model.save() applies the film look and WebP encoding.
            profile.portrait = File(PORTRAIT_PATH.open("rb"), name=PORTRAIT_PATH.name)
            profile.portrait_alt = PORTRAIT_ALT
        profile.save()
        if profile.portrait:
            profile.portrait.close()

        for order, (label, url, kind) in enumerate(SOCIAL_LINKS):
            SocialLink.objects.create(label=label, url=url, kind=kind, order=order)

        for order, (value, label) in enumerate(FIELD_NOTES):
            FieldNote.objects.create(value=value, label=label, order=order)

        for order, (title, body) in enumerate(PRINCIPLES):
            Principle.objects.create(title=title, body=body, order=order)

        for order, data in enumerate(PROJECTS):
            Project.objects.create(order=order, status=Project.Status.PUBLISHED, is_featured=True, **data)

        for order, data in enumerate(EXPERIENCE):
            data = dict(data)
            links = data.pop("links")
            job = Experience.objects.create(order=order, **data)
            for link_order, (label, url) in enumerate(links):
                ExperienceLink.objects.create(experience=job, label=label, url=url, order=link_order)

        for order, data in enumerate(EDUCATION):
            Education.objects.create(order=order, **data)

        for order, (name, issuer, url) in enumerate(CERTIFICATIONS):
            Certification.objects.create(name=name, issuer=issuer, url=url, order=order)

        for order, (title, detail) in enumerate(ACHIEVEMENTS):
            Achievement.objects.create(title=title, detail=detail, order=order)

        for order, data in enumerate(SKILLS):
            data = dict(data)
            names = data.pop("skills")
            minor = data.pop("minor", [])
            category = SkillCategory.objects.create(order=order, **data)
            for skill_order, name in enumerate(names):
                Skill.objects.create(category=category, name=name, order=skill_order)
            for skill_order, name in enumerate(minor, start=len(names)):
                Skill.objects.create(category=category, name=name, order=skill_order, is_minor=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded the portfolio with {len(PROJECTS)} published projects. Edit everything in the admin."
            )
        )
