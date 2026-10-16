"""Public TechDialect product landing page: zero external scripts or database reads."""
from flask import Blueprint, render_template_string

landing_bp = Blueprint("landing", __name__)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b1c27">
<meta name="description" content="TechDialect makes STEM, digital skills and technology education more accessible through Nigerian languages. Explore school lessons, adult technology training, and community-reviewed local-language knowledge.">
<meta property="og:type" content="website">
<meta property="og:title" content="TechDialect | Technology makes sense in every language">
<meta property="og:description" content="Learn STEM and digital skills, explore local-language lessons and help preserve the words that make learning possible.">
<title>TechDialect | Technology makes sense in every language</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='15' fill='%230b1c27'/%3E%3Cpath d='M16 21h31M32 21v27m-10-7 10 7 10-7' fill='none' stroke='%23baf47d' stroke-width='5' stroke-linecap='round'/%3E%3C/svg%3E">
<style>
:root{color-scheme:light;--navy:#0b1c27;--ink:#102734;--muted:#4e626b;--paper:#f7f8f5;--lime:#bded83;--line:#dbe4dc;--white:#fff;--orange:#ffb680;font:16px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);line-height:1.55}a{color:inherit;text-decoration:none}a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #337be6;outline-offset:4px}button{font:inherit}header{position:relative;z-index:5;border-bottom:1px solid #dce8dc;background:#fff}
.shell{max-width:1160px;padding:0 26px;margin:0 auto}.nav{min-height:78px;display:flex;align-items:center;justify-content:space-between;gap:24px}.brand{display:flex;align-items:center;gap:10px;font-weight:830;font-size:1.26rem;letter-spacing:-.7px;white-space:nowrap}
.brandmark{width:39px;height:39px;border-radius:12px;background:var(--navy);color:var(--lime);display:grid;place-items:center;font-size:1.45rem;font-weight:900}
.navlinks{display:flex;align-items:center;gap:24px;font-size:.88rem;color:#3b505b;font-weight:620}.navlinks a:hover,.foot a:hover{text-decoration:underline;text-underline-offset:5px}
.actions{display:flex;align-items:center;gap:12px}.button{display:inline-flex;justify-content:center;align-items:center;gap:9px;border-radius:11px;padding:12px 18px;font-size:.88rem;font-weight:750;border:1px solid transparent;transition:transform .14s ease,background .14s ease}.button:hover{transform:translateY(-2px)}.button.dark{background:var(--navy);color:white}.button.light{border-color:#c7d7ca;background:white;color:var(--navy)}.button.lime{background:var(--lime);color:var(--navy)}.label{font-size:.76rem;letter-spacing:.15em;font-weight:830;text-transform:uppercase;color:#46745e}.label.inverse{color:#b9ef84}
.hero{background:var(--navy);color:white;overflow:hidden;position:relative}.hero:before{content:"";position:absolute;right:-220px;top:-270px;width:670px;height:670px;border-radius:50%;background:radial-gradient(circle,#385a42aa 0,transparent 68%);pointer-events:none}.heroinner{padding:76px 0 88px;display:grid;grid-template-columns:1.05fr .95fr;align-items:center;gap:44px;position:relative}.hero h1{font-size:clamp(2.8rem,5.3vw,5.55rem);letter-spacing:-.066em;line-height:1.065;max-width:750px;margin:17px 0 21px;font-weight:820}.hero h1 em{font-style:normal;color:var(--lime)}.hero p{font-size:1.08rem;color:#c5d5d7;max-width:550px;margin:0 0 31px}.herobuttons{display:flex;gap:12px;flex-wrap:wrap}.subnote{font-size:.78rem!important;color:#9fb9b9!important;margin:22px 0 0!important}
.illustration{min-height:410px;position:relative;display:grid;align-content:center;justify-items:center}.orbit{position:absolute;border:1px solid #9dbbb035;border-radius:50%;width:385px;height:385px;top:8px}.orbit.two{width:285px;height:285px;top:58px}.showcase{background:#fff;color:var(--ink);width:min(410px,96%);padding:24px;border-radius:20px;box-shadow:0 25px 65px #0005;position:relative;z-index:2;transform:rotate(-3deg)}.mini-top{display:flex;justify-content:space-between;align-items:center;color:#5a6b71;font-size:.75rem;font-weight:700;padding-bottom:14px;border-bottom:1px solid var(--line)}.dot{height:8px;width:8px;background:#62b57c;border-radius:50%;display:inline-block;margin-right:6px}.showcase h2{margin:18px 0 6px;font-size:1.65rem;letter-spacing:-.035em}.showcase p{font-size:.88rem;color:#526673;margin:0 0 14px}.translation{border-radius:12px;background:#edf7e9;padding:13px 15px;display:flex;flex-direction:column;gap:5px;margin:12px 0}.translation small{font-weight:780;font-size:.7rem;color:#42704b;letter-spacing:.09em}.translation strong{font-size:1.08rem;color:#143a27}.translation:nth-of-type(3){background:#f4f1e6}.translation:nth-of-type(3) small{color:#79623c}.illustration .float{position:absolute;z-index:3;padding:10px 15px;background:#bcec89;border-radius:10px;font-size:.74rem;font-weight:800;color:#153323;right:-2%;bottom:12%;box-shadow:0 15px 35px #0002;transform:rotate(4deg)}.spark{position:absolute;left:0;top:10%;font-size:2.8rem;color:#d4eaac;transform:rotate(-12deg)}
.stats{background:#eaf0e9;border-bottom:1px solid var(--line)}.statsinner{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;padding:20px 0}.stat{display:flex;align-items:center;gap:14px}.stat strong{font-size:1.5rem;letter-spacing:-.06em}.stat span{font-size:.84rem;color:#536a67}.staticon{font-size:1.55rem}
.section{padding:92px 0}.sectionhead{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:33px}.section h2{font-size:clamp(2.05rem,4vw,3.3rem);letter-spacing:-.05em;line-height:1.12;max-width:720px;margin:12px 0}.lead{max-width:650px;color:var(--muted);font-size:1.03rem}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.feature{background:white;border:1px solid var(--line);border-radius:19px;padding:30px;display:flex;flex-direction:column;min-height:300px;transition:border .15s}.feature:hover{border-color:#b1d48e}.feature .symbol{width:58px;height:58px;border-radius:15px;background:#eaf4e3;display:grid;place-items:center;font-size:1.65rem;margin-bottom:24px}.feature:nth-child(2) .symbol{background:#fff0e1}.feature:nth-child(3) .symbol{background:#e7eefa}.feature h3{font-size:1.32rem;letter-spacing:-.03em;margin:0 0 9px}.feature p{color:var(--muted);font-size:.91rem;margin:0 0 21px;flex:1}.textlink{font-weight:790;color:#174d3f;font-size:.9rem}.textlink:hover{text-decoration:underline}
.split{background:#edf2eb}.splitinner{display:grid;grid-template-columns:.98fr 1.02fr;gap:75px;align-items:center}.lessongrid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.lessoncard{background:white;border:1px solid #d6e0d5;border-radius:15px;padding:20px;min-height:138px}.lessoncard .square{font-size:1.65rem}.lessoncard strong{display:block;margin:8px 0 3px;font-size:.96rem}.lessoncard small{color:#577067}.lessoncard:nth-child(2){transform:translateY(22px)}.lessoncard:nth-child(4){transform:translateY(22px)}.kicker{background:#dff2d7;display:inline-block;padding:7px 10px;border-radius:8px;color:#30583b;font-size:.75rem;font-weight:820}.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:23px;counter-reset:step}.step{position:relative;padding:23px 26px;background:white;border:1px solid var(--line);border-radius:16px}.step:before{counter-increment:step;content:"0" counter(step);display:grid;place-items:center;font-size:.83rem;font-weight:850;background:#dff1d6;width:42px;height:42px;border-radius:10px}.step h3{margin:18px 0 7px;font-size:1.08rem}.step p{margin:0;color:var(--muted);font-size:.9rem}
.quote{background:var(--navy);color:white;padding:74px 0}.quotebox{display:flex;justify-content:space-between;align-items:center;gap:32px}.quote h2{font-size:clamp(2rem,3.8vw,3.5rem);letter-spacing:-.05em;margin:11px 0;line-height:1.1;max-width:690px}.quote p{color:#bbcbca;margin:0}
footer{background:#07141c;color:#d3dedc;padding:44px 0}.foot{display:flex;justify-content:space-between;gap:32px;align-items:flex-start}.foot p{color:#9dafb2;font-size:.85rem;max-width:400px;margin:10px 0}.foot-links{display:flex;gap:24px;flex-wrap:wrap;font-size:.84rem}.copyright{border-top:1px solid #31414a;padding-top:18px;color:#9dadb0;font-size:.8rem;margin-top:33px}
.mobile-menu{display:none}
@media(max-width:900px){.heroinner{grid-template-columns:1fr;padding:62px 0 70px}.illustration{min-height:350px}.orbit{top:-30px}.orbit.two{top:20px}.cards{grid-template-columns:repeat(2,1fr)}.cards .feature:last-child{grid-column:span 2}.splitinner{gap:35px}.navlinks{gap:14px}}
@media(max-width:680px){.shell{padding:0 19px}.nav{min-height:68px}.navlinks{display:none}.actions .button.light{display:none}.mobile-menu{display:block}.mobile-menu summary{font-size:.8rem;font-weight:800;list-style:none;cursor:pointer;border:1px solid #dae2dc;border-radius:9px;padding:9px}.mobile-menu[open] nav{position:absolute;right:16px;top:60px;background:white;box-shadow:0 12px 25px #0002;padding:18px;border:1px solid var(--line);border-radius:12px;display:grid;gap:13px;min-width:210px}.heroinner{padding:58px 0}.hero h1{font-size:clamp(2.65rem,11vw,4.3rem)}.illustration{min-height:330px}.orbit{width:290px;height:290px;top:12px}.orbit.two{width:225px;height:225px;top:45px}.showcase{padding:19px;width:92%}.illustration .float{right:0;bottom:3%}.statsinner{grid-template-columns:1fr;gap:13px}.stat strong{font-size:1.2rem}.section{padding:62px 0}.sectionhead{display:block}.cards,.steps,.splitinner{grid-template-columns:1fr}.cards .feature:last-child{grid-column:span 1}.feature{min-height:230px}.splitinner{gap:45px}.lessoncard:nth-child(2),.lessoncard:nth-child(4){transform:none}.quotebox{display:block}.quotebox .button{margin-top:24px}.foot{display:block}.foot-links{margin-top:22px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<header>
<div class="shell nav">
<a class="brand" href="{{ url_for('landing.home') }}" aria-label="TechDialect home"><span class="brandmark" aria-hidden="true">T</span><span>techdialect<span style="color:#538c46">.</span></span></a>
<nav class="navlinks" aria-label="Main navigation"><a href="#learning">Learning</a><a href="{{ url_for('stem.adults_index') }}">Adult Education</a><a href="{{ url_for('videos.index') }}">Tutorials</a><a href="#how">How it works</a></nav>
<div class="actions"><a class="button light" href="{{ url_for('login') }}">Sign in</a><a class="button dark" href="{{ url_for('stem.index') }}">Start learning <span aria-hidden="true">↗</span></a>
<details class="mobile-menu"><summary>Menu</summary><nav aria-label="Mobile navigation"><a href="#learning">Learning</a><a href="{{ url_for('stem.adults_index') }}">Adult education</a><a href="{{ url_for('videos.index') }}">Tutorials</a><a href="{{ url_for('login') }}">Sign in</a><a href="{{ url_for('register') }}">Join as contributor</a></nav></details></div>
</div></header>
<main>
<section class="hero"><div class="shell heroinner">
<div><span class="label inverse">Technology for every Nigerian</span>
<h1>Big ideas.<br>Every <em>language.</em></h1>
<p>Science, digital skills and everyday technology explained simply. Learn at your pace, discover Nigerian-language content, and help build knowledge everyone can understand.</p>
<div class="herobuttons"><a class="button lime" href="{{ url_for('stem.index') }}">Explore free lessons <span aria-hidden="true">↗</span></a>
<a class="button light" href="{{ url_for('stem.adults_index') }}">Technology for adults</a></div>
<p class="subnote">20 school STEM lessons · 12 practical adult lessons · Community-reviewed translations</p></div>
<div class="illustration" aria-label="Example of TechDialect learning cards"><div class="orbit"></div><div class="orbit two"></div><span class="spark" aria-hidden="true">✦</span>
<div class="showcase"><div class="mini-top"><span>✳ &nbsp; LEARN A CONCEPT</span><span><i class="dot"></i>Start with English</span></div>
<h2>Technology, made familiar.</h2><p>Learn the idea first. Discover reviewed local-language lessons as they are published.</p>
<div class="translation"><small>STEM · SCHOOL</small><strong>How plants make food →</strong><a class="textlink" href="{{ url_for('stem.lesson_detail', slug='plant-food') }}">Explore photosynthesis</a></div>
<div class="translation"><small>DIGITAL SKILLS · ADULTS</small><strong>Using your smartphone →</strong><a class="textlink" href="{{ url_for('stem.lesson_detail', slug='smartphone-basics') }}">Learn step by step</a></div>
</div><div class="float">Tiv · Hausa · Yoruba · Igbo · Pidgin</div></div>
</div></section>
<section class="stats" aria-label="Learning areas"><div class="shell statsinner">
<div class="stat"><span class="staticon" aria-hidden="true">◉</span><div><strong>20</strong> <span>school STEM starter lessons</span></div></div>
<div class="stat"><span class="staticon" aria-hidden="true">▤</span><div><strong>12</strong> <span>practical adult digital lessons</span></div></div>
<div class="stat"><span class="staticon" aria-hidden="true">◇</span><div><strong>5</strong> <span>starter Nigerian languages supported</span></div></div>
</div></section>
<section class="section" id="learning"><div class="shell">
<div class="sectionhead"><div><span class="label">Learning paths</span><h2>Useful learning for wherever you are.</h2><p class="lead">Whether you're studying science at school, using a smartphone for the first time or building a business, there's a practical place to start.</p></div></div>
<div class="cards"><article class="feature"><span class="symbol" aria-hidden="true">✳</span><h3>School STEM</h3><p>Explore Primary 4, Primary 5 and JSS 1 science, computing and mathematics. Every lesson has an explanation and a practice quiz.</p><a class="textlink" href="{{ url_for('stem.index') }}">Explore STEM lessons ↗</a></article>
<article class="feature"><span class="symbol" aria-hidden="true">▣</span><h3>Adult tech skills</h3><p>Learn smartphones, online safety, digital payments, documents, spreadsheets and AI at a beginner-friendly pace.</p><a class="textlink" href="{{ url_for('stem.adults_index') }}">Explore Adult Education ↗</a></article>
<article class="feature"><span class="symbol" aria-hidden="true">▷</span><h3>Video tutorials</h3><p>Watch curated tutorials linked to lessons, including videos from TechDialect's educators. YouTube loads only when you select Play.</p><a class="textlink" href="{{ url_for('videos.index') }}">Browse tutorials ↗</a></article></div>
</div></section>
<section class="section split"><div class="shell splitinner">
<div class="lessongrid" aria-label="Example learning topics"><div class="lessoncard"><span class="square" aria-hidden="true">☼</span><strong>Understanding the water cycle</strong><small>School STEM</small></div>
<div class="lessoncard"><span class="square" aria-hidden="true">⌕</span><strong>Staying safe online</strong><small>Adult digital skills</small></div>
<div class="lessoncard"><span class="square" aria-hidden="true">▦</span><strong>Budget with spreadsheets</strong><small>Work and business</small></div>
<div class="lessoncard"><span class="square" aria-hidden="true">◎</span><strong>Digital confidence</strong><small>Everyday technology</small></div></div>
<div><span class="label">Learn at your pace</span><h2>Clear explanations. Real-world practice.</h2>
<p class="lead">Every starter lesson focuses on one idea, a practical example and a short question. Your progress stays on your device. Previously opened learning pages can work offline.</p>
<p class="lead">Language editions are only presented as verified after human technical and language review. We don't pretend every lesson already has every translation.</p>
<a class="button dark" href="{{ url_for('stem.adults_index') }}">Explore practical lessons ↗</a></div></div></section>
<section class="section" id="how"><div class="shell"><span class="label">How TechDialect works</span><h2>Learning is better when it makes sense.</h2>
<div class="steps"><article class="step"><h3>Choose what to learn</h3><p>Pick a school level, an adult technology pathway or a video tutorial that meets your needs.</p></article>
<article class="step"><h3>Practice with confidence</h3><p>Follow the explanation, try an exercise and revisit saved lessons offline.</p></article>
<article class="step"><h3>Grow local-language knowledge</h3><p>Contributors prepare community-language editions. Specialists review accuracy before publication.</p></article></div></div></section>
<section class="quote"><div class="shell quotebox"><div><span class="label inverse">Become a contributor</span><h2>Help make useful knowledge feel like home.</h2><p>Speak a Nigerian language? Help translate and review lessons with your community.</p></div><a class="button lime" href="{{ url_for('register') }}">Join TechDialect ↗</a></div></section>
</main>
<footer><div class="shell"><div class="foot"><div><a class="brand" href="{{ url_for('landing.home') }}"><span class="brandmark" aria-hidden="true">T</span><span>techdialect.</span></a>
<p>Technology and digital skills, made accessible through learning and the richness of Nigerian languages.</p></div>
<nav class="foot-links" aria-label="Footer navigation"><a href="{{ url_for('stem.index') }}">School STEM</a><a href="{{ url_for('stem.adults_index') }}">Adult learning</a>
<a href="{{ url_for('videos.index') }}">Tutorials</a><a href="{{ url_for('login') }}">Contributor login</a><a href="{{ url_for('register') }}">Register</a></nav></div>
<div class="copyright">© TechDialect · An initiative of Simeon's Laboratories and Co Technologies Ltd · Technologia Omnibus.</div></div></footer>
</body></html>"""

@landing_bp.get("/")
def home():
    return render_template_string(PAGE)
