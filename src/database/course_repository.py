import sqlite3
from pathlib import Path
from typing import Any


class CourseRepository:
    """Leitura e persistência de cursos na tabela cur_curso."""

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Garante o esquema de cursos sem apagar dados existentes."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cur_curso (
                    cur_id INTEGER PRIMARY KEY,
                    cur_nome VARCHAR(100),
                    cur_descricao VARCHAR(100)
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(cur_curso)")
            }
            if "cur_nome" not in columns:
                connection.execute(
                    "ALTER TABLE cur_curso ADD COLUMN cur_nome VARCHAR(100)"
                )
            if "cur_descricao" not in columns:
                connection.execute(
                    "ALTER TABLE cur_curso ADD COLUMN cur_descricao VARCHAR(100)"
                )

    def list_all(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT cur_id, cur_nome, cur_descricao
                FROM cur_curso
                ORDER BY cur_id
                """
            ).fetchall()
        return [
            {
                "id": row["cur_id"],
                # Dados legados guardavam o nome em cur_descricao.
                "nome": row["cur_nome"] or row["cur_descricao"] or "",
                "descricao": row["cur_descricao"] or "",
            }
            for row in rows
        ]

    def create(self, nome: str, descricao: str = "") -> dict[str, Any]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            cursor = connection.execute(
                """
                INSERT INTO cur_curso (cur_nome, cur_descricao)
                VALUES (?, ?)
                """,
                (nome, descricao),
            )
            course_id = cursor.lastrowid
        return {"id": course_id, "nome": nome, "descricao": descricao}
