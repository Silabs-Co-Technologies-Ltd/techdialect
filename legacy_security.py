"""Request protection for the legacy Flask interface.

The current translation UI uses rendered inline HTML forms, so existing forms
get an anti-CSRF hidden field in the outgoing HTML rather than requiring a risky
manual update to every legacy template. Browser JSON calls use X-CSRF-Token.

Quota storage is the current persistent SQLite database. Reverse proxies must
configure REMOTE_ADDR correctly; arbitrary X-Forwarded-For headers are ignored.
Move the counters to shared storage when switching to horizontally scaled
production infrastructure.
"""
import hashlib
import hmac
import re
import secrets
import time

from flask import abort, jsonify, request, session

POST_FORM = re.compile(
    r"""<form\b(?=[^>]*\bmethod\s*=\s*["']?post(?:["'\s>]))[^>]*>""",
    re.IGNORECASE,
)

# Requests allowed in each 60-second window. Keep API inference and logins cheap.
LIMITS = {
    ("GET", "/api/translate"): 30,
    ("POST", "/api/translate_article"): 6,
    ("POST", "/translate_article"): 6,
    ("POST", "/login"): 12,
    ("POST", "/register"): 6,
    ("POST", "/translate"): 30,
}
WINDOW_SECONDS = 60


def csrf_token():
    value = session.get("_legacy_csrf")
    if not value:
        value = secrets.token_urlsafe(32)
        session["_legacy_csrf"] = value
    return value


def _valid_csrf():
    candidate = request.headers.get("X-CSRF-Token", "")
    if not candidate and request.mimetype != "application/json":
        candidate = request.form.get("csrf_token", "")
    expected = session.get("_legacy_csrf", "")
    return bool(candidate and expected and hmac.compare_digest(
        str(candidate), str(expected)))


def _limited(db, secret, limit, window_seconds=WINDOW_SECONDS):
    # Hash addresses before persistence to avoid recording raw client IPs.
    address = request.remote_addr or "unknown"
    identifier = hmac.new(
        secret.encode("utf-8"), (address + "|" + request.path).encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    now = int(time.time())
    current = now // window_seconds
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS request_quotas (
        identity TEXT NOT NULL,
        window_number INTEGER NOT NULL,
        hits INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (identity,window_number)
    )""")
    conn.execute("""INSERT INTO request_quotas(identity,window_number,hits)
        VALUES (?,?,1)
        ON CONFLICT(identity,window_number) DO UPDATE SET hits=hits+1
    """, (identifier, current))
    count = conn.execute(
        "SELECT hits FROM request_quotas WHERE identity=? AND window_number=?",
        (identifier, current)
    ).fetchone()[0]
    if count == 1 and now % 60 == 0:
        conn.execute(
            "DELETE FROM request_quotas WHERE window_number < ?",
            (current - 2,)
        )
    conn.commit()
    return count > limit, window_seconds - now % window_seconds


def install_legacy_security(app, get_database):
    @app.before_request
    def secure_legacy_requests():
        # New blueprints have their own CSRF guards.
        if request.blueprint is not None:
            return None

        limit = LIMITS.get((request.method, request.path))
        if limit is not None:
            denied, retry = _limited(
                get_database, app.secret_key, limit
            )
            if denied:
                response = jsonify({
                    "error": "Rate limit exceeded. Please try again shortly."
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry)
                return response

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            # Public stateless JSON endpoint: session CSRF tokens are not needed.
            # The API is quota-limited above and must not use cookie auth.
            if request.path == "/api/translate_article":
                return None
            if not _valid_csrf():
                abort(400, description="Missing or invalid CSRF token")

        return None

    @app.after_request
    def secure_legacy_responses(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")

        if (request.blueprint is not None or request.method != "GET" or
                response.mimetype != "text/html" or response.is_streamed or
                response.status_code != 200):
            return response

        text = response.get_data(as_text=True)
        if "<form" not in text.lower() and "<head" not in text.lower():
            return response

        token = csrf_token()
        # The token is URL-safe text, so no HTML escaping is required.
        hidden = '<input type="hidden" name="csrf_token" value="' + token + '">'
        text = POST_FORM.sub(lambda match: match.group(0) + hidden, text)
        text = re.sub(
            r"<head\b[^>]*>",
            lambda match: match.group(0) +
            '<meta name="csrf-token" content="' + token + '">',
            text, count=1, flags=re.IGNORECASE,
        )
        response.set_data(text)
        response.headers["Cache-Control"] = "private, no-store"
        return response

    return app
