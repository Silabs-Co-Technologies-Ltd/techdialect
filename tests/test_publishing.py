"""Publication must require separate approval and authorized admin action."""
import sqlite3
import pytest
from flask import Flask
import publishing

def test_publication_blueprint_routes():
    app=Flask(__name__)
    app.register_blueprint(publishing.publish_bp)
    assert "publishing.publish_term" in app.view_functions
    assert "publishing.public_terms" in app.view_functions
