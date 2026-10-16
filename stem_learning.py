"""Review-aware foundational STEM lessons, separated from the translation engine.

English lessons are editorial source material. No local-language translation is
invented; those must be reviewed and explicitly published later.
"""
from flask import Blueprint, abort, render_template_string, request, Response

stem_bp = Blueprint("stem", __name__, url_prefix="/learn")

LESSONS = [
    {"slug":"plant-food","title":"How plants make food","subject":"Basic Science","level":"Primary 4","concept":"Photosynthesis","explanation":"Plants use sunlight, water and carbon dioxide from the air to make food. During this process they release oxygen.","question":"What provides energy for photosynthesis?","options":["Sunlight","Soil alone","Wind"],"answer":0},
    {"slug":"fractions","title":"Fractions in everyday life","subject":"Mathematics","level":"Primary 4","concept":"Fractions","explanation":"A fraction describes part of a whole. If a cake is divided equally into four pieces, one piece is one quarter.","question":"What fraction is one of four equal pieces?","options":["One quarter","One half","One whole"],"answer":0},
    {"slug":"water-cycle","title":"Where rain comes from","subject":"Basic Science","level":"Primary 5","concept":"Water cycle","explanation":"Sunlight warms water and some changes into water vapour. Vapour cools into tiny droplets in clouds. Droplets can fall as rain.","question":"What is water changing into vapour called?","options":["Evaporation","Freezing","Melting"],"answer":0},
    {"slug":"computer-input","title":"How computers receive information","subject":"Computing","level":"Primary 5","concept":"Input devices","explanation":"An input device lets a person send information to a computer. Keyboards, microphones and touchscreens are common examples.","question":"Which device can send typed text to a computer?","options":["Keyboard","Loudspeaker","Monitor"],"answer":0},
    {"slug":"simple-circuits","title":"Making a light shine","subject":"Technology","level":"JSS 1","concept":"Electric circuit","explanation":"A simple circuit needs an energy source, conductors and a device such as a bulb. A complete circuit allows electric current to flow.","question":"What usually stops a bulb shining in a simple circuit?","options":["An open switch","A closed switch","A complete wire connection"],"answer":0},
    {"slug":"place-value","title":"Understanding place value","subject":"Mathematics","level":"Primary 4","concept":"Place value","explanation":"The position of a digit tells us its value. In 4,582, the digit 5 is in the hundreds place, so it represents 500.","question":"What does the digit 5 represent in 4,582?","options":["5","50","500"],"answer":2},
    {"slug":"multiplication-arrays","title":"Multiplication using groups","subject":"Mathematics","level":"Primary 4","concept":"Multiplication","explanation":"Multiplication can show equal groups. Three rows with four seeds in each row contain twelve seeds altogether: 3 × 4 = 12.","question":"How many seeds are in three groups of four?","options":["12","7","16"],"answer":0},
    {"slug":"states-of-matter","title":"Solids, liquids and gases","subject":"Basic Science","level":"Primary 4","concept":"States of matter","explanation":"Solids keep their shape, liquids take the shape of their container, and gases spread to fill available space. Water can exist as ice, liquid water or vapour.","question":"Which state of matter takes the shape of its container but has a fixed volume?","options":["Gas","Liquid","Solid"],"answer":1},
    {"slug":"magnetism","title":"Discovering magnets","subject":"Basic Science","level":"Primary 4","concept":"Magnetism","explanation":"A magnet can attract certain materials such as iron. Magnets have north and south poles. Opposite poles attract while like poles repel.","question":"What happens when two north poles face each other?","options":["They repel","They always attract","They disappear"],"answer":0},
    {"slug":"human-senses","title":"How we sense our world","subject":"Basic Science","level":"Primary 4","concept":"Five senses","explanation":"Our eyes help us see, ears detect sounds, the nose detects smells, the tongue helps us taste, and skin senses touch, temperature and pressure.","question":"Which sense organ helps us hear?","options":["Skin","Tongue","Ear"],"answer":2},
    {"slug":"decimals","title":"Decimals in everyday money","subject":"Mathematics","level":"Primary 5","concept":"Decimals","explanation":"Decimals can represent parts of a whole. The decimal 0.5 means five tenths, which is the same amount as one half.","question":"Which fraction has the same value as 0.5?","options":["One tenth","One half","One quarter"],"answer":1},
    {"slug":"force-motion","title":"Pushes, pulls and movement","subject":"Basic Science","level":"Primary 5","concept":"Forces and motion","explanation":"A force is a push or a pull. It can start, stop or change the direction or speed of a moving object. Kicking a ball applies a force.","question":"Which action applies a force to a stationary ball?","options":["Pushing it","Watching it","Naming it"],"answer":0},
    {"slug":"soil-types","title":"Learning about soil","subject":"Basic Science","level":"Primary 5","concept":"Soil types","explanation":"Soil supports plants and holds water and air. Sandy soil has larger grains and usually drains water faster than clay-rich soil. Different crops need different soil conditions.","question":"Which soil generally drains water more quickly?","options":["Clay-rich soil","Sandy soil","Both always drain equally"],"answer":1},
    {"slug":"food-chains","title":"Living things depend on each other","subject":"Basic Science","level":"Primary 5","concept":"Food chains","explanation":"A food chain shows how energy passes from one living thing to another. Plants use sunlight to make food. Animals may eat plants or other animals.","question":"Which organism often starts a simple land food chain?","options":["A lion","A hawk","A green plant"],"answer":2},
    {"slug":"safe-internet","title":"Staying safe online","subject":"Computing","level":"Primary 5","concept":"Internet safety","explanation":"A strong password helps protect an account. Do not share passwords, private addresses or personal photographs with strangers online. Ask a trusted adult when something seems unsafe.","question":"What should you do if a stranger asks for your password online?","options":["Keep it private and tell a trusted adult","Send it to them","Post it publicly"],"answer":0},
    {"slug":"integers","title":"Positive and negative numbers","subject":"Mathematics","level":"JSS 1","concept":"Integers","explanation":"Integers include positive whole numbers, negative whole numbers and zero. A temperature of minus 3 degrees can be written as −3.","question":"Which of these is an integer less than zero?","options":["4","−3","0"],"answer":1},
    {"slug":"energy-transfer","title":"Energy changes form","subject":"Basic Science","level":"JSS 1","concept":"Energy transformation","explanation":"Energy can change from one form into another. An electric bulb changes electrical energy into light and also produces heat.","question":"What useful energy form does a switched-on light bulb produce?","options":["Sound only","Wind only","Light"],"answer":2},
    {"slug":"algorithm-steps","title":"Giving a computer clear instructions","subject":"Computing","level":"JSS 1","concept":"Algorithms","explanation":"An algorithm is an ordered set of steps for solving a problem. A computer program follows instructions, so the order and clarity of each step matter.","question":"What is an algorithm?","options":["A sequence of steps for a task","A type of computer screen","A password"],"answer":0},
    {"slug":"weather-climate","title":"Weather and climate are different","subject":"Basic Science","level":"JSS 1","concept":"Weather and climate","explanation":"Weather describes conditions such as rain, wind and temperature at a particular time and place. Climate describes typical weather patterns over many years.","question":"Which describes climate?","options":["Rain this afternoon","Typical rainfall over many years","A wind gust right now"],"answer":1},
    {"slug":"measurements-units","title":"Measuring things accurately","subject":"Mathematics","level":"JSS 1","concept":"SI units","explanation":"Measurements use agreed units. Length can be measured in metres, mass in kilograms and time in seconds. Choosing the right unit makes results easier to compare.","question":"What is the SI unit for length?","options":["Kilogram","Second","Metre"],"answer":2},
]
from adult_catalog import ADULT_LESSONS
LESSONS.extend(ADULT_LESSONS)
LESSON_BY_SLUG = {lesson["slug"]: lesson for lesson in LESSONS}
from curriculum_catalog import PATHWAYS, PATHWAY_BY_SLUG, validate_pathways
validate_pathways(LESSON_BY_SLUG)
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
.progress-indicator{display:block;color:#285f49;font-weight:600}
.reset-progress{border:1px solid #b4cad1;border-radius:8px;padding:8px 12px;background:#fff;margin:6px 0 16px}
ol{padding-left:1.7rem;line-height:1.7}li{margin:9px 0}
.video-placeholder{padding:24px;border:0;background:#18394c;color:white;border-radius:12px;cursor:pointer;min-height:140px;width:100%;font:inherit}
[data-video-player] iframe{aspect-ratio:16/9;width:100%;border:0;border-radius:12px}
</style></head><body><main class="wrap">
<header><strong>TechDialect STEM</strong><nav><a href="/learn/">School STEM</a> · <a href="/learn/adults">Adult Tech Learning</a> · <a href="/learn/progress">Progress</a> · <a href="/videos/">Video Tutorials</a></nav><small id="network-status" role="status" aria-live="polite"></small></header>
{% if lesson %}
<article data-lesson-detail="{{ lesson.slug }}"><p class="tag">{{ lesson.subject }} · {{ lesson.level }}</p><h1>{{ lesson.title }}</h1>
<h2>{{ lesson.concept }}</h2><p>{{ lesson.explanation }}</p>
{% if lesson.steps %}
<section class="card" aria-label="Practical step-by-step activity"><h2>Practice step by step</h2>
<ol>{% for step in lesson.steps %}<li>{{ step }}</li>{% endfor %}</ol>
<h3>Try this on your device</h3><p>{{ lesson.task }}</p>
<p class="muted">Practice with fictional or non-sensitive details. Do not share a password, PIN or OTP.</p>
</section>
{% endif %}
<form method="get"><label for="language">Reviewed terminology language</label>
<select name="language" id="language">
<option value="">English only</option>
{% for lang in languages %}<option value="{{ lang }}" {% if lang==selected_lang %}selected{% endif %}>{{ lang }}</option>{% endfor %}
</select><button type="submit">Show terminology</button></form>
{% if edition %}
<section class="card"><p class="tag">Human-reviewed {{ selected_lang }} lesson edition</p>
<p>{{ edition.explanation }}</p>
{% if local_steps %}
<h3>Reviewed step-by-step guidance</h3>
<ol>{% for step in local_steps %}<li>{{ step }}</li>{% endfor %}</ol>
{% endif %}
{% if local_task %}<h3>Try this</h3><p>{{ local_task }}</p>{% endif %}
<p><strong>Example:</strong> {{ edition.example_text }}</p>
<div class="quiz" data-quiz data-language="{{ selected_lang }}" aria-label="Local-language practice">
<h3>{{ edition.question }}</h3>
{% for choice in edition_choices %}
<button type="button" class="option" data-correct="{{ 'true' if loop.index0==0 else 'false' }}">{{ choice }}</button>
{% endfor %}
<p role="status" aria-live="polite"></p>
</div>
</section>
{% endif %}
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
{% if lesson.level=='Adult Education' and selected_lang and not edition %}
<p class="note">A fully reviewed {{ selected_lang }} version is not yet available. The English instructions below are the original learning material.</p>
{% endif %}
<p class="note">{% if edition %}The English version remains available for comparison.{% else %}English source lesson. Local-language editions will appear only after specialist review.{% endif %}</p>
<div class="quiz" data-quiz data-language="English" aria-label="English practice">
<h3>Check your understanding</h3><p>{{ lesson.question }}</p>
{% for option in lesson.options %}
<button type="button" class="option" data-correct="{{ 'true' if loop.index0 == lesson.answer else 'false' }}">{{ option }}</button>
{% endfor %}
<p role="status" aria-live="polite"></p></div>
{% if tutorials %}
<section aria-label="Related video tutorials"><h2>Watch a related tutorial</h2>
{% for tutorial in tutorials %}
<div class="card"><h3>{{ tutorial.title }}</h3><p class="muted">{{ tutorial.language }}</p>
{% if tutorial.description %}<p>{{ tutorial.description }}</p>{% endif %}
<div data-video-player>
<button type="button" class="video-placeholder" data-youtube-id="{{ tutorial.video_id }}"
 aria-label="Load YouTube video: {{ tutorial.title }}">▶ Play YouTube tutorial</button>
</div><p class="muted">Video is loaded only when you select Play. Internet is required.</p>
<a href="https://www.youtube.com/watch?v={{ tutorial.video_id }}"
 target="_blank" rel="noopener noreferrer">Open on YouTube</a></div>
{% endfor %}</section>
{% else %}<p class="muted">No YouTube tutorials have been published for this lesson yet.
<a href="/videos/">Browse the video library</a>.</p>{% endif %}
</article>
{% else %}
<h1>Learn with TechDialect</h1>
<p class="muted">Choose school STEM or practical technology learning for adults. All Nigerian-language editions must be reviewed before publication.</p>
<article><h2>Technology for adults, in familiar languages</h2>
<p>Learn how to use a smartphone, stay safe online, manage work and use AI tools.</p>
<p><a href="{{ url_for('stem.adults_index') }}">Explore Adult Education →</a></p></article>
<h2>School STEM (pilot lessons)</h2>
{% for path in school_pathways %}
<article class="pathway"><p class="tag">{{ path.level }} · {{ path.lesson_slugs|length }} lessons</p>
<h3><a href="{{ url_for('stem.path_detail', path_slug=path.slug) }}">{{ path.title }}</a></h3>
<p>{{ path.description }}</p></article>
{% endfor %}
<h2>School lesson library</h2>
<p id="learning-progress" role="status" aria-live="polite"></p>
<button type="button" id="clear-progress" class="reset-progress">Clear progress on this device</button>
{% for item in school_lessons %}<article data-lesson="{{ item.slug }}"><p class="tag">{{ item.subject }} · {{ item.level }}</p>
<h2><a href="{{ url_for('stem.lesson_detail',slug=item.slug) }}">{{ item.title }}</a></h2>
<p>{{ item.concept }}</p><small class="progress-indicator">Not practiced yet</small></article>{% endfor %}
{% endif %}
<script src="/videos/embed.js" defer></script>
<script>
(function() {
  // Only the device stores progress. No names, accounts or learner details are sent.
  const progressKey = 'techdialect-stem-progress-v1';
  function readProgress() {
    try {
      const value = JSON.parse(localStorage.getItem(progressKey) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch (e) { return {}; }
  }
  // Number of practice attempts per lesson and language, stored locally.
  const attemptsKey = 'techdialect-stem-attempts-v1';
  function recordAttempt(slug, language, correct) {
    try {
      const stats = JSON.parse(localStorage.getItem(attemptsKey) || '{}');
      const saved = stats && typeof stats === 'object' && !Array.isArray(stats) ? stats : {};
      const key = slug + '|' + language;
      const previous = saved[key] && typeof saved[key] === 'object' ? saved[key] : {};
      saved[key] = {total: Math.max(0, Number(previous.total) || 0) + 1,
                    correct: Math.max(0, Number(previous.correct) || 0) + (correct ? 1 : 0)};
      localStorage.setItem(attemptsKey, JSON.stringify(saved));
    } catch (e) {}
  }
  function saveProgress(slug, language) {
    try {
      const saved = readProgress();
      saved[slug + '|' + language] = true;
      localStorage.setItem(progressKey, JSON.stringify(saved));
    } catch (e) { /* Browsers with storage disabled still allow learning. */ }
  }
  function refreshProgress() {
    const saved = readProgress();
    let completed = 0;
    const items = document.querySelectorAll('[data-lesson]');
    items.forEach(function(item) {
      const isDone = Object.keys(saved).some(function(key) {
        return key.startsWith(item.dataset.lesson + '|') && saved[key] === true;
      });
      const indicator = item.querySelector('.progress-indicator');
      if (indicator) indicator.textContent = isDone ? 'Practiced successfully ✓' : 'Not practiced yet';
      if (isDone) completed++;
    });
    const status = document.getElementById('learning-progress');
    if (status) status.textContent = completed + ' of ' + items.length + ' lessons practiced successfully on this device.';
  }
  const resetButton = document.getElementById('clear-progress');
  if (resetButton) resetButton.addEventListener('click', function() {
    if (!window.confirm('Clear saved STEM progress on this device?')) return;
    try {
      localStorage.removeItem(progressKey);
      localStorage.removeItem(attemptsKey);
    } catch (e) {}
    refreshProgress();
  });
  refreshProgress();
  document.querySelectorAll('[data-quiz]').forEach(function(quiz) {
    const choices = Array.from(quiz.querySelectorAll('button.option'));
    // Correct-answer positions should not be predictable from the source template.
    for (let i = choices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const temp = choices[i]; choices[i] = choices[j]; choices[j] = temp;
    }
    const status = quiz.querySelector('[role="status"]');
    choices.forEach(function(button) {
      quiz.insertBefore(button, status);
      button.addEventListener('click', function() {
        choices.forEach(function(item) {
          item.disabled = true;
          item.classList.toggle('correct', item.dataset.correct === 'true');
          item.classList.toggle('incorrect', item === button && item.dataset.correct !== 'true');
        });
        status.textContent = button.dataset.correct === 'true'
          ? 'Correct! Well done.'
          : 'Not quite. The correct answer is highlighted.';
        const detail = document.querySelector('[data-lesson-detail]');
        if (detail) {
          const language = quiz.dataset.language || 'English';
          const correct = button.dataset.correct === 'true';
          recordAttempt(detail.dataset.lessonDetail, language, correct);
          if (correct) saveProgress(detail.dataset.lessonDetail, language);
        }
      });
    });
  });
  const el = document.getElementById('network-status');
  function setConnection() {
    if(el) el.textContent = navigator.onLine ? 'Online' : 'Offline: saved lessons only';
  }
  window.addEventListener('online', setConnection);
  window.addEventListener('offline', setConnection);
  setConnection();
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      navigator.serviceWorker.register('/learn/sw.js', {scope:'/learn/'})
        .catch(function() { if(el) el.textContent = 'Offline downloads unavailable'; });
    });
  }
})();
</script></main></body></html>"""

@stem_bp.get("/")
def index():
    return render_template_string(PAGE, page_title="Learn", lesson=None,
                                  school_lessons=[x for x in LESSONS if x["level"] != "Adult Education"],
                                  school_pathways=[x for x in PATHWAYS if x["level"] != "Adult Education"])

ADULTS_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adult Technology Learning | TechDialect</title><style>
:root{font-family:system-ui,sans-serif;color:#153244;background:#f3f8fa}
body{margin:0}*{box-sizing:border-box}main{max-width:960px;margin:0 auto;padding:24px}
a{color:#005e80}a:focus-visible,select:focus-visible,button:focus-visible{outline:3px solid #e9a445;outline-offset:3px}
h1{font-size:clamp(2rem,5vw,3rem)}p{line-height:1.6}
.hero{background:#143e53;color:white;border-radius:20px;padding:32px;margin:20px 0}
.hero a{color:#fbd887}.pathways{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(265px,100%),1fr));gap:18px}
article,form{background:white;border:1px solid #d2e3e8;border-radius:14px;padding:20px;margin:16px 0}
label{display:block;font-weight:600;margin-bottom:8px}
select,button{font:inherit;padding:12px;border:1px solid #9bbcc6;border-radius:8px}
button{background:#006b83;color:white;border:0}
small{color:#3c6070}.tag{color:#2e6a78;font-weight:700}
</style></head><body><main>
<nav><a href="{{ url_for('stem.index') }}">School STEM</a> ·
<a href="/videos/?level=Adult+Education">Adult Video Tutorials</a> ·
<a href="{{ url_for('stem.progress_report') }}">Device Progress</a></nav>
<section class="hero"><small style="color:#c5edf0">TECHDIALECT ADULT EDUCATION</small>
<h1>Technology skills for everyday life</h1>
<p>Learn at your own pace, whether you are just starting with smartphones or want to grow a business using digital tools.</p>
<p>Read the English starter lessons now. Reviewed Nigerian-language editions appear as language and technical specialists publish them.</p>
</section>
<form method="get" action="{{ url_for('stem.adults_index') }}">
<label for="language">Choose a language for available reviewed lessons</label>
<select id="language" name="language"><option value="">English source material</option>
{% for lang in languages %}<option value="{{ lang }}" {% if lang==selected_lang %}selected{% endif %}>{{ lang }}</option>{% endfor %}
</select><button type="submit">Apply language</button>
<p><small>Selecting a language does not mean every lesson is translated yet. Unavailable reviewed editions retain clear English content.</small></p></form>
<h2>Choose a practical learning track</h2>
<div class="pathways">
{% for path in pathways %}
<article><p class="tag">{{ path.lesson_slugs|length }} short lessons</p>
<h3><a href="{{ url_for('stem.path_detail',path_slug=path.slug,language=selected_lang if selected_lang else none) }}">{{ path.title }}</a></h3>
<p>{{ path.description }}</p></article>
{% endfor %}</div>
<h2>All adult technology lessons</h2>
{% for lesson in lessons %}
<article data-lesson="{{ lesson.slug }}"><h3>
<a href="{{ url_for('stem.lesson_detail',slug=lesson.slug,language=selected_lang if selected_lang else none) }}">{{ lesson.title }}</a></h3>
<p><small>{{ lesson.subject }}</small></p>
<p>{{ lesson.concept }}</p><p class="progress-indicator">Not practiced yet</p></article>
{% endfor %}
<p><small>No fees, accounts or student identity are needed to read starter lessons. Practice results stay on this device.</small></p>
<script src="{{ url_for('stem.progress_script') }}" defer></script>
</main></body></html>"""

@stem_bp.get("/adults")
def adults_index():
    languages = available_languages()
    selected = request.args.get("language", "").strip()
    if selected and selected not in languages:
        abort(400)
    paths = [p for p in PATHWAYS if p["level"] == "Adult Education"]
    lessons = [x for x in LESSONS if x["level"] == "Adult Education"]
    return render_template_string(ADULTS_PAGE, pathways=paths, lessons=lessons,
                                  languages=languages, selected_lang=selected)

PATH_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ pathway.title }} | TechDialect STEM</title>
<style>
body{margin:0;background:#f5f9fb;color:#183144;font-family:system-ui,sans-serif}
main{max-width:820px;margin:0 auto;padding:24px}
a{color:#006187}a:focus-visible{outline:3px solid #e5a14a;outline-offset:3px}
article{padding:20px;margin:14px 0;border:1px solid #d7e4e9;border-radius:14px;background:white}
h1{font-size:clamp(1.5rem,4vw,2.2rem)}.muted{color:#425e6e}
.steps{display:grid;gap:12px}.progress-indicator{color:#2f6d48}
</style></head><body><main>
<p><a href="{{ url_for('stem.index') }}">← All learning pathways</a> ·
<a href="{{ url_for('stem.progress_report') }}">Device progress</a> ·
<a href="/videos/">Video Tutorials</a>
{% if pathway.level=='Adult Education' %} · <a href="{{ url_for('stem.adults_index') }}">Adult Education</a>{% endif %}</p>
<p class="muted">{{ pathway.level }} · Starter learning pathway</p>
<h1>{{ pathway.title }}</h1><p>{{ pathway.description }}</p>
<p class="muted">Follow the lessons in order. Each activity has a quick understanding check.
Successful practice is stored only on this device.</p>
<p id="pathway-progress" role="status" aria-live="polite"></p>
<section class="steps" aria-label="Ordered lessons">
{% for lesson in lessons %}
<article data-lesson="{{ lesson.slug }}">
<p class="muted">Lesson {{ loop.index }} of {{ lessons|length }} · {{ lesson.subject }}</p>
<h2><a href="{{ url_for('stem.lesson_detail', slug=lesson.slug, language=selected_lang if selected_lang else none) }}">{{ lesson.title }}</a></h2>
<p>{{ lesson.concept }}</p>
<small class="progress-indicator">Not practiced yet</small>
</article>
{% endfor %}
</section>
<script src="{{ url_for('stem.progress_script') }}" defer></script>
</main></body></html>"""

@stem_bp.get("/path/<path_slug>")
def path_detail(path_slug):
    pathway = PATHWAY_BY_SLUG.get(path_slug)
    if pathway is None:
        abort(404)
    selected = request.args.get("language", "").strip()
    if selected and selected not in available_languages():
        abort(400)
    sequence = [LESSON_BY_SLUG[slug] for slug in pathway["lesson_slugs"]]
    return render_template_string(PATH_PAGE, pathway=pathway, lessons=sequence, selected_lang=selected)

REPORT_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Learning progress | TechDialect STEM</title>
<style>
body{font:16px system-ui,sans-serif;color:#193545;background:#f5f9fb;margin:0}
main{max-width:940px;margin:0 auto;padding:24px}
article{background:white;border:1px solid #d6e5e8;border-radius:14px;padding:20px;margin:16px 0}
h1{font-size:clamp(1.6rem,4vw,2.3rem)}a{color:#00618b}
a:focus-visible,button:focus-visible{outline:3px solid #d69938;outline-offset:3px}
button{font:inherit;padding:12px;border:1px solid #c5d5d9;background:white;border-radius:10px;margin:3px}
.primary{background:#00667f;color:white;border-color:#00667f}
table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #dfe7eb}
.scroll{overflow-x:auto}.muted{color:#446372}caption{text-align:left;color:#446372;margin-bottom:10px}
</style></head><body><main>
<p><a href="{{ url_for('stem.index') }}">← Learning pathways</a></p>
<h1>Learning progress on this device</h1>
<p class="muted">A private, local snapshot of practice activity. No names, student IDs, or scores are transmitted to TechDialect.
Use separate devices or browser profiles for different learners.</p>
<article><h2>Progress summary</h2>
<p id="report-summary" role="status" aria-live="polite">Reading saved local practice...</p>
<button id="download-progress" type="button" class="primary">Export anonymous CSV report</button>
<button id="reset-device-progress" type="button">Clear local progress</button>
</article>
{% for path in pathways %}
<article><h2>{{ path.title }}</h2><div class="scroll"><table>
<caption>{{ path.level }} · {{ path.lesson_slugs|length }} starter lessons</caption>
<thead><tr><th scope="col">Subject and lesson</th><th scope="col">Practice status</th><th scope="col">Correct / attempts</th></tr></thead>
<tbody>
{% for slug in path.lesson_slugs %}
{% set lesson = lesson_map[slug] %}
<tr data-report-row data-slug="{{ slug }}" data-title="{{ lesson.title }}"
  data-level="{{ lesson.level }}" data-subject="{{ lesson.subject }}">
<td>{{ lesson.subject }} · <a href="{{ url_for('stem.lesson_detail', slug=slug) }}">{{ lesson.title }}</a></td>
<td data-report-status>Not practiced</td><td data-report-score>0 / 0</td>
</tr>
{% endfor %}
</tbody></table></div></article>
{% endfor %}
<p class="muted">These values count one question per completed practice attempt and should not be treated as an examination or verified school performance report.</p>
<script src="{{ url_for('stem.progress_script') }}" defer></script>
</main></body></html>"""

@stem_bp.get("/progress")
def progress_report():
    return render_template_string(REPORT_PAGE, pathways=PATHWAYS, lesson_map=LESSON_BY_SLUG)

PROGRESS_JS = "/* TechDialect learning progress is device-only. No cookies, accounts, or POST calls. */\n(function () {\n  \"use strict\";\n  const completedKey = \"techdialect-stem-progress-v1\";\n  const attemptsKey = \"techdialect-stem-attempts-v1\";\n  function read(key) {\n    try {\n      const value = JSON.parse(localStorage.getItem(key) || \"{}\");\n      return value && typeof value === \"object\" && !Array.isArray(value) ? value : {};\n    } catch (_) { return {}; }\n  }\n  function store(key, value) {\n    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}\n  }\n  function summary(slug, completed, attempts) {\n    const rows = Object.keys(completed).filter(function (key) {\n      return key.startsWith(slug + \"|\") && completed[key] === true;\n    });\n    const stats = Object.entries(attempts).filter(function (entry) {\n      return entry[0].startsWith(slug + \"|\") && entry[1] &&\n        typeof entry[1] === \"object\";\n    });\n    const counts = stats.reduce(function (out, entry) {\n      out.total += Math.max(0, Number(entry[1].total) || 0);\n      out.correct += Math.max(0, Number(entry[1].correct) || 0);\n      return out;\n    }, {total: 0, correct: 0});\n    return {mastered: rows.length > 0, attempts: counts.total, correct: counts.correct};\n  }\n  function render() {\n    const completed = read(completedKey);\n    const attempts = read(attemptsKey);\n    let mastered = 0;\n    const cards = Array.from(document.querySelectorAll(\"[data-lesson]\"));\n    cards.forEach(function (card) {\n      const current = summary(card.dataset.lesson, completed, attempts);\n      if (current.mastered) mastered += 1;\n      const indicator = card.querySelector(\".progress-indicator\");\n      if (indicator) {\n        indicator.textContent = current.mastered\n          ? \"Practiced successfully ✓\"\n          : current.attempts ? \"Keep practicing · \" + current.attempts + \" attempts\"\n          : \"Not practiced yet\";\n      }\n    });\n    const pathStatus = document.getElementById(\"pathway-progress\");\n    if (pathStatus) {\n      pathStatus.textContent = mastered + \" of \" + cards.length +\n        \" lessons practiced successfully on this device\";\n    }\n    const reportRows = Array.from(document.querySelectorAll(\"[data-report-row]\"));\n    let reportMastered = 0, reportAttempts = 0, reportCorrect = 0;\n    reportRows.forEach(function (row) {\n      const result = summary(row.dataset.slug, completed, attempts);\n      if (result.mastered) reportMastered += 1;\n      reportAttempts += result.attempts;\n      reportCorrect += result.correct;\n      const cell = row.querySelector(\"[data-report-status]\");\n      if (cell) cell.textContent = result.mastered\n        ? \"Practiced successfully\"\n        : result.attempts ? \"Still practicing\" : \"Not practiced\";\n      const score = row.querySelector(\"[data-report-score]\");\n      if (score) score.textContent = result.correct + \" / \" + result.attempts;\n    });\n    const reportSummary = document.getElementById(\"report-summary\");\n    if (reportSummary) {\n      reportSummary.textContent = reportMastered + \" / \" + reportRows.length +\n        \" lessons practiced successfully. \" + reportCorrect + \" correct answers out of \" +\n        reportAttempts + \" local practice attempts.\";\n    }\n    return {completed: completed, attempts: attempts};\n  }\n  function csvValue(value) {\n    return '\"' + String(value == null ? \"\" : value).replace(/\"/g, '\"\"') + '\"';\n  }\n  const download = document.getElementById(\"download-progress\");\n  if (download) download.addEventListener(\"click\", function () {\n    const local = render();\n    const rows = [\n      [\"Class\", \"Subject\", \"Lesson\", \"Practiced successfully\", \"Correct answers\", \"Attempts\"]\n    ];\n    document.querySelectorAll(\"[data-report-row]\").forEach(function (row) {\n      const status = summary(row.dataset.slug, local.completed, local.attempts);\n      rows.push([\n        row.dataset.level, row.dataset.subject, row.dataset.title,\n        status.mastered ? \"Yes\" : \"No\", status.correct, status.attempts\n      ]);\n    });\n    const content = rows.map(function (row) {\n      return row.map(csvValue).join(\",\");\n    }).join(\"\\r\\n\");\n    const file = new Blob([\"\\uFEFF\", content], {type: \"text/csv;charset=utf-8\"});\n    const link = document.createElement(\"a\");\n    const url = URL.createObjectURL(file);\n    link.href = url;\n    link.download = \"techdialect-device-learning-report.csv\";\n    link.click();\n    URL.revokeObjectURL(url);\n  });\n  const clear = document.getElementById(\"reset-device-progress\");\n  if (clear) clear.addEventListener(\"click\", function () {\n    if (!window.confirm(\"Clear learning progress and assessment attempts from this device?\")) return;\n    try {\n      localStorage.removeItem(completedKey);\n      localStorage.removeItem(attemptsKey);\n    } catch (_) {}\n    render();\n  });\n  render();\n})();"

@stem_bp.get("/progress.js")
def progress_script():
    response = Response(PROGRESS_JS, mimetype="application/javascript")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response

def lesson_tutorials(slug):
    from video_tutorials import published_for_lesson
    return published_for_lesson(slug)


def published_lesson_edition(slug, language):
    from smart_translation_system import get_db
    from lesson_editor import published_edition
    return published_edition(get_db(), slug, language)

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
    edition = None
    edition_choices = []
    local_steps = []
    local_task = ""
    if selected:
        import json
        edition = published_lesson_edition(slug, selected)
        if edition:
            edition_choices = json.loads(edition["options_json"])
            if "steps_json" in edition.keys() and edition["steps_json"]:
                local_steps = json.loads(edition["steps_json"])
            if "task_text" in edition.keys():
                local_task = edition["task_text"] or ""
    tutorials = lesson_tutorials(slug)
    return render_template_string(PAGE, page_title=lesson["title"], lesson=lesson,
                                  languages=languages, selected_lang=selected, term=term,
                                  edition=edition, edition_choices=edition_choices,
                                  local_steps=local_steps, local_task=local_task,
                                  tutorials=tutorials)

# Cache only public learning materials, not admin pages, credentials or private records.
# Previously visited language editions are cached for offline revisiting.
SW_VERSION = "techdialect-stem-v4"
SW_JS = r"""const CACHE_NAME = "techdialect-stem-v4";
const PRECACHE = ["/learn/", "/learn/adults", "/learn/progress", "/learn/progress.js",
                  "/learn/path/adult-digital-basics", "/learn/path/adult-online-safety",
                  "/learn/path/adult-work-ai",
                  "/learn/path/primary-4", "/learn/path/primary-5", "/learn/path/jss-1",
                  "/learn/plant-food",
                  "/learn/fractions",
                  "/learn/water-cycle",
                  "/learn/computer-input",
                  "/learn/simple-circuits",
                  "/learn/place-value",
                  "/learn/multiplication-arrays",
                  "/learn/states-of-matter",
                  "/learn/magnetism",
                  "/learn/human-senses",
                  "/learn/decimals",
                  "/learn/force-motion",
                  "/learn/soil-types",
                  "/learn/food-chains",
                  "/learn/safe-internet",
                  "/learn/integers",
                  "/learn/energy-transfer",
                  "/learn/algorithm-steps",
                  "/learn/weather-climate",
                  "/learn/measurements-units",
                  "/learn/smartphone-basics", "/learn/mobile-data-wifi",
                  "/learn/typing-and-voice", "/learn/photos-files", "/learn/email-basics",
                  "/learn/recognize-scams", "/learn/search-trust", "/learn/digital-payments",
                  "/learn/documents-cv", "/learn/spreadsheets-budget",
                  "/learn/sell-online", "/learn/ai-assistants"];
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME)
    .then((cache) => cache.addAll(PRECACHE))
    .then(() => self.skipWaiting()));
});
self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((names) =>
    Promise.all(names.filter((name) =>
      name.startsWith("techdialect-stem-") && name !== CACHE_NAME)
      .map((name) => caches.delete(name)))
  ).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin ||
      !url.pathname.startsWith("/learn/") || url.pathname === "/learn/sw.js") return;
  event.respondWith(
    fetch(req).then((response) => {
      if (response.ok && response.type === "basic") {
        const saved = response.clone();
        event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.put(req, saved)));
      }
      return response;
    }).catch(() => caches.match(req).then((saved) =>
      saved || caches.match("/learn/")))
  );
});
"""

@stem_bp.get("/sw.js")
def service_worker():
    response = Response(SW_JS, mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Service-Worker-Allowed"] = "/learn/"
    return response
