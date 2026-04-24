# Techdialect Translation Engine

**technologia omnibus** — Technology for all.

A community-powered Nigerian language dataset platform that translates English into Nigerian local languages using AI, while simultaneously building the datasets that make those translations better over time.

**Live site:** [silabs.pythonanywhere.com](https://silabs.pythonanywhere.com)  
**Built by:** [Silabs Technology Ltd.](https://github.com/Silabs)  
**License:** MIT

---

## What is Techdialect?

Techdialect solves two problems at once:

1. **Useful today** — Anyone can translate English words, sentences, and full articles into Nigerian languages right now, using AI
2. **Building tomorrow** — Every translation saved by users trains the AI to get better, creating a self-improving dataset that grows with every use

The more people use it, the smarter it gets — for everyone.

---

## Supported Languages

| Language | NLLB-200 Code | Status |
|---|---|---|
| Tiv | `tiv_Latn` | ✅ Live |
| Yoruba | `yor_Latn` | ✅ Live |
| Hausa | `hau_Arab` | ✅ Live |
| Igbo | `ibo_Latn` | ✅ Live |
| Nigerian Pidgin | `pcm_Latn` | ✅ Live |

Any user can propose additional languages. Admins approve them and they go live instantly.

---

## Features

### For Users
- **Quick Entry** — Add English ↔ local language pairs with `Ctrl+Enter` speed
- **AI Translation** — Powered by Facebook's NLLB-200 model via HuggingFace API
- **Article Translation** — Paste full paragraphs or articles, get full translation
- **Fuzzy Matching** — Finds close matches even when exact words aren't in the database
- **Contributor Badges** — Earn badges as you grow your contribution count
- **Coverage Dashboard** — See which categories need more words
- **CSV Bulk Upload** — Import hundreds of translations at once
- **CSV Export** — Download the full dataset for any language

### For Admins
- **User approval system** — New registrations require admin approval before access
- **Language proposals** — Users propose new languages; admins approve
- **Message inbox** — Users can send messages to admin; weekly export and cleanup
- **Contribution stats** — See who is contributing and how much
- **Full user management** — View, approve, or remove users

### API Endpoints
```
GET  /api/translate?text=hello&lang=Tiv
GET  /api/languages
GET  /api/stats
GET  /api/coverage?lang=Tiv
POST /api/translate_article   { "text": "...", "lang": "Tiv" }
```

---

## Badge System

Contributors earn badges based on their total number of translations saved:

| Badge | Level | Contributions |
|---|---|---|
| 🌱 | Seed | 1 – 9 |
| 🥉 | Bronze | 10 – 49 |
| 🥈 | Silver | 50 – 99 |
| 🥇 | Gold | 100 – 499 |
| 💎 | Platinum | 500 – 999 |
| 🏆 | Legend | 1,000+ |

Each badge includes a shareable card at `/badge/<username>` showing the contributor's name, level, count, and language contributions.

---

## How Translation Works

```
User types English word
        │
        ▼
Tier 1: Exact database match?  ──YES──▶  Return stored translation
        │ NO
        ▼
Tier 2: Fuzzy match (>55%)?   ──YES──▶  Return closest match
        │ NO
        ▼
Tier 3: HuggingFace AI call   ──OK──▶   Return AI translation + offer to save
        │ FAIL
        ▼
Tier 4: Not found — prompt user to add manually
```

Every AI translation that gets saved becomes a training example for the next query — this is the flywheel that makes the system self-improving.

---

## Quick Start (Local Development)

### Requirements
- Python 3.10+
- pip

### Installation

```bash
# Clone the repo
git clone https://github.com/Silabs/techdialect.git
cd techdialect

# Install dependencies
pip install flask python-dotenv requests werkzeug

# Create .env file
echo "SECRET_KEY=your-secret-key-here" > .env
echo "HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx" >> .env
echo "DAILY_GOAL=20" >> .env

# Run
python smart_translation_system.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

Default admin login: `Silabstechdialect` / `Techdialect@2024`  
**Change the password immediately after first login.**

### Getting a HuggingFace Token (free)
1. Go to [huggingface.co](https://huggingface.co) and create a free account
2. Click your avatar → Settings → Access Tokens → New Token
3. Role: **Read**, give it any name, copy the token
4. Add to `.env` as `HF_TOKEN=hf_...`

Without `HF_TOKEN`, the system still works using exact and fuzzy database matching only.

---

## PythonAnywhere Deployment

### Step 1 — Upload the file
Dashboard → Files → upload `smart_translation_system.py` to `/home/<yourusername>/`

### Step 2 — Create a Web App
Web tab → Add a new web app → Manual configuration → Python 3.10

### Step 3 — Set the WSGI file
Click the WSGI file link and replace all content with:

```python
import sys
import os

sys.path.insert(0, '/home/<yourusername>')

os.environ['SECRET_KEY'] = 'your-secret-key'
os.environ['HF_TOKEN']   = 'hf_xxxxxxxxxxxxxxxxxxxx'
os.environ['DAILY_GOAL'] = '20'

from smart_translation_system import app as application
```

### Step 4 — Install dependencies
Open a Bash console and run:
```bash
pip install --user flask python-dotenv requests werkzeug
```

### Step 5 — Reload
Go to the Web tab and click **Reload**.

---

## Database Schema

```sql
users        (id, username, email, password_hash, role, approved, created_at)
languages    (id, name, nllb_code, added_by, approved, created_at)
translations (id, english_text, local_text, target_lang, category, source, added_by, created_at)
daily_log    (log_date, count)
messages     (id, user_id, subject, body, created_at, read_at)
```

---

## CSV Format for Bulk Upload

```csv
english_text,local_text,category,target_lang
Good morning,,,Tiv
Hello,,,Yoruba
```

- `target_lang` defaults to the currently selected language if omitted
- `category` defaults to `General` if omitted
- Duplicate `(english_text, target_lang)` pairs are silently skipped

---

## Contributing

We welcome contributions — especially:

- **Translations** — Add words in your language via the website
- **New languages** — Propose languages not yet in the system
- **Bug fixes** — Open an issue or pull request
- **Feature improvements** — See the roadmap below

### For developers

```bash
# Fork the repo on GitHub
# Make your changes
# Test locally
python smart_translation_system.py

# Submit a pull request
```

All code currently lives in a single file (`smart_translation_system.py`) for ease of deployment on basic hosts like PythonAnywhere. However, see [UPGRADE_PLAN.md](UPGRADE_PLAN.md) for our roadmap to a modular, high-scale architecture.

### Code structure

```
smart_translation_system.py
├── CONFIGURATION          (env vars, constants)
├── FLASK APP INIT
├── DATABASE LAYER         (schema, helpers, CRUD)
├── USER / AUTH HELPERS    (login, decorators)
├── TRANSLATION ENGINE     (3-tier: exact → fuzzy → AI)
├── ARTICLE TRANSLATION    (chunking + stitching)
├── BADGE SYSTEM           (levels + shareable cards)
├── HTML TEMPLATES         (Auth, Main, Admin, Badge, Messages)
├── RENDER HELPER
├── AUTH ROUTES            (/login, /register, /logout)
├── ADMIN ROUTES           (/admin, /admin/messages, etc.)
├── MAIN APP ROUTES        (/, /translate, /add, /save, etc.)
├── REST API               (/api/translate, /api/stats, etc.)
└── ENTRY POINT
```

---

## Roadmap

### Phase 1 — Now (Tiv focus)
- [x] Core translation engine (exact + fuzzy + AI)
- [x] Multi-user with admin approval
- [x] Article/paragraph translation
- [x] User-managed languages
- [x] Contributor badges
- [x] User-to-admin messaging
- [ ] 1,000 Tiv word dataset
- [x] Repository Audit & Cleanup (Removed duplicates, optimized badge logic)
- [x] Strategic Upgrade Plan for ₦10M Tech Challenge

### Phase 2 — 6 Months
- [ ] Expand all 5 launched languages to full coverage
- [ ] STEM terminology packs
- [ ] Mobile-optimised PWA
- [ ] Email notifications for approvals

### Phase 3 — 1 Year
- [ ] 50 Nigerian languages
- [ ] School/classroom mode
- [ ] Offline mobile app
- [ ] API rate limiting + public API keys
- [ ] PostgreSQL migration for scale

---

## Architecture Notes (for contributors)

**Why a single file?**  
PythonAnywhere free tier works best with a single importable module. When the project moves to a paid host, the single file splits cleanly into:
- `translation_service.py` — the 3-tier engine
- `auth.py` — user management
- `api.py` — REST endpoints
- `templates/` — HTML templates

**Why SQLite?**  
Zero configuration, works on any host, handles hundreds of concurrent users fine for this use case. The `PRAGMA journal_mode=WAL` setting handles concurrency on PythonAnywhere. Migration to PostgreSQL requires changing only `get_db()` and `init_db()`.

**Why NLLB-200?**  
Facebook's NLLB-200 (No Language Left Behind) is specifically trained for low-resource languages including all major Nigerian languages. It supports 200 languages with a single model, making it ideal for a platform covering multiple Nigerian languages.

---

## Licence

MIT Licence — see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. Attribution appreciated.

---

## Contact

- **Website:** [silabs.pythonanywhere.com](https://silabs.pythonanywhere.com)
- **GitHub:** [github.com/Silabs](https://github.com/Silabs)
- **Platform:** Use the Contact Admin form inside the application

---

*Techdialect — technologia omnibus*  
*Built with ❤️ for Nigerian language communities*
