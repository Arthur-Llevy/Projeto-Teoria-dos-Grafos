import hashlib
import json
import sqlite3
from collections import defaultdict
from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from src.database import GradeAlreadyExistsError
from src.graph.graph_db import GraphDatabase
from src.graph.sqlite_loader import load_from_sqlite
from src.graph.coloring import color_and_assign_slots

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")

def _g():
    return current_app.extensions["graph_db"]


def _generate_proposal():
    """Calculate assignments and enrich them with display data from SQLite."""
    database_path = current_app.extensions["grade_repository"].database_path
    graph = GraphDatabase()
    if not load_from_sqlite(graph, database_path):
        raise RuntimeError("Não foi possível carregar o grafo do SQLite.")

    assignments = color_and_assign_slots(graph)
    rows = []
    day_order = {
        "Segunda": 1,
        "Terça": 2,
        "Quarta": 3,
        "Quinta": 4,
        "Sexta": 5,
        "Sábado": 6,
        "Domingo": 7,
    }
    for vertex, result in assignments.items():
        allocation_node_id = vertex.split("#50min:", maxsplit=1)[0]
        allocation = graph.nodes[allocation_node_id]["properties"]
        discipline = graph.nodes.get(f"disc:{allocation.get('dis_id')}", {})
        professor = graph.nodes.get(f"prof:{allocation.get('pro_id')}", {})
        horario = graph.nodes.get(f"hor:{result['horario_id']}", {})
        discipline_properties = discipline.get("properties", {})
        professor_properties = professor.get("properties", {})
        horario_properties = horario.get("properties", {})
        preferred_slot_ids = {
            int(slot_id)
            for slot_id in professor_properties.get("horarios_preferidos", [])
        }
        day = horario_properties.get("dia_semana", "")
        start = horario_properties.get("hora_inicio", "")
        rows.append({
            "alo_id": int(allocation["alo_id"]),
            "aula": int(vertex.rsplit(":", maxsplit=1)[1]),
            "color": result["color"],
            "horario_id": int(result["horario_id"]),
            "dia": day,
            "hora_inicio": start,
            "hora_fim": horario_properties.get("hora_fim", ""),
            "disciplina": discipline_properties.get("descricao", "Disciplina"),
            "codigo": discipline_properties.get("codigo", ""),
            "periodo": discipline_properties.get("periodo", ""),
            "carga_horaria": discipline_properties.get("carga_horaria", ""),
            "professor": professor_properties.get("nome", "Professor não informado"),
            "preferencia": (
                "Atendida"
                if preferred_slot_ids and result["horario_id"] in preferred_slot_ids
                else "Fora da preferência"
                if preferred_slot_ids
                else "Sem preferência"
            ),
        })
    rows.sort(
        key=lambda row: (
            day_order.get(row["dia"], 99),
            row["hora_inicio"],
            row["disciplina"],
            row["alo_id"],
            row["aula"],
        )
    )
    return rows


def _proposal_fingerprint(semester, rows):
    assignments = sorted(
        ({"alo_id": row["alo_id"], "horario_id": row["horario_id"]}
         for row in rows),
        key=lambda item: (item["alo_id"], item["horario_id"]),
    )
    payload = json.dumps(
        {"semestre": semester, "alocacoes": assignments},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _render_proposal(semester, rows, error=None, status=200):
    repository = current_app.extensions["grade_repository"]
    return render_template(
        "grade_proposal.html",
        semester=semester,
        rows=rows,
        errors=[error] if error else [],
        existing_count=repository.count_for_semester(semester),
        fingerprint=_proposal_fingerprint(semester, rows),
    ), status


@graph_bp.get("/resumo")
def resumo():
    g = _g()
    por_tipo = defaultdict(int)
    for n in g.nodes.values():
        por_tipo[n["type"]] += 1
    por_rel = defaultdict(int)
    for e in g.edges:
        por_rel[e["relation"]] += 1
    return jsonify({
        "total_nos": len(g.nodes),
        "total_arestas": len(g.edges),
        "nos_por_tipo": dict(por_tipo),
        "arestas_por_relacao": dict(por_rel),
    })


@graph_bp.get("/professor/<int:pro_id>/horarios")
def horarios_professor(pro_id: int):
    g = _g()
    prof_id = f"prof:{pro_id}"
    if prof_id not in g.nodes:
        abort(404, f"Professor {pro_id} não encontrado")

    # professor --ALOCADO_EM--> alocacao --OCORRE_EM--> horario
    #                                   --MINISTRA--> disciplina
    #                                   --NA_SALA--> sala
    alocacoes = g.get_neighbors(prof_id, relation="ALOCADO_EM")

    resultado = []
    for alo in alocacoes:
        alo_id = alo["id"]
        disciplina = next(
            (n for n in g.get_neighbors(alo_id, relation="MINISTRA")),
            None,
        )
        sala = next(
            (n for n in g.get_neighbors(alo_id, relation="NA_SALA")),
            None,
        )
        for hor in g.get_neighbors(alo_id, relation="OCORRE_EM"):
            resultado.append({
                "alocacao_id": alo_id,
                "disciplina": disciplina["properties"] if disciplina else None,
                "sala": sala["properties"] if sala else None,
                "horario": hor["properties"],
            })

    resultado.sort(key=lambda x: (
        x["horario"]["dia_semana"], x["horario"]["hora_inicio"]
    ))
    return jsonify(resultado)


@graph_bp.get("/conflitos")
def conflitos():
    """Detecta (horário, sala) ocupados por mais de uma alocação."""
    g = _g()
    ocupacao = defaultdict(list)

    for alo in g.get_nodes_by_type("alocacao"):
        alo_id = alo["id"]
        horarios = g.get_neighbors(alo_id, relation="OCORRE_EM")
        salas = g.get_neighbors(alo_id, relation="NA_SALA")
        for h in horarios:
            for s in salas:
                ocupacao[(h["id"], s["id"])].append(alo_id)

    conflitos = []
    for (h_id, s_id), aloc_ids in ocupacao.items():
        if len(aloc_ids) <= 1:
            continue
        conflitos.append({
            "horario": g.nodes[h_id]["properties"],
            "sala": g.nodes[s_id]["properties"],
            "alocacoes": [
                {
                    "id": a_id,
                    "professor": next(
                        (n["properties"]["nome"]
                         for n in g.get_neighbors(a_id, relation="ALOCADO_EM")
                         if n["type"] == "professor"),
                        None,
                    ),
                    "disciplina": next(
                        (n["properties"]["descricao"]
                         for n in g.get_neighbors(a_id, relation="MINISTRA")),
                        None,
                    ),
                }
                for a_id in aloc_ids
            ],
        })
    return jsonify(conflitos)


@graph_bp.get("/disciplinas/<int:dis_id>")
def disciplina_detalhe(dis_id: int):
    g = _g()
    did = f"disc:{dis_id}"
    if did not in g.nodes:
        abort(404, f"Disciplina {dis_id} não encontrada")

    # Quem ministra essa disciplina? disc <-MINISTRA- alo <-ALOCADO_EM- prof
    alocacoes = [
        n for n in g.get_neighbors(did, relation="MINISTRA")
        if n["type"] == "alocacao"
    ]
    professores = []
    for alo in alocacoes:
        professores.extend(
            n["properties"] for n in g.get_neighbors(alo["id"], relation="ALOCADO_EM")
            if n["type"] == "professor"
        )

    return jsonify({
        "disciplina": g.nodes[did]["properties"],
        "professores": professores,
    })


@graph_bp.post("/reload")
def reload():
    g = GraphDatabase()
    db = current_app.extensions["grade_repository"].database_path
    ok = load_from_sqlite(g, db)
    if ok:
        current_app.extensions["graph_db"] = g
    return jsonify({"ok": ok}), (200 if ok else 500)


@graph_bp.post("/grade/colorir")
def color_grade():
    """Generate a timetable proposal from the application's SQLite database."""
    database_path = current_app.extensions["grade_repository"].database_path
    graph = GraphDatabase()
    if not load_from_sqlite(graph, database_path):
        return jsonify({"erro": "Não foi possível carregar o grafo do SQLite."}), 500

    try:
        assignments = color_and_assign_slots(graph)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 422

    by_allocation = defaultdict(list)
    for vertex, assignment in assignments.items():
        allocation_id = vertex.split("#50min:", maxsplit=1)[0]
        by_allocation[allocation_id].append({
            "aula": int(vertex.rsplit(":", maxsplit=1)[1]),
            **assignment,
        })

    current_app.extensions["graph_db"] = graph
    return jsonify({
        "ok": True,
        "alocacoes": [
            {
                "alo_id": graph.nodes[allocation_id]["properties"].get("alo_id"),
                "aulas": sorted(meetings, key=lambda item: item["aula"]),
            }
            for allocation_id, meetings in sorted(by_allocation.items())
        ],
    }), 200


@graph_bp.post("/grade/proposta")
def review_grade_proposal():
    """Generate an HTML preview without persisting its timetable rows."""
    semester = request.form.get("semestre", "").strip()
    if not semester or len(semester) > 10:
        return render_template(
            "grade_proposal.html",
            semester=semester,
            rows=[],
            errors=["Informe um semestre com até 10 caracteres."],
            existing_count=0,
            fingerprint="",
        ), 400

    try:
        rows = _generate_proposal()
    except ValueError as exc:
        return render_template(
            "grade_proposal.html",
            semester=semester,
            rows=[],
            errors=[str(exc)],
            existing_count=0,
            fingerprint="",
        ), 422
    except RuntimeError as exc:
        return render_template(
            "grade_proposal.html",
            semester=semester,
            rows=[],
            errors=[str(exc)],
            existing_count=0,
            fingerprint="",
        ), 500

    return _render_proposal(semester, rows)


@graph_bp.post("/grade/proposta/aceitar")
def accept_grade_proposal():
    """Recalculate the displayed proposal and persist it only after acceptance."""
    semester = request.form.get("semestre", "").strip()
    submitted_fingerprint = request.form.get("fingerprint", "")
    if not semester or len(semester) > 10:
        return redirect(url_for("index"))

    try:
        rows = _generate_proposal()
    except ValueError as exc:
        return render_template(
            "grade_proposal.html",
            semester=semester,
            rows=[],
            errors=[str(exc)],
            existing_count=0,
            fingerprint="",
        ), 422
    except RuntimeError as exc:
        return render_template(
            "grade_proposal.html",
            semester=semester,
            rows=[],
            errors=[str(exc)],
            existing_count=0,
            fingerprint="",
        ), 500

    current_fingerprint = _proposal_fingerprint(semester, rows)
    if submitted_fingerprint != current_fingerprint:
        return _render_proposal(
            semester,
            rows,
            error=(
                "Os dados mudaram desde a prévia. Confira a proposta atualizada "
                "antes de aceitá-la."
            ),
            status=409,
        )

    assignments = [
        {"alo_id": row["alo_id"], "horario_id": row["horario_id"]}
        for row in rows
    ]
    replace_existing = request.form.get("substituir") == "1"
    repository = current_app.extensions["grade_repository"]
    try:
        repository.replace_semester(
            semester,
            assignments,
            replace_existing=replace_existing,
        )
    except GradeAlreadyExistsError:
        return _render_proposal(
            semester,
            rows,
            error=(
                "Esse semestre já possui uma grade salva. Marque a opção para "
                "substituí-la e confirme novamente, ou descarte a proposta."
            ),
            status=409,
        )
    except (ValueError, sqlite3.Error):
        current_app.logger.exception("Falha ao aceitar a proposta da grade")
        return _render_proposal(
            semester,
            rows,
            error="Não foi possível salvar a proposta. Consulte o log da aplicação.",
            status=422,
        )

    updated_graph = GraphDatabase()
    if load_from_sqlite(updated_graph, repository.database_path):
        current_app.extensions["graph_db"] = updated_graph
    return redirect(
        url_for("index", grade_salva="1", semestre=semester), code=303
    )


@graph_bp.post("/grade/proposta/descartar")
def discard_grade_proposal():
    """Discard the browser preview; no proposal rows were persisted yet."""
    semester = request.form.get("semestre", "").strip()
    return redirect(
        url_for("index", proposta_descartada="1", semestre=semester), code=303
    )


@graph_bp.post("/grade/instanciar")
def instantiate_grade():
    """Persist timetable assignments supplied by the graph or frontend."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"erro": "Envie um objeto JSON com o campo semestre."}), 400

    semester = payload.get("semestre")
    if not isinstance(semester, str) or not semester.strip():
        return jsonify({"erro": "O campo semestre é obrigatório."}), 400

    replace_existing = payload.get("substituir", False)
    if not isinstance(replace_existing, bool):
        return jsonify({"erro": "O campo substituir deve ser booleano."}), 400

    assignments = payload.get("alocacoes")
    if not isinstance(assignments, list) or not assignments:
        return jsonify({
            "erro": "Envie ao menos uma alocação com alo_id e horario_id.",
        }), 400

    try:
        persistence = current_app.extensions["grade_repository"].replace_semester(
            semester,
            assignments,
            replace_existing=replace_existing,
        )
    except GradeAlreadyExistsError as exc:
        return jsonify({
            "erro": str(exc),
            "instrucao": "Envie substituir=true para substituir a grade desse semestre.",
        }), 409
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 422
    except sqlite3.IntegrityError as exc:
        current_app.logger.exception("Falha de integridade ao persistir a grade")
        return jsonify({"erro": f"A grade referencia dados inválidos: {exc}"}), 422
    except sqlite3.Error:
        current_app.logger.exception("Falha SQLite ao persistir a grade")
        return jsonify({"erro": "Não foi possível persistir a grade no SQLite."}), 500

    # Atualiza a representação em memória para que as rotas de consulta leiam
    # as mesmas associações que acabaram de ser gravadas.
    updated_graph = GraphDatabase()
    load_ok = load_from_sqlite(
        updated_graph,
        current_app.extensions["grade_repository"].database_path,
    )
    if not load_ok:
        current_app.logger.error("Grade persistida, mas o grafo não foi recarregado")
        return jsonify({
            "erro": "A grade foi salva, mas o grafo em memória não foi recarregado.",
            **persistence,
        }), 500
    current_app.extensions["graph_db"] = updated_graph

    return jsonify({
        "ok": True,
        "semestre": semester.strip(),
        **persistence,
    }), 201
