import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


WEEKDAYS = {
    "Segunda": 2,
    "Terça": 3,
    "Quarta": 4,
    "Quinta": 5,
    "Sexta": 6,
}


class SlotRepository:
    """Leitura e persistência de slots na tabela hor_horario."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hor_horario (
                    hor_id INTEGER PRIMARY KEY,
                    hor_codigo_slot VARCHAR(100),
                    hor_dia_semana VARCHAR(20),
                    hor_bloco VARCHAR(10),
                    hor_hora_inicio TIME,
                    hor_hora_fim TIME
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_hor_horario_dia_bloco
                ON hor_horario (hor_dia_semana, hor_bloco)
                """
            )

    def list_all(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT hor_id, hor_codigo_slot, hor_dia_semana, hor_bloco,
                       hor_hora_inicio, hor_hora_fim
                FROM hor_horario
                ORDER BY CASE hor_dia_semana
                    WHEN 'Segunda' THEN 1 WHEN 'Terça' THEN 2
                    WHEN 'Quarta' THEN 3 WHEN 'Quinta' THEN 4
                    WHEN 'Sexta' THEN 5 ELSE 6 END,
                    hor_bloco COLLATE NOCASE, hor_hora_inicio, hor_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create(
        self, day: str, block: str, start: str, end: str
    ) -> dict[str, Any]:
        day = day.strip() if isinstance(day, str) else ""
        block = block.strip().upper() if isinstance(block, str) else ""
        start = start.strip() if isinstance(start, str) else ""
        end = end.strip() if isinstance(end, str) else ""

        if day not in WEEKDAYS:
            raise ValueError("Selecione um dia útil válido.")
        if len(block) != 1 or block not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            raise ValueError("O bloco deve ser uma letra de A a Z.")
        start_time = self._parse_time(start)
        end_time = self._parse_time(end)
        if end_time <= start_time:
            raise ValueError("O horário final deve ser posterior ao inicial.")

        with sqlite3.connect(str(self.database_path), timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            overlap = connection.execute(
                """
                SELECT 1 FROM hor_horario
                WHERE hor_dia_semana = ?
                  AND hor_hora_inicio < ?
                  AND hor_hora_fim > ?
                LIMIT 1
                """,
                (day, end, start),
            ).fetchone()
            if overlap:
                raise ValueError("Esse horário se sobrepõe a outro bloco do dia.")

            code = f"{WEEKDAYS[day]}{block}"
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO hor_horario
                        (hor_codigo_slot, hor_dia_semana, hor_bloco,
                         hor_hora_inicio, hor_hora_fim)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (code, day, block, start, end),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"O bloco {block} já está cadastrado para {day}."
                ) from exc
            slot_id = cursor.lastrowid
            row = connection.execute(
                """
                SELECT hor_id, hor_codigo_slot, hor_dia_semana, hor_bloco,
                       hor_hora_inicio, hor_hora_fim
                FROM hor_horario WHERE hor_id = ?
                """,
                (slot_id,),
            ).fetchone()
        return dict(row)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        if not isinstance(value, str):
            raise ValueError("Informe os horários no formato HH:MM.")
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("Informe os horários no formato HH:MM.") from exc
        if parsed.strftime("%H:%M") != value:
            raise ValueError("Informe os horários no formato HH:MM.")
        return parsed
