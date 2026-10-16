"""Starter STEM learning pathways.

These are pilot grade groupings derived from TechDialect's authored lessons,
not a claim of government curriculum certification. School validation is needed.
"""
PATHWAYS = (
    {
        "slug": "primary-4",
        "title": "Primary 4 STEM Foundations",
        "level": "Primary 4",
        "description": "Explore maths, living things and everyday physical science through seven lessons.",
        "lesson_slugs": ("fractions", "place-value", "multiplication-arrays", "plant-food", "states-of-matter", "magnetism", "human-senses"),
    },
    {
        "slug": "primary-5",
        "title": "Primary 5 Discoveries",
        "level": "Primary 5",
        "description": "Build scientific, digital-safety and maths skills through seven lessons.",
        "lesson_slugs": ("water-cycle", "force-motion", "soil-types", "food-chains", "computer-input", "decimals", "safe-internet"),
    },
    {
        "slug": "jss-1",
        "title": "JSS 1 Technology",
        "level": "JSS 1",
        "description": "Explore technology, measurements, algorithms and energy through six lessons.",
        "lesson_slugs": ("simple-circuits", "integers", "measurements-units", "energy-transfer", "algorithm-steps", "weather-climate"),
    },
    {
        "slug":"adult-digital-basics",
        "title":"Smartphones and Digital Confidence",
        "level":"Adult Education",
        "description":"Learn phones, connections, typing and everyday file management.",
        "lesson_slugs":("smartphone-basics","mobile-data-wifi","typing-and-voice","photos-files"),
    },
    {
        "slug":"adult-online-safety",
        "title":"Online Safety and Everyday Services",
        "level":"Adult Education",
        "description":"Use email, search and payments safely, and recognize common scams.",
        "lesson_slugs":("email-basics","recognize-scams","search-trust","digital-payments"),
    },
    {
        "slug":"adult-work-ai",
        "title":"Work, Business and AI Tools",
        "level":"Adult Education",
        "description":"Learn document skills, budgeting, online business and responsible AI.",
        "lesson_slugs":("documents-cv","spreadsheets-budget","sell-online","ai-assistants"),
    },
)
PATHWAY_BY_SLUG = {path["slug"]: path for path in PATHWAYS}


def validate_pathways(lessons):
    """Fail early on missing, duplicate or mismatched learning material."""
    if len(PATHWAYS) != len(PATHWAY_BY_SLUG):
        raise ValueError("Duplicate pathway slug")
    seen = set()
    for path in PATHWAYS:
        if not path["lesson_slugs"]:
            raise ValueError("Empty pathway")
        for slug in path["lesson_slugs"]:
            if slug not in lessons:
                raise ValueError("Pathway references nonexistent lesson: " + slug)
            if lessons[slug]["level"] != path["level"]:
                raise ValueError("Pathway level mismatch: " + slug)
            if slug in seen:
                raise ValueError("Lesson belongs to multiple pathways: " + slug)
            seen.add(slug)
    if seen != set(lessons):
        raise ValueError("Unassigned lessons: " + ", ".join(sorted(set(lessons) - seen)))
    return True
