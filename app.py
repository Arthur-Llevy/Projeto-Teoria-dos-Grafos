from flask import Flask
from src.api.health import health_bp
from src.graph.graph_db import GraphDatabase
from pathlib import Path
import os

app = Flask(__name__)

# Carrega o grafo de exemplo uma vez por processo e mantém os nós e arestas
# na memória enquanto a aplicação estiver em execução.
graph_db = GraphDatabase()
sample_graph = Path(__file__).resolve().parent / "src" / "graph" / "sample_graph_data.json"
if not graph_db.load(str(sample_graph)):
    raise RuntimeError(f"Não foi possível carregar o grafo inicial: {sample_graph}")
app.extensions["graph_db"] = graph_db

app.register_blueprint(health_bp)

@app.route("/")
def index():
    return "Welcome to the course management system."
