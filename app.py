from flask import Flask
from src.api.health import health_bp
import os

app = Flask(__name__)

app.register_blueprint(health_bp)

@app.route("/")
def index():
    return "Welcome to the course management system."
