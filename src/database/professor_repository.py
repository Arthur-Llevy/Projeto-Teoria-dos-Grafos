import sqlite3
from pathlib import Path
from typing import Any


class ProfessorRepository:
    """Leitura e persistência de docentes na tabela pro_professor."""

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Create storage for optional time preferences and their coordinator setting."""
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pro_preferencia_horario (
                    pro_id INTEGER NOT NULL,
                    hor_id INTEGER NOT NULL,
                    PRIMARY KEY (pro_id, hor_id),
                    FOREIGN KEY (pro_id) REFERENCES pro_professor(pro_id),
                    FOREIGN KEY (hor_id) REFERENCES hor_horario(hor_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cfg_preferencia_horario (
                    cfg_id INTEGER PRIMARY KEY CHECK (cfg_id = 1),
                    cfg_min_horarios_excedentes INTEGER NOT NULL
                        CHECK (cfg_min_horarios_excedentes >= 0)
                )
                """
            )

    def list_all(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT p.pro_id, p.pro_nome, p.pro_matricula, p.cur_id,
                       COALESCE(c.cur_nome, c.cur_descricao, '') AS curso
                FROM pro_professor AS p
                LEFT JOIN cur_curso AS c ON c.cur_id = p.cur_id
                ORDER BY p.pro_nome COLLATE NOCASE, p.pro_id
                """
            ).fetchall()
        return [
            {
                "id": row["pro_id"],
                "nome": row["pro_nome"] or "",
                "matricula": row["pro_matricula"] or "",
                "curso_id": row["cur_id"],
                "curso": row["curso"],
            }
            for row in rows
        ]

    def get_professor(self, professor_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT p.pro_id, p.pro_nome, p.pro_matricula, p.cur_id,
                       COALESCE(NULLIF(c.cur_nome, ''), c.cur_descricao, '') AS curso
                FROM pro_professor AS p
                LEFT JOIN cur_curso AS c ON c.cur_id = p.cur_id
                WHERE p.pro_id = ?
                """,
                (professor_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["pro_id"],
            "nome": row["pro_nome"] or "",
            "matricula": row["pro_matricula"] or "",
            "curso_id": row["cur_id"],
            "curso": row["curso"],
        }

    def list_allocated_disciplines(self, professor_id: int) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT a.alo_id, d.dis_id, d.dis_codigo, d.dis_descricao,
                       d.dis_periodo, d.dis_carga_horaria
                FROM alo_alocacao AS a
                JOIN dis_disciplina AS d ON d.dis_id = a.dis_id
                WHERE a.pro_id = ?
                ORDER BY d.dis_periodo, d.dis_descricao, a.alo_id
                """,
                (professor_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_available_disciplines(self, professor_id: int) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT d.dis_id, d.dis_codigo, d.dis_descricao, d.dis_periodo,
                       d.dis_carga_horaria
                FROM pro_professor AS p
                JOIN dis_disciplina AS d ON d.cur_id = p.cur_id
                WHERE p.pro_id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM alo_alocacao AS a
                      WHERE a.pro_id = p.pro_id AND a.dis_id = d.dis_id
                  )
                ORDER BY d.dis_periodo, d.dis_descricao
                """,
                (professor_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_allocation(self, professor_id: int, discipline_id: int) -> int:
        """Link a professor to a discipline from the same course."""
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            discipline = connection.execute(
                """
                SELECT d.dis_carga_horaria
                FROM pro_professor AS p
                JOIN dis_disciplina AS d ON d.cur_id = p.cur_id
                WHERE p.pro_id = ? AND d.dis_id = ?
                """,
                (professor_id, discipline_id),
            ).fetchone()
            if discipline is None:
                raise ValueError("A disciplina não pertence ao curso do professor.")
            existing = connection.execute(
                "SELECT alo_id FROM alo_alocacao WHERE pro_id = ? AND dis_id = ?",
                (professor_id, discipline_id),
            ).fetchone()
            if existing is not None:
                raise ValueError("Essa disciplina já está alocada ao professor.")

            preference_count = connection.execute(
                "SELECT COUNT(*) FROM pro_preferencia_horario WHERE pro_id = ?",
                (professor_id,),
            ).fetchone()[0]
            if preference_count:
                try:
                    workload = int(discipline[0])
                except (TypeError, ValueError) as exc:
                    raise ValueError("A carga horária da disciplina é inválida.") from exc
                if workload <= 0 or workload % 15:
                    raise ValueError(
                        "A carga horária deve ser positiva e múltipla de 15 horas."
                    )
                min_extra_row = connection.execute(
                    """
                    SELECT cfg_min_horarios_excedentes
                    FROM cfg_preferencia_horario WHERE cfg_id = 1
                    """
                ).fetchone()
                if min_extra_row is None:
                    raise ValueError(
                        "Configure o parâmetro N antes de alterar as alocações "
                        "de um professor com preferências."
                    )
                required = 0
                workloads = connection.execute(
                    """
                    SELECT d.dis_carga_horaria
                    FROM alo_alocacao AS a
                    JOIN dis_disciplina AS d ON d.dis_id = a.dis_id
                    WHERE a.pro_id = ?
                    """,
                    (professor_id,),
                ).fetchall()
                for (raw_workload,) in workloads:
                    current_workload = int(raw_workload)
                    if current_workload <= 0 or current_workload % 15:
                        raise ValueError(
                            "Uma disciplina já alocada possui carga horária inválida."
                        )
                    required += current_workload // 15
                projected_minimum = (
                    required + workload // 15 + min_extra_row[0]
                )
                if preference_count < projected_minimum:
                    raise ValueError(
                        "Esta alocação aumentaria o mínimo de horários preferidos "
                        f"para {projected_minimum}. Atualize as preferências antes "
                        "de alocar a disciplina."
                    )
            cursor = connection.execute(
                "INSERT INTO alo_alocacao (pro_id, dis_id) VALUES (?, ?)",
                (professor_id, discipline_id),
            )
            return int(cursor.lastrowid)

    def list_slots(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT hor_id, hor_dia_semana, hor_hora_inicio, hor_hora_fim
                FROM hor_horario
                ORDER BY CASE hor_dia_semana
                    WHEN 'Segunda' THEN 1 WHEN 'Terça' THEN 2
                    WHEN 'Quarta' THEN 3 WHEN 'Quinta' THEN 4
                    WHEN 'Sexta' THEN 5 WHEN 'Sábado' THEN 6
                    WHEN 'Domingo' THEN 7 ELSE 8 END,
                    hor_hora_inicio, hor_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_min_extra_slots(self) -> int | None:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            row = connection.execute(
                """
                SELECT cfg_min_horarios_excedentes
                FROM cfg_preferencia_horario WHERE cfg_id = 1
                """
            ).fetchone()
        return row[0] if row else None

    def set_min_extra_slots(self, value: int) -> None:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute(
                """
                INSERT INTO cfg_preferencia_horario
                    (cfg_id, cfg_min_horarios_excedentes)
                VALUES (1, ?)
                ON CONFLICT(cfg_id) DO UPDATE SET
                    cfg_min_horarios_excedentes = excluded.cfg_min_horarios_excedentes
                """,
                (value,),
            )

    def required_slot_count(self, professor_id: int) -> int:
        """Count weekly 50-minute meetings required by this professor's load."""
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            rows = connection.execute(
                """
                SELECT d.dis_carga_horaria
                FROM alo_alocacao AS a
                JOIN dis_disciplina AS d ON d.dis_id = a.dis_id
                WHERE a.pro_id = ?
                """,
                (professor_id,),
            ).fetchall()
        required = 0
        for (raw_workload,) in rows:
            try:
                workload = int(raw_workload)
            except (TypeError, ValueError) as exc:
                raise ValueError("A carga horária de uma disciplina é inválida.") from exc
            if workload <= 0 or workload % 15:
                raise ValueError(
                    "As disciplinas alocadas precisam ter carga horária positiva "
                    "e múltipla de 15 horas."
                )
            required += workload // 15
        return required

    def list_preferred_slot_ids(self, professor_id: int) -> set[int]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            rows = connection.execute(
                "SELECT hor_id FROM pro_preferencia_horario WHERE pro_id = ?",
                (professor_id,),
            ).fetchall()
        return {row[0] for row in rows}

    def professors_with_preferences(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT p.pro_id, p.pro_nome, COUNT(pref.hor_id) AS slot_count
                FROM pro_professor AS p
                JOIN pro_preferencia_horario AS pref ON pref.pro_id = p.pro_id
                GROUP BY p.pro_id, p.pro_nome
                ORDER BY p.pro_nome
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_preferred_slots(self, professor_id: int, slot_ids: list[int]) -> None:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "DELETE FROM pro_preferencia_horario WHERE pro_id = ?",
                (professor_id,),
            )
            connection.executemany(
                """
                INSERT INTO pro_preferencia_horario (pro_id, hor_id)
                VALUES (?, ?)
                """,
                [(professor_id, slot_id) for slot_id in slot_ids],
            )

    def list_courses(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT cur_id, COALESCE(cur_nome, cur_descricao, '') AS nome
                FROM cur_curso
                ORDER BY nome COLLATE NOCASE, cur_id
                """
            ).fetchall()
        return [{"id": row["cur_id"], "nome": row["nome"]} for row in rows]

    def has_matricula(self, matricula: str) -> bool:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            return connection.execute(
                """
                SELECT 1 FROM pro_professor
                WHERE UPPER(TRIM(pro_matricula)) = UPPER(?)
                LIMIT 1
                """,
                (matricula,),
            ).fetchone() is not None

    def create(self, nome: str, matricula: str, curso_id: int) -> dict[str, Any]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            cursor = connection.execute(
                """
                INSERT INTO pro_professor (pro_nome, pro_matricula, cur_id)
                VALUES (?, ?, ?)
                """,
                (nome, matricula, curso_id),
            )
            professor_id = cursor.lastrowid
        return {
            "id": professor_id,
            "nome": nome,
            "matricula": matricula,
            "curso_id": curso_id,
        }
