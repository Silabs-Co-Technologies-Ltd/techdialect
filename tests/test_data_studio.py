from flask import Flask
from data_studio import data_bp

def test_blueprint_registration():
    app = Flask(__name__)
    app.secret_key = "test-only"
    app.register_blueprint(data_bp)
    assert "data.index" in app.view_functions
    assert "data.submit" in app.view_functions
    assert "data.review" in app.view_functions
