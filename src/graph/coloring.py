"""Color graph allocation vertices and map colors to real timetable slots.

Each allocation is expanded into one vertex per 30 hours of discipline
workload. Each color maps to two consecutive 50-minute ``hor_id`` values.

For a universal course timetable, the regular full-profile constraint is
covered by connecting required disciplines in the same course and ideal term.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import ceil
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

from src.graph.graph_db import GraphDatabase

VERTEX_TYPE = "alocacao"
DISCIPLINE_RELATION = "MINISTRA"
PROFESSOR_RELATION = "ALOCADO_EM"
SLOT_NODE_TYPE = "horario"
HOURS_PER_VERTEX = 30
MAX_PROFESSOR_SEMESTER_HOURS = 240


@dataclass(frozen=True)
class SlotPair:
    """Two adjacent 50-minute slots representing one 30-hour workload unit."""

    day: str
    start: str
    end: str
    horario_ids: Tuple[int, int]


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
    adjacency: Dict[str, Set[str]],
    colors: Dict[str, int],
    max_parallel_classes: Optional[int] = None,
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

    if max_parallel_classes is not None:
        classes_by_color: Dict[int, int] = defaultdict(int)
        for color in colors.values():
            classes_by_color[color] += 1
        overloaded = {
            color: count
            for color, count in classes_by_color.items()
            if count > max_parallel_classes
        }
        if overloaded:
            color, count = min(overloaded.items())
            raise ValueError(
                f"A cor {color} reúne {count} alocações simultâneas, "
                f"mas há apenas {max_parallel_classes} salas."
            )


def color_allocations(
    graph: GraphDatabase,
    max_colors: Optional[int] = None,
    max_parallel_classes: Optional[int] = None,
) -> Dict[str, int]:
    """Color 30-hour workload units with DSatur and room-count capacity."""
    if max_colors is not None and max_colors < 1:
        raise ValueError("max_colors deve ser maior que zero.")

    validate_professor_workload(graph)
    adjacency = build_conflict_graph(graph)
    rooms = graph.get_nodes_by_type("sala")
    if max_parallel_classes is None and rooms:
        max_parallel_classes = len(rooms)
    if max_parallel_classes is not None and max_parallel_classes < 1:
        raise ValueError("max_parallel_classes deve ser maior que zero.")

    if max_colors is None:
        max_colors = _max_disjoint_pair_count(graph)
    if adjacency and max_colors < 1:
        raise ValueError(
            "O grafo não contém pares de horários consecutivos para agendar aulas."
        )

    uncolored = set(adjacency)
    colors: Dict[str, int] = {}
    class_count_by_color: Dict[int, int] = defaultdict(int)

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
        color = next((
            candidate
            for candidate in range(1, max_colors + 1)
            if candidate not in unavailable
            and (
                max_parallel_classes is None
                or class_count_by_color[candidate] < max_parallel_classes
            )
        ), None)
        if color is None:
            raise ValueError(
                f"Não foi possível colorir o grafo com até {max_colors} pares "
                "de horários e a capacidade de salas disponível."
            )

        colors[vertex] = color
        class_count_by_color[color] += 1
        uncolored.remove(vertex)

    validate_coloring(adjacency, colors, max_parallel_classes)
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


def _minute(value: str) -> int:
    try:
        parts = str(value).split(":")
        hours, minutes = parts[:2]
        return int(hours) * 60 + int(minutes)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Horário inválido: {value!r}.") from exc


def _slot_pairs(graph: GraphDatabase) -> List[SlotPair]:
    slots = sorted(graph.get_nodes_by_type(SLOT_NODE_TYPE), key=_slot_sort_key)
    by_day: Dict[str, list[Dict]] = defaultdict(list)
    for slot in slots:
        props = slot["properties"]
        day = str(props.get("dia_semana", props.get("dia", "")))
        by_day[day].append(slot)

    pairs: List[SlotPair] = []
    for day, day_slots in by_day.items():
        day_slots.sort(key=_slot_sort_key)
        for first, second in zip(day_slots, day_slots[1:]):
            first_props, second_props = first["properties"], second["properties"]
            first_end = _minute(first_props.get("hora_fim", ""))
            second_start = _minute(second_props.get("hora_inicio", ""))
            if first_end != second_start:
                continue
            ids = []
            for slot in (first, second):
                raw_id = slot["properties"].get(
                    "hor_id", slot["id"].removeprefix("hor:")
                )
                try:
                    ids.append(int(raw_id))
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"O nó de horário {slot['id']} não tem hor_id inteiro."
                    ) from exc
            pairs.append(
                SlotPair(
                    day,
                    str(first_props["hora_inicio"]),
                    str(second_props["hora_fim"]),
                    tuple(ids),
                )
            )
    return pairs


def _max_disjoint_pair_count(graph: GraphDatabase) -> int:
    """Count non-overlapping two-block meetings available over all weekdays."""
    pairs_by_day: Dict[str, List[SlotPair]] = defaultdict(list)
    for pair in _slot_pairs(graph):
        pairs_by_day[pair.day].append(pair)
    total = 0
    for day_pairs in pairs_by_day.values():
        selected = 0
        last_end = -1
        for pair in sorted(day_pairs, key=lambda item: (_minute(item.end), item.start)):
            start = _minute(pair.start)
            if start >= last_end:
                selected += 1
                last_end = _minute(pair.end)
        total += selected
    return total


def _same_day_adjacent(first: SlotPair, second: SlotPair) -> bool:
    return first.day == second.day and (
        _minute(first.end) == _minute(second.start)
        or _minute(second.end) == _minute(first.start)
    )


def _required_pair_groups(graph: GraphDatabase) -> List[Tuple[str, str]]:
    """Return color pairs belonging to the two 30h chunks of each 60h class."""
    groups = []
    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        discipline = _discipline_for_allocation(graph, allocation)
        if _discipline_workload(discipline) == 60:
            chunks = _vertices_by_allocation(graph)[allocation["id"]]
            if len(chunks) != 2:
                raise ValueError(
                    f"A disciplina de 60h da alocação {allocation['id']} "
                    "não foi dividida em dois blocos de 30h."
                )
            groups.append((chunks[0], chunks[1]))
        elif _discipline_workload(discipline) != 30:
            raise ValueError(
                f"A carga horária da alocação {allocation['id']} é "
                f"{_discipline_workload(discipline)}h; os padrões definidos "
                "só cobrem disciplinas de 30h e 60h."
            )
    return groups


def map_colors_to_slots(
    graph: GraphDatabase, colors: Mapping[str, int]
) -> Dict[int, Tuple[int, int]]:
    """Map colors to consecutive slot pairs, keeping 60h classes contiguous."""
    pairs = _slot_pairs(graph)
    if not pairs and colors:
        raise ValueError("O grafo não contém pares de horários consecutivos.")

    color_ids = sorted(set(colors.values()))
    if any(color < 1 for color in color_ids):
        raise ValueError("As cores precisam ser índices inteiros a partir de 1.")
    if color_ids and color_ids[-1] > len(pairs):
        raise ValueError(
            f"O grafo usa {color_ids[-1]} cores, mas só há {len(pairs)} pares."
        )

    # Colors are assigned a pair with backtracking: pairs cannot overlap, and
    # chunks of each 60h class must use two days or four consecutive blocks.
    color_of_vertex = dict(colors)
    constraints: Set[frozenset[int]] = set()
    for left, right in _required_pair_groups(graph):
        if left not in color_of_vertex or right not in color_of_vertex:
            raise ValueError("Uma disciplina de 60h está sem cor atribuída.")
        constraints.add(frozenset((color_of_vertex[left], color_of_vertex[right])))

    domains = {color: list(pairs) for color in color_ids}
    mapped: Dict[int, SlotPair] = {}
    used_ids: Set[int] = set()

    def search() -> bool:
        if len(mapped) == len(color_ids):
            return True
        remaining = [color for color in color_ids if color not in mapped]
        color = min(
            remaining,
            key=lambda candidate: (
                sum(
                    1
                    for pair in domains[candidate]
                    if not (set(pair.horario_ids) & used_ids)
                    and all(
                        other not in mapped
                        or frozenset((candidate, other)) not in constraints
                        or _same_day_adjacent(pair, mapped[other])
                        or pair.day != mapped[other].day
                        for other in remaining
                        if other != candidate
                    )
                ),
                candidate,
            ),
        )
        for pair in domains[color]:
            pair_ids = set(pair.horario_ids)
            if pair_ids & used_ids:
                continue
            valid = True
            for other, other_pair in mapped.items():
                if frozenset((color, other)) in constraints:
                    same_day = pair.day == other_pair.day
                    if same_day and not _same_day_adjacent(pair, other_pair):
                        valid = False
                        break
            if not valid:
                continue
            mapped[color] = pair
            used_ids.update(pair_ids)
            if search():
                return True
            used_ids.difference_update(pair_ids)
            del mapped[color]
        return False

    if not search():
        raise ValueError(
            "Não há combinação de pares de horários que respeite a sequência "
            "das disciplinas de 60h."
        )
    return {color: mapped[color].horario_ids for color in color_ids}


def color_and_assign_slots(
    graph: GraphDatabase,
    max_colors: Optional[int] = None,
) -> Dict[str, Dict[str, object]]:
    """Color the graph and attach two consecutive real slot IDs per chunk."""
    colors = color_allocations(graph, max_colors=max_colors)
    slot_ids = map_colors_to_slots(graph, colors)
    results: Dict[str, Dict[str, object]] = {}
    for vertex, color in colors.items():
        assignment = {"color": color, "horario_ids": slot_ids[color]}
        results[vertex] = assignment
        allocation_id = vertex.split("#30h:", maxsplit=1)[0]
        stored = graph.nodes[allocation_id]["properties"]["assignments"]
        next(item for item in stored if item["vertex"] == vertex).update(assignment)

    return results
