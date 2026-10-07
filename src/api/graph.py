from collections import defaultdict
from flask import Blueprint, jsonify, current_app, abort

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")

def _g():
    return current_app.extensions["graph_db"]


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
    from src.graph.sqlite_loader import load_from_sqlite
    from pathlib import Path
    g = _g()
    g.clear()
    db = Path(current_app.root_path) / "grade_horaria.db"
    ok = load_from_sqlite(g, db)
    return jsonify({"ok": ok}), (200 if ok else 500)