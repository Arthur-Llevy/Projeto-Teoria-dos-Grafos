import sqlite3
from pathlib import Path
from typing import Any


class GradeAlreadyExistsError(Exception):
    """Raised when a semester already has rows and replacement was not allowed."""


class GradeRepository:
    """Persist a generated timetable in the SQLite gra_grade_horaria table."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Ensure the grade table exists without altering saved timetables."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS gra_grade_horaria (
                    gra_id INTEGER PRIMARY KEY,
                    gra_semestre VARCHAR(10),
                    alo_id INTEGER,
                    hor_id INTEGER,
                    sal_id INTEGER,
                    FOREIGN KEY (alo_id) REFERENCES alo_alocacao(alo_id),
                    FOREIGN KEY (hor_id) REFERENCES hor_horario(hor_id),
                    FOREIGN KEY (sal_id) REFERENCES sal_sala(sal_id)
                )
                """
            )

    def replace_semester(
        self,
        semester: str,
        assignments: list[dict[str, Any]],
        *,
        replace_existing: bool = False,
    ) -> dict[str, int]:
        semester = semester.strip()
        if not semester or len(semester) > 10:
            raise ValueError("O semestre deve ter entre 1 e 10 caracteres.")
        if not assignments:
            raise ValueError("Não há alocações coloridas para persistir.")

        rows = []
        for assignment in assignments:
            try:
                allocation_id = int(assignment["alo_id"])
                horario_id = int(assignment["horario_id"])
                room_id = assignment.get("sal_id")
                if room_id is not None:
                    room_id = int(room_id)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "Cada atribuição precisa de alo_id e horario_id inteiros; "
                    "sal_id deve ser inteiro ou nulo."
                ) from exc
            rows.append((semester, allocation_id, horario_id, room_id))

        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            existing_count = connection.execute(
                "SELECT COUNT(*) FROM gra_grade_horaria WHERE gra_semestre = ?",
                (semester,),
            ).fetchone()[0]
            if existing_count and not replace_existing:
                raise GradeAlreadyExistsError(
                    f"O semestre {semester} já possui {existing_count} registros."
                )

            deleted_count = 0
            if existing_count:
                cursor = connection.execute(
                    "DELETE FROM gra_grade_horaria WHERE gra_semestre = ?",
                    (semester,),
                )
                deleted_count = cursor.rowcount

            connection.executemany(
                """
                INSERT INTO gra_grade_horaria
                    (gra_semestre, alo_id, hor_id, sal_id)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

        return {"inserted": len(rows), "deleted": deleted_count}
