"""Vercel's documented Flask WSGI entry point.

Production Vercel requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.
Never store private application data in local SQLite on serverless functions.
"""
from smart_translation_system import app
