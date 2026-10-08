"""Color graph allocation vertices and map colors to real timetable slots.

Each allocation is expanded into one vertex per 30 hours of discipline
workload, as required by Fluxo_requisitos.pdf. Colors are 1-based indexes;
``map_colors_to_slots`` translates each index into an actual ``hor_id``.

For a universal course timetable, the regular full-profile constraint is
covered by connecting required disciplines in the same course and ideal term.
"""

from collections import defaultdict
from math import ceil
from typing import Dict, Iterable, Mapping, Optional, Set, Tuple

from src.graph.graph_db import GraphDatabase

VERTEX_TYPE = "alocacao"
DISCIPLINE_RELATION = "MINISTRA"
PROFESSOR_RELATION = "ALOCADO_EM"
SLOT_NODE_TYPE = "horario"
HOURS_PER_VERTEX = 30
MAX_PROFESSOR_SEMESTER_HOURS = 240


def _discipline_for_allocation(
    graph: GraphDatabase, allocation: Dict
) -> Optional[Dict]:
    for neighbor in graph.get_neighbors(
        allocation["id"], relation=DISCIPLINE_RELATION
    ):
        if neighbor["type"] == "disciplina":
            return neighbor

    discipline_id = allocation["properties"].get("dis_id")
    if discipline_id is None:
        return None
    expected_id = f"disc:{discipline_id}"
    return next(
        (
            node
            for node in graph.get_nodes_by_type("disciplina")
            if node["id"] == expected_id
            or str(node["properties"].get("dis_id")) == str(discipline_id)
            or str(node["properties"].get("id")) == str(discipline_id)
        ),
        None,
    )


def _professor_for_allocation(
    graph: GraphDatabase, allocation: Dict
) -> Optional[str]:
    for neighbor in graph.get_neighbors(
        allocation["id"], relation=PROFESSOR_RELATION
    ):
        if neighbor["type"] == "professor":
            return neighbor["id"]

    professor_id = allocation["properties"].get("pro_id")
    if professor_id is None:
        return None
    expected_id = f"prof:{professor_id}"
    return next(
        (
            node["id"]
            for node in graph.get_nodes_by_type("professor")
            if node["id"] == expected_id
            or str(node["properties"].get("pro_id")) == str(professor_id)
            or str(node["properties"].get("id")) == str(professor_id)
        ),
        expected_id,
    )


def _discipline_workload(discipline: Dict) -> int:
    properties = discipline["properties"]
    raw_hours = properties.get(
        "carga_horaria", properties.get("dis_carga_horaria")
    )
    try:
        workload = int(raw_hours)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Carga horária inválida na disciplina {discipline['id']}."
        ) from exc
    if workload <= 0:
        raise ValueError(
            f"A disciplina {discipline['id']} precisa ter carga horária positiva."
        )
    return workload


def _vertices_by_allocation(graph: GraphDatabase) -> Dict[str, list[str]]:
    """Expand each allocation into vertices of at most 30 discipline hours."""
    vertices: Dict[str, list[str]] = {}
    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        discipline = _discipline_for_allocation(graph, allocation)
        if discipline is None:
            raise ValueError(
                f"A alocação {allocation['id']} não está vinculada a uma disciplina."
            )

        workload = _discipline_workload(discipline)
        count = ceil(workload / HOURS_PER_VERTEX)
        vertices[allocation["id"]] = [
            f"{allocation['id']}#30h:{index}"
            for index in range(1, count + 1)
        ]
    return vertices


def validate_professor_workload(
    graph: GraphDatabase,
    max_hours: int = MAX_PROFESSOR_SEMESTER_HOURS,
) -> Dict[str, int]:
    """Reject graphs where a professor exceeds the semester workload in the PDF."""
    if max_hours <= 0:
        raise ValueError("max_hours deve ser maior que zero.")

    hours_by_professor: Dict[str, int] = defaultdict(int)
    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        professor_id = _professor_for_allocation(graph, allocation)
        if professor_id is None:
            continue

        discipline = _discipline_for_allocation(graph, allocation)
        if discipline is None:
            raise ValueError(
                f"A alocação {allocation['id']} não está vinculada a uma disciplina."
            )
        hours_by_professor[professor_id] += _discipline_workload(discipline)

    overloaded = {
        professor_id: hours
        for professor_id, hours in hours_by_professor.items()
        if hours > max_hours
    }
    if overloaded:
        details = ", ".join(
            f"{professor_id}: {hours}h"
            for professor_id, hours in sorted(overloaded.items())
        )
        raise ValueError(
            f"Carga horária docente acima do limite de {max_hours}h por semestre: "
            f"{details}."
        )
    return dict(hours_by_professor)


def _connect_group(adjacency: Dict[str, Set[str]], vertices: Iterable[str]) -> None:
    members = list(vertices)
    for index, vertex in enumerate(members):
        for other in members[index + 1 :]:
            if vertex != other:
                adjacency[vertex].add(other)
                adjacency[other].add(vertex)


def build_conflict_graph(
    graph: GraphDatabase,
) -> Dict[str, Set[str]]:
    """Build an adjacency list for the hard constraints.

    Vertices from the same professor, required curriculum period, or discipline
    are connected and therefore need different colors. In a universal course
    timetable, required disciplines in the same course and ideal term model the
    regular full profile.
    """
    vertices_by_allocation = _vertices_by_allocation(graph)
    adjacency: Dict[str, Set[str]] = {
        vertex: set()
        for allocation_vertices in vertices_by_allocation.values()
        for vertex in allocation_vertices
    }
    curricular_groups: Dict[Tuple[str, str], list[str]] = defaultdict(list)
    professor_groups: Dict[str, list[str]] = defaultdict(list)
    discipline_groups: Dict[str, list[str]] = defaultdict(list)

    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        allocation_id = allocation["id"]
        allocation_vertices = vertices_by_allocation[allocation_id]
        discipline = _discipline_for_allocation(graph, allocation)
        properties = discipline["properties"]
        is_elective = properties.get(
            "eh_eletiva", properties.get("dis_eh_eletiva", False)
        )
        course_id = properties.get("cur_id", properties.get("curso_id"))
        period = properties.get("periodo", properties.get("dis_periodo"))
        if not is_elective and course_id is not None and period is not None:
            curricular_groups[(str(course_id), str(period))].extend(
                allocation_vertices
            )

        discipline_id = properties.get(
            "dis_id", properties.get("id", discipline["id"])
        )
        discipline_groups[str(discipline_id)].extend(allocation_vertices)

        professor_id = _professor_for_allocation(graph, allocation)
        if professor_id is not None:
            professor_groups[professor_id].extend(allocation_vertices)

    for group in curricular_groups.values():
        _connect_group(adjacency, group)
    for group in professor_groups.values():
        _connect_group(adjacency, group)
    for group in discipline_groups.values():
        _connect_group(adjacency, group)

    return adjacency


def validate_coloring(
    adjacency: Dict[str, Set[str]], colors: Dict[str, int]
) -> None:
    missing = set(adjacency) - set(colors)
    if missing:
        raise ValueError(f"Alocações sem cor: {', '.join(sorted(missing))}")

    for vertex, neighbors in adjacency.items():
        for neighbor in neighbors:
            if colors[vertex] == colors[neighbor]:
                raise ValueError(
                    f"Conflito: {vertex} e {neighbor} receberam "
                    f"a cor {colors[vertex]}."
                )


def color_allocations(
    graph: GraphDatabase,
    max_colors: Optional[int] = None,
) -> Dict[str, int]:
    """Validate workload and color allocation vertices with deterministic DSatur."""
    if max_colors is not None and max_colors < 1:
        raise ValueError("max_colors deve ser maior que zero.")

    validate_professor_workload(graph)
    adjacency = build_conflict_graph(graph)
    uncolored = set(adjacency)
    colors: Dict[str, int] = {}

    while uncolored:
        vertex = min(
            uncolored,
            key=lambda item: (
                -len({colors[n] for n in adjacency[item] if n in colors}),
                -len(adjacency[item]),
                item,
            ),
        )
        unavailable = {colors[n] for n in adjacency[vertex] if n in colors}
        color = next(
            (candidate for candidate in range(1, len(adjacency) + 1)
             if candidate not in unavailable),
            None,
        )
        if max_colors is not None and (color is None or color > max_colors):
            raise ValueError(
                f"Não foi possível colorir o grafo com apenas {max_colors} cores."
            )
        if color is None:
            raise RuntimeError("Não foi possível encontrar uma cor disponível.")

        colors[vertex] = color
        uncolored.remove(vertex)

    validate_coloring(adjacency, colors)
    _store_assignments(graph, colors)
    return colors


def _store_assignments(graph: GraphDatabase, colors: Dict[str, int]) -> None:
    """Store initial color results on allocation nodes, grouped by allocation."""
    grouped: Dict[str, list[Dict[str, int]]] = defaultdict(list)
    for vertex, color in colors.items():
        allocation_id = vertex.split("#30h:", maxsplit=1)[0]
        grouped[allocation_id].append({"vertex": vertex, "color": color})

    for allocation_id, assignments in grouped.items():
        assignments.sort(
            key=lambda assignment: int(
                assignment["vertex"].rsplit(":", maxsplit=1)[1]
            )
        )
        properties = graph.nodes[allocation_id]["properties"]
        properties["assignments"] = assignments
        if len(assignments) == 1:
            properties["color"] = assignments[0]["color"]
        else:
            properties.pop("color", None)


def _slot_sort_key(slot: Dict) -> Tuple[int, str, int, str]:
    properties = slot["properties"]
    days = {
        "Segunda": 1,
        "Terça": 2,
        "Quarta": 3,
        "Quinta": 4,
        "Sexta": 5,
        "Sábado": 6,
        "Domingo": 7,
    }
    day = properties.get("dia_semana", properties.get("dia", ""))
    slot_id = properties.get("hor_id", slot["id"].removeprefix("hor:"))
    try:
        numeric_id = int(slot_id)
    except (TypeError, ValueError):
        numeric_id = 0
    return (
        days.get(day, 99),
        properties.get("hora_inicio", ""),
        numeric_id,
        slot["id"],
    )


def map_colors_to_slots(
    graph: GraphDatabase, colors: Mapping[str, int]
) -> Dict[int, int]:
    """Map each 1-based color to a real ``hor_id`` from graph slot nodes."""
    slots = sorted(graph.get_nodes_by_type(SLOT_NODE_TYPE), key=_slot_sort_key)
    if not slots and colors:
        raise ValueError("O grafo não contém nós de horário para mapear as cores.")

    color_ids = sorted(set(colors.values()))
    if any(color < 1 for color in color_ids):
        raise ValueError("As cores precisam ser índices inteiros a partir de 1.")
    if color_ids and color_ids[-1] > len(slots):
        raise ValueError(
            f"O grafo usa {color_ids[-1]} cores, mas só há {len(slots)} horários."
        )

    mapped: Dict[int, int] = {}
    for color in color_ids:
        raw_slot_id = slots[color - 1]["properties"].get(
            "hor_id", slots[color - 1]["id"].removeprefix("hor:")
        )
        try:
            mapped[color] = int(raw_slot_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"O nó de horário {slots[color - 1]['id']} não tem hor_id inteiro."
            ) from exc
    return mapped


def color_and_assign_slots(
    graph: GraphDatabase,
    max_colors: Optional[int] = None,
) -> Dict[str, Dict[str, object]]:
    """Color the graph and add real horario IDs to each allocation chunk."""
    colors = color_allocations(graph, max_colors=max_colors)
    slot_ids = map_colors_to_slots(graph, colors)
    results: Dict[str, Dict[str, object]] = {}
    for vertex, color in colors.items():
        assignment = {"color": color, "horario_id": slot_ids[color]}
        results[vertex] = assignment
        allocation_id = vertex.split("#30h:", maxsplit=1)[0]
        stored = graph.nodes[allocation_id]["properties"]["assignments"]
        next(item for item in stored if item["vertex"] == vertex).update(assignment)

    return results
