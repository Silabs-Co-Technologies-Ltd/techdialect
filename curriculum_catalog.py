"""Starter STEM learning pathways.

These are pilot grade groupings derived from TechDialect's authored lessons,
not a claim of government curriculum certification. School validation is needed.
"""
PATHWAYS = (
    {
        "slug": "primary-4",
        "title": "Primary 4 STEM Foundations",
        "level": "Primary 4",
        "description": "Explore fractions and the science of how plants make food.",
        "lesson_slugs": ("fractions", "plant-food"),
    },
    {
        "slug": "primary-5",
        "title": "Primary 5 Discoveries",
        "level": "Primary 5",
        "description": "Understand the water cycle and how computers receive information.",
        "lesson_slugs": ("water-cycle", "computer-input"),
    },
    {
        "slug": "jss-1",
        "title": "JSS 1 Technology",
        "level": "JSS 1",
        "description": "Discover the foundations of simple electrical circuits.",
        "lesson_slugs": ("simple-circuits",),
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
