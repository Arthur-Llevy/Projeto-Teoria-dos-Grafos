from flask import Flask, render_template
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
    courses = graph_db.get_nodes_by_type("curso")
    disciplines = graph_db.get_nodes_by_type("disciplina")
    schedules = graph_db.get_nodes_by_type("horario")
    professors = graph_db.get_nodes_by_type("professor")
    rooms = graph_db.get_nodes_by_type("sala")
    nodes_by_id = graph_db.nodes
    schedule_entries = []

    for schedule in schedules:
        schedule_id = schedule["id"]
        discipline = next((nodes_by_id[edge["from"]] for edge in graph_db.edges
            if edge["to"] == schedule_id and edge["relation"] == "tem_horario"
            and nodes_by_id[edge["from"]]["type"] == "disciplina"), None)
        if discipline is None:
            continue
        discipline_id = discipline["id"]
        professor = next((nodes_by_id[edge["from"]] for edge in graph_db.edges
            if edge["to"] == discipline_id and edge["relation"] == "ministrada_por"
            and nodes_by_id[edge["from"]]["type"] == "professor"), None)
        room = next((nodes_by_id[edge["to"]] for edge in graph_db.edges
            if edge["from"] == discipline_id and edge["relation"] == "tem_horario"
            and nodes_by_id[edge["to"]]["type"] == "sala"), None)
        schedule_entries.append({
            "day": schedule["properties"]["dia"],
            "start": schedule["properties"]["hora_inicio"],
            "end": schedule["properties"]["hora_fim"],
            "period": schedule["properties"]["periodo"],
            "discipline": discipline["properties"],
            "professor": professor["properties"] if professor else {},
            "room": room["properties"] if room else {},
        })

    course = courses[0]["properties"] if courses else {}
    period = schedule_entries[0]["period"] if schedule_entries else "Sem período"
    return render_template("index.html", course=course, period=period,
        entries=schedule_entries, discipline_count=len(disciplines),
        professor_count=len(professors), room_count=len(rooms))
