"""Review-aware foundational STEM lessons, separated from the translation engine.

English lessons are editorial source material. No local-language translation is
invented; those must be reviewed and explicitly published later.
"""
from flask import Blueprint, abort, render_template_string, request

stem_bp = Blueprint("stem", __name__, url_prefix="/learn")

LESSONS = [
    {"slug":"plant-food","title":"How plants make food","subject":"Basic Science","level":"Primary 4","concept":"Photosynthesis","explanation":"Plants use sunlight, water and carbon dioxide from the air to make food. During this process they release oxygen.","question":"What provides energy for photosynthesis?","options":["Sunlight","Soil alone","Wind"],"answer":0},
    {"slug":"fractions","title":"Fractions in everyday life","subject":"Mathematics","level":"Primary 4","concept":"Fractions","explanation":"A fraction describes part of a whole. If a cake is divided equally into four pieces, one piece is one quarter.","question":"What fraction is one of four equal pieces?","options":["One quarter","One half","One whole"],"answer":0},
    {"slug":"water-cycle","title":"Where rain comes from","subject":"Basic Science","level":"Primary 5","concept":"Water cycle","explanation":"Sunlight warms water and some changes into water vapour. Vapour cools into tiny droplets in clouds. Droplets can fall as rain.","question":"What is water changing into vapour called?","options":["Evaporation","Freezing","Melting"],"answer":0},
    {"slug":"computer-input","title":"How computers receive information","subject":"Computing","level":"Primary 5","concept":"Input devices","explanation":"An input device lets a person send information to a computer. Keyboards, microphones and touchscreens are common examples.","question":"Which device can send typed text to a computer?","options":["Keyboard","Loudspeaker","Monitor"],"answer":0},
    {"slug":"simple-circuits","title":"Making a light shine","subject":"Technology","level":"JSS 1","concept":"Electric circuit","explanation":"A simple circuit needs an energy source, conductors and a device such as a bulb. A complete circuit allows electric current to flow.","question":"What usually stops a bulb shining in a simple circuit?","options":["An open switch","A closed switch","A complete wire connection"],"answer":0},
]
LESSON_BY_SLUG = {lesson["slug"]: lesson for lesson in LESSONS}
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ page_title }} | TechDialect STEM</title>
<style>
:root{font-family:system-ui,sans-serif;color:#182b3a;background:#f5f9fb}
*{box-sizing:border-box}body{margin:0}.wrap{max-width:840px;margin:auto;padding:24px}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:30px}
select,button{font:inherit}select{padding:10px;border-radius:8px;margin:6px}form button{padding:10px;border:0;border-radius:8px;background:#006887;color:white}label{display:block;margin-top:16px}
a{color:#005c86}a:focus-visible,button:focus-visible{outline:3px solid #e38b25;outline-offset:3px}
article,.card{background:white;border:1px solid #d7e4e9;border-radius:16px;padding:22px;margin:12px 0}
h1{font-size:clamp(1.6rem,4vw,2.4rem)}.muted{color:#486476}.tag{font-size:.85rem;color:#306078}
.option{display:block;width:100%;padding:14px;border:1px solid #c8d6dd;background:#fff;border-radius:10px;text-align:left;margin:9px 0;cursor:pointer;font-size:1rem}
.option:hover{background:#edf7fa}.option.correct{border-color:#25754a;background:#e6f6ec}.option.incorrect{border-color:#9f4d40;background:#fcece9}
.note{border-left:4px solid #e5a14a;padding:10px 14px;background:#fffaec}
</style></head><body><main class="wrap">
<header><strong>TechDialect STEM</strong><a href="/learn">All lessons</a></header>
{% if lesson %}
<article><p class="tag">{{ lesson.subject }} · {{ lesson.level }}</p><h1>{{ lesson.title }}</h1>
<h2>{{ lesson.concept }}</h2><p>{{ lesson.explanation }}</p>
<form method="get"><label for="language">Reviewed terminology language</label>
<select name="language" id="language">
<option value="">English only</option>
{% for lang in languages %}<option value="{{ lang }}" {% if lang==selected_lang %}selected{% endif %}>{{ lang }}</option>{% endfor %}
</select><button type="submit">Show terminology</button></form>
{% if selected_lang %}
{% if term %}
<section class="card" aria-label="Verified local-language term">
<p class="tag">Published terminology · {{ selected_lang }}</p>
<strong>{{ term.local_text }}</strong>
{% if term.dialect %}<p class="muted">Dialect: {{ term.dialect }}</p>{% endif %}
</section>
{% else %}
<p class="note">No reviewed {{ selected_lang }} terminology has been published for this concept. The English explanation remains available.</p>
{% endif %}
{% endif %}
<p class="note">English source lesson. Local-language editions will appear only after teacher and native-speaker review.</p>
<h3>Check your understanding</h3><p>{{ lesson.question }}</p>
{% for option in lesson.options %}
<button type="button" class="option" data-correct="{{ 'true' if loop.index0 == lesson.answer else 'false' }}">{{ option }}</button>
{% endfor %}
<p id="feedback" role="status" aria-live="polite"></p></article>
<script>
document.querySelectorAll(".option").forEach(button=>button.addEventListener("click",()=>{
document.querySelectorAll(".option").forEach(b=>{b.disabled=true;b.classList.add(b.dataset.correct==="true"?"correct":"incorrect")});
document.getElementById("feedback").textContent=button.dataset.correct==="true"?"Correct! Well done.":"Not quite. The correct answer is highlighted.";
}));
</script>
{% else %}
<h1>Science and mathematics, made understandable</h1>
<p class="muted">Explore the first editorial English STEM lessons. Reviewed Nigerian-language lessons are coming next.</p>
{% for item in lessons %}<article><p class="tag">{{ item.subject }} · {{ item.level }}</p>
<h2><a href="{{ url_for('stem.lesson_detail',slug=item.slug) }}">{{ item.title }}</a></h2>
<p>{{ item.concept }}</p></article>{% endfor %}
{% endif %}</main></body></html>"""

@stem_bp.get("/")
def index():
    return render_template_string(PAGE, page_title="Learn", lessons=LESSONS, lesson=None)

def available_languages():
    from smart_translation_system import db_lang_names
    return sorted(db_lang_names())

def reviewed_term(concept, language):
    """Only expose verified, explicitly published terms; never guess a translation."""
    if not language:
        return None
    from smart_translation_system import get_db
    from publishing import _schema
    db = get_db()
    _schema(db)
    return db.execute(
        """SELECT s.local_text, s.dialect
           FROM published_terms p JOIN language_submissions s
           ON s.id=p.submission_id
           WHERE s.status='approved' AND s.language=?
           AND LOWER(TRIM(s.english_text))=LOWER(TRIM(?))
           ORDER BY p.published_at DESC LIMIT 1""",
        (language, concept)
    ).fetchone()

@stem_bp.get("/<slug>")
def lesson_detail(slug):
    lesson = LESSON_BY_SLUG.get(slug)
    if not lesson:
        abort(404)
    languages = available_languages()
    selected = request.args.get("language", "").strip()
    if selected and selected not in languages:
        abort(400)
    term = reviewed_term(lesson["concept"], selected)
    return render_template_string(PAGE, page_title=lesson["title"], lesson=lesson,
                                  languages=languages, selected_lang=selected, term=term)
