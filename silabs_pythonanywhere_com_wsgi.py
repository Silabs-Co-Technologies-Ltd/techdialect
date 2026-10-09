import sys
import os
import logging

# ── DEPLOYMENT CONFIGURATION ──────────────────────────────────────────────────
# Set the path to your application directory
sys.path.insert(0, '/home/Silabs')

# ── ENVIRONMENT DEFAULTS ──────────────────────────────────────────────────────
# Ensuring production-ready defaults if not set in the environment
os.environ.setdefault('SECRET_KEY', 'techdialect-production-key-2024-secure')
os.environ.setdefault('DAILY_GOAL', '20')

# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

try:
    from smart_translation_system import app as application
    logging.info("Techdialect Engine loaded successfully.")
except Exception as e:
    logging.error(f"CRITICAL: Failed to load Techdialect Engine: {e}")
    raise
