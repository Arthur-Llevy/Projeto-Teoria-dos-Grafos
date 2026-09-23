from typing import List, Dict, Any, Optional
from src.graph.graph_db import GraphDatabase
from src.graph.models import (
    Curso,
    Disciplina,
    Professor,
    Sala,
    Horario,
    NodeType,
    RelationType,
)


class GraphBuilder:
    """
    Factory para instanciar um grafo em memória a partir de dados
    estruturados (dicionários, JSON, SQLite).
    """

    def __init__(self, db: Optional[GraphDatabase] = None):
        self.db = db or GraphDatabase()

    # ------------------------------------------------------------------ #
    #  Curso
    # ------------------------------------------------------------------ #
    def add_course(self, course: Curso) -> str:
        node_id = self.db.add_node_with_id(
            node_id=course.id,
            node_type=NodeType.CURSO,
            properties=course.to_dict(),
        )
        return node_id

    def add_courses(self, courses: List[Curso]) -> List[str]:
        return [self.add_course(c) for c in courses]

    # ------------------------------------------------------------------ #
    #  Disciplina
    # ------------------------------------------------------------------ #
    def add_discipline(self, discipline: Disciplina) -> str:
        node_id = self.db.add_node_with_id(
            node_id=discipline.id,
            node_type=NodeType.DISCIPLINA,
            properties=discipline.to_dict(),
        )
        return node_id

    def add_disciplines(self, disciplines: List[Disciplina]) -> List[str]:
        return [self.add_discipline(d) for d in disciplines]

    # ------------------------------------------------------------------ #
    #  Professor
    # ------------------------------------------------------------------ #
    def add_professor(self, professor: Professor) -> str:
        node_id = self.db.add_node_with_id(
            node_id=professor.id,
            node_type=NodeType.PROFESSOR,
            properties=professor.to_dict(),
        )
        return node_id

    def add_professors(self, professors: List[Professor]) -> List[str]:
        return [self.add_professor(p) for p in professors]

    # ------------------------------------------------------------------ #
    #  Sala
    # ------------------------------------------------------------------ #
    def add_room(self, room: Sala) -> str:
        node_id = self.db.add_node_with_id(
            node_id=room.id,
            node_type=NodeType.SALA,
            properties=room.to_dict(),
        )
        return node_id

    def add_rooms(self, rooms: List[Sala]) -> List[str]:
        return [self.add_room(r) for r in rooms]

    # ------------------------------------------------------------------ #
    #  Horario
    # ------------------------------------------------------------------ #
    def add_schedule(self, schedule: Horario) -> str:
        node_id = self.db.add_node_with_id(
            node_id=schedule.id,
            node_type=NodeType.HORARIO,
            properties=schedule.to_dict(),
        )
        return node_id

    def add_schedules(self, schedules: List[Horario]) -> List[str]:
        return [self.add_schedule(s) for s in schedules]

    # ------------------------------------------------------------------ #
    #  Relations
    # ------------------------------------------------------------------ #
    def add_prerequisite(self, discipline_id: str, prerequisite_id: str):
        self.db.add_edge(
            from_id=discipline_id,
            to_id=prerequisite_id,
            relation=RelationType.PREREQUISITO,
        )

    def add_corequisite(self, discipline_id: str, corequisite_id: str):
        self.db.add_edge(
            from_id=discipline_id,
            to_id=corequisite_id,
            relation=RelationType.CORREQUISITO,
        )

    def add_teaches(self, professor_id: str, discipline_id: str):
        self.db.add_edge(
            from_id=professor_id,
            to_id=discipline_id,
            relation=RelationType.MINISTRADA_POR,
        )

    def add_belongs_to(self, discipline_id: str, course_id: str):
        self.db.add_edge(
            from_id=discipline_id,
            to_id=course_id,
            relation=RelationType.PERTENCE_A,
        )

    def add_enrolled(self, student_id: str, course_id: str):
        self.db.add_edge(
            from_id=student_id,
            to_id=course_id,
            relation=RelationType.MATRICULADO_EM,
        )

    def add_takes(self, student_id: str, discipline_id: str):
        self.db.add_edge(
            from_id=student_id,
            to_id=discipline_id,
            relation=RelationType.CURSADA,
        )

    def add_has_schedule(self, discipline_id: str, schedule_id: str):
        self.db.add_edge(
            from_id=discipline_id,
            to_id=schedule_id,
            relation=RelationType.TEM_HORARIO,
        )

    # ------------------------------------------------------------------ #
    #  Bulk from dicts
    # ------------------------------------------------------------------ #
    @classmethod
    def from_dicts(
        cls,
        courses: Optional[List[Dict]] = None,
        disciplines: Optional[List[Dict]] = None,
        professors: Optional[List[Dict]] = None,
        rooms: Optional[List[Dict]] = None,
        schedules: Optional[List[Dict]] = None,
    ) -> "GraphBuilder":
        builder = cls()
        if courses:
            builder.add_courses([Curso.from_dict(d) for d in courses])
        if disciplines:
            builder.add_disciplines([Disciplina.from_dict(d) for d in disciplines])
        if professors:
            builder.add_professors([Professor.from_dict(d) for d in professors])
        if rooms:
            builder.add_rooms([Sala.from_dict(d) for d in rooms])
        if schedules:
            builder.add_schedules([Horario.from_dict(d) for d in schedules])
        return builder
