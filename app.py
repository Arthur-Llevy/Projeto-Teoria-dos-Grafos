from flask import Flask, redirect, render_template, request, url_for
from src.api.health import health_bp
from src.api.graph import graph_bp               
from src.graph.graph_db import GraphDatabase
from src.graph.sqlite_loader import load_from_sqlite  
from pathlib import Path
import sqlite3

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "grade_horaria.db"
SAMPLE_GRAPH = BASE_DIR / "src" / "graph" / "sample_graph_data.json"

graph_db = GraphDatabase()

if DB_PATH.exists():
    load_from_sqlite(graph_db, DB_PATH)
    app.logger.info("Grafo carregado do SQLite: %s", DB_PATH)
elif not graph_db.load(str(SAMPLE_GRAPH)):
    raise RuntimeError(f"Não foi possível carregar o grafo: {SAMPLE_GRAPH}")

app.extensions["graph_db"] = graph_db

app.register_blueprint(health_bp)
app.register_blueprint(graph_bp)

@app.route("/")
def index():
    database_path = Path(__file__).resolve().parent / "grade_horaria.db"
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    rows = connection.execute("""
        SELECT g.gra_semestre, h.hor_dia_semana, h.hor_hora_inicio,
               h.hor_hora_fim, a.alo_id, d.dis_id, d.dis_codigo,
               d.dis_descricao, d.dis_periodo, d.dis_carga_horaria,
               d.dis_eh_eletiva, p.pro_id, p.pro_nome, s.sal_descricao
        FROM gra_grade_horaria AS g
        JOIN alo_alocacao AS a ON a.alo_id = g.alo_id
        JOIN dis_disciplina AS d ON d.dis_id = a.dis_id
        JOIN hor_horario AS h ON h.hor_id = g.hor_id
        LEFT JOIN pro_professor AS p ON p.pro_id = a.pro_id
        LEFT JOIN sal_sala AS s ON s.sal_id = g.sal_id
        ORDER BY CASE h.hor_dia_semana
            WHEN 'Segunda' THEN 1 WHEN 'Terça' THEN 2 WHEN 'Quarta' THEN 3
            WHEN 'Quinta' THEN 4 WHEN 'Sexta' THEN 5 END,
            h.hor_hora_inicio, d.dis_descricao
    """).fetchall()
    disciplines = connection.execute("""
         SELECT d.dis_id, d.dis_codigo, d.dis_descricao, d.dis_periodo,
             d.dis_carga_horaria, d.dis_eh_eletiva, p.pro_id AS professor_id,
               p.pro_nome AS professor
        FROM dis_disciplina AS d
        LEFT JOIN alo_alocacao AS a ON a.dis_id = d.dis_id
        LEFT JOIN pro_professor AS p ON p.pro_id = a.pro_id
        ORDER BY d.dis_descricao
    """).fetchall()
    professors = connection.execute(
        "SELECT pro_id, pro_nome FROM pro_professor ORDER BY pro_nome"
    ).fetchall()
    course = connection.execute(
        "SELECT cur_descricao FROM cur_curso ORDER BY cur_id LIMIT 1"
    ).fetchone()
    room_count = connection.execute(
        "SELECT COUNT(*) FROM sal_sala"
    ).fetchone()[0]
    time_slots = connection.execute("""
        SELECT hor_hora_inicio AS start, hor_hora_fim AS end
        FROM hor_horario
        GROUP BY hor_hora_inicio, hor_hora_fim
        ORDER BY hor_hora_inicio
    """).fetchall()
    connection.close()

    meetings = {}
    for row in rows:
        meeting_key = (
            row["gra_semestre"], row["alo_id"], row["hor_dia_semana"],
            row["sal_descricao"],
        )
        meetings.setdefault(meeting_key, []).append(row)

    schedule_entries = []
    for meeting_rows in meetings.values():
        meeting_rows.sort(key=lambda row: row["hor_hora_inicio"])
        first = meeting_rows[0]
        blocks = []
        for row in meeting_rows:
            if blocks and blocks[-1]["end"] == row["hor_hora_inicio"]:
                blocks[-1]["end"] = row["hor_hora_fim"]
                blocks[-1]["span"] += 1
            else:
                blocks.append({
                    "start": row["hor_hora_inicio"],
                    "end": row["hor_hora_fim"],
                    "span": 1,
                })

        for block in blocks:
            schedule_entries.append({
                "day": first["hor_dia_semana"],
                "start": block["start"],
                "end": block["end"],
                "row": next(i for i, slot in enumerate(time_slots)
                            if slot["start"] == block["start"]),
                "span": block["span"],
                "period": first["dis_periodo"],
                "discipline": {
                    "id": first["dis_id"], "codigo": first["dis_codigo"],
                    "nome": first["dis_descricao"], "periodo": first["dis_periodo"],
                    "carga_horaria": first["dis_carga_horaria"],
                    "eh_eletiva": bool(first["dis_eh_eletiva"]),
                },
                "professor": {
                    "id": first["pro_id"],
                    "nome": first["pro_nome"] or "Professor não informado",
                },
                "room": {"nome": first["sal_descricao"] or "Sala não informada"},
                "color": first["dis_id"] % 6,
            })

    days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    day_entries = {day: [] for day in days}
    for entry in schedule_entries:
        day_entries[entry["day"]].append(entry)
    for entries_for_day in day_entries.values():
        entries_by_start = {}
        for entry in entries_for_day:
            entries_by_start.setdefault(entry["start"], []).append(entry)
        for entries_at_start in entries_by_start.values():
            for lane, entry in enumerate(entries_at_start):
                entry["lane"] = lane
                entry["lane_count"] = len(entries_at_start)

    day_counts = {
        day: sum(1 for entry in schedule_entries if entry["day"] == day)
        for day in days
    }

    return render_template(
        "index.html", course={"nome": course["cur_descricao"] if course else "Curso"},
        entries=schedule_entries, disciplines=disciplines, professors=professors,
        days=days, time_slots=time_slots, day_counts=day_counts,
        discipline_count=len(disciplines), professor_count=len(professors),
        room_count=room_count,
        discipline_created=request.args.get("cadastro") == "sucesso",
    )


@app.route("/disciplinas/nova", methods=["GET", "POST"])
def nova_disciplina():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    courses = connection.execute(
        "SELECT cur_id, cur_descricao FROM cur_curso ORDER BY cur_descricao"
    ).fetchall()
    errors = []

    if request.method == "POST":
        values = request.form
        code = values.get("codigo", "").strip()
        description = values.get("descricao", "").strip()
        try:
            period = int(values.get("periodo", ""))
            if period < 1:
                raise ValueError
        except ValueError:
            period = None
            errors.append("Informe um período válido, maior que zero.")
        try:
            workload = int(values.get("carga_horaria", ""))
            if workload < 1:
                raise ValueError
        except ValueError:
            workload = None
            errors.append("Informe uma carga horária válida, maior que zero.")
        try:
            course_id = int(values.get("curso_id", ""))
        except ValueError:
            course_id = None

        if not code:
            errors.append("Informe o código da disciplina.")
        if not description:
            errors.append("Informe o nome da disciplina.")
        if len(code) > 20:
            errors.append("O código deve ter no máximo 20 caracteres.")
        if len(description) > 100:
            errors.append("O nome deve ter no máximo 100 caracteres.")
        if course_id not in {course["cur_id"] for course in courses}:
            errors.append("Selecione um curso válido.")

        duplicate = connection.execute(
            "SELECT 1 FROM dis_disciplina WHERE UPPER(dis_codigo) = UPPER(?)",
            (code,),
        ).fetchone()
        if code and duplicate:
            errors.append("Já existe uma disciplina com esse código.")

        if not errors:
            cursor = connection.execute(
                """INSERT INTO dis_disciplina
                   (dis_codigo, dis_descricao, dis_periodo, dis_carga_horaria,
                    dis_eh_eletiva, cur_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    description,
                    period,
                    workload,
                    int(values.get("eh_eletiva") == "1"),
                    course_id,
                ),
            )
            connection.commit()
            discipline_id = cursor.lastrowid
            graph = app.extensions["graph_db"]
            graph.add_node_with_id(
                node_id=f"disc:{discipline_id}",
                node_type="disciplina",
                properties={
                    "dis_id": discipline_id,
                    "codigo": code,
                    "descricao": description,
                    "periodo": period,
                    "carga_horaria": workload,
                    "eh_eletiva": values.get("eh_eletiva") == "1",
                    "cur_id": course_id,
                },
            )
            course_node_id = f"curso:{course_id}"
            if course_node_id in graph.nodes:
                graph.add_edge(
                    f"disc:{discipline_id}", course_node_id, "PERTENCE_A"
                )
            connection.close()
            return redirect(url_for("index", cadastro="sucesso"))

    else:
        values = {}

    connection.close()
    return render_template(
        "discipline_new.html", courses=courses, errors=errors, values=values
    )
