import sqlite3
from pathlib import Path
from typing import Union


def _safe_add_edge(graph_db, from_id: str, to_id: str,
                   relation: str, properties=None):
    """Cria aresta somente se ambos os nós existirem; senão avisa e ignora."""
    if from_id not in graph_db.nodes:
        print(f"[loader] ⚠ aresta ignorada (from ausente): {from_id}")
        return
    if to_id not in graph_db.nodes:
        print(f"[loader] ⚠ aresta ignorada (to ausente): {to_id}")
        return
    graph_db.add_edge(from_id, to_id, relation=relation,
                      properties=properties or {})


def load_from_sqlite(graph_db, db_path: Union[str, Path]) -> bool:
    """Popula a GraphDatabase a partir do SQLite da grade horária."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"[loader] banco não encontrado: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # Nós: Cursos
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM cur_curso"):
        graph_db.add_node_with_id(
            node_id=f"curso:{r['cur_id']}",
            node_type="curso",
            properties={
                "cur_id": r["cur_id"],
                "descricao": r["cur_descricao"],
            },
        )

    # ------------------------------------------------------------------
    # Nós: Professores
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM pro_professor"):
        pid = f"prof:{r['pro_id']}"
        graph_db.add_node_with_id(
            node_id=pid,
            node_type="professor",
            properties={
                "pro_id": r["pro_id"],
                "nome": r["pro_nome"],
                "matricula": r["pro_matricula"],
                "cur_id": r["cur_id"],
            },
        )
        if r["cur_id"] is not None:
            _safe_add_edge(graph_db, pid, f"curso:{r['cur_id']}", "VINCULADO_A")

    # ------------------------------------------------------------------
    # Nós: Disciplinas
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM dis_disciplina"):
        did = f"disc:{r['dis_id']}"
        graph_db.add_node_with_id(
            node_id=did,
            node_type="disciplina",
            properties={
                "dis_id": r["dis_id"],
                "codigo": r["dis_codigo"],
                "descricao": r["dis_descricao"],
                "periodo": r["dis_periodo"],
                "carga_horaria": r["dis_carga_horaria"],
                "eh_eletiva": bool(r["dis_eh_eletiva"]),
                "cur_id": r["cur_id"],
            },
        )
        if r["cur_id"] is not None:
            _safe_add_edge(graph_db, did, f"curso:{r['cur_id']}", "PERTENCE_A")

    # ------------------------------------------------------------------
    # Nós: Horários
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM hor_horario"):
        graph_db.add_node_with_id(
            node_id=f"hor:{r['hor_id']}",
            node_type="horario",
            properties={
                "hor_id": r["hor_id"],
                "codigo_slot": r["hor_codigo_slot"],
                "dia_semana": r["hor_dia_semana"],
                "bloco": r["hor_bloco"],
                "hora_inicio": r["hor_hora_inicio"],
                "hora_fim": r["hor_hora_fim"],
            },
        )

    # ------------------------------------------------------------------
    # Nós: Salas
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM sal_sala"):
        graph_db.add_node_with_id(
            node_id=f"sala:{r['sal_id']}",
            node_type="sala",
            properties={
                "sal_id": r["sal_id"],
                "descricao": r["sal_descricao"],
                "capacidade": r["sal_capacidade"],
            },
        )

    # ------------------------------------------------------------------
    # Nós: Alocações + arestas
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM alo_alocacao"):
        aid = f"alo:{r['alo_id']}"
        graph_db.add_node_with_id(
            node_id=aid,
            node_type="alocacao",
            properties={
                "alo_id": r["alo_id"],
                "pro_id": r["pro_id"],
                "dis_id": r["dis_id"],
            },
        )
        if r["pro_id"] is not None:
            _safe_add_edge(graph_db, f"prof:{r['pro_id']}", aid, "ALOCADO_EM")
        if r["dis_id"] is not None:
            _safe_add_edge(graph_db, aid, f"disc:{r['dis_id']}", "MINISTRA")

    # ------------------------------------------------------------------
    # Grade horária: alo -> hor / sala
    # ------------------------------------------------------------------
    for r in cur.execute("SELECT * FROM gra_grade_horaria"):
        alo_id = f"alo:{r['alo_id']}"
        hor_id = f"hor:{r['hor_id']}"
        sal_id = f"sala:{r['sal_id']}"
        _safe_add_edge(graph_db, alo_id, hor_id, "OCORRE_EM",
                       {"semestre": r["gra_semestre"]})
        _safe_add_edge(graph_db, alo_id, sal_id, "NA_SALA",
                       {"semestre": r["gra_semestre"]})

    conn.close()

    # Resumo final no log
    from collections import Counter
    tipos = Counter(n["type"] for n in graph_db.nodes.values())
    print(f"[loader] grafo carregado: {dict(tipos)} | "
          f"total arestas: {len(graph_db.edges)}")
    return True