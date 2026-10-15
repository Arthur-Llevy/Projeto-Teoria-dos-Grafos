"""Color timetable meetings loaded from the application's SQLite database.

The SQLite database remains the source of truth. The graph is its in-memory
representation, used here to build and solve the allocation conflict graph.
Each 15 hours of discipline workload represents one weekly 50-minute meeting.
"""

from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

from src.graph.graph_db import GraphDatabase

VERTEX_TYPE = "alocacao"
DISCIPLINE_RELATION = "MINISTRA"
PROFESSOR_RELATION = "ALOCADO_EM"
SLOT_NODE_TYPE = "horario"
HOURS_PER_MEETING = 15


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
    if workload <= 0 or workload % HOURS_PER_MEETING:
        raise ValueError(
            f"A carga horária da disciplina {discipline['id']} deve ser positiva "
            f"e múltipla de {HOURS_PER_MEETING}h para representar aulas de 50 minutos."
        )
    return workload


def _vertices_by_allocation(graph: GraphDatabase) -> Dict[str, List[str]]:
    """Create one vertex for every 50-minute meeting in a weekly schedule."""
    vertices: Dict[str, List[str]] = {}
    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        discipline = _discipline_for_allocation(graph, allocation)
        if discipline is None:
            raise ValueError(
                f"A alocação {allocation['id']} não está vinculada a uma disciplina."
            )
        meeting_count = _discipline_workload(discipline) // HOURS_PER_MEETING
        vertices[allocation["id"]] = [
            f"{allocation['id']}#50min:{index}"
            for index in range(1, meeting_count + 1)
        ]
    return vertices


def _connect_group(adjacency: Dict[str, Set[str]], vertices: Iterable[str]) -> None:
    members = list(vertices)
    for index, vertex in enumerate(members):
        for other in members[index + 1 :]:
            if vertex != other:
                adjacency[vertex].add(other)
                adjacency[other].add(vertex)


def build_conflict_graph(graph: GraphDatabase) -> Dict[str, Set[str]]:
    """Build conflicts for teachers, required course periods, and class meetings.

    Meetings belonging to one allocation must use distinct periods. Grouping by
    allocation is sufficient for the same-class constraint; grouping every row
    with the same discipline ID would also conflict separate offerings of that
    discipline and duplicate conflicts already covered by course and period.
    """
    vertices_by_allocation = _vertices_by_allocation(graph)
    vertices = {
        vertex
        for allocation_vertices in vertices_by_allocation.values()
        for vertex in allocation_vertices
    }
    adjacency: Dict[str, Set[str]] = {vertex: set() for vertex in vertices}
    curricular_groups: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    professor_groups: Dict[str, List[str]] = defaultdict(list)

    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        allocation_id = allocation["id"]
        allocation_vertices = vertices_by_allocation[allocation_id]
        # Each weekly meeting of the same offering is a different period.
        _connect_group(adjacency, allocation_vertices)

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

        professor_id = _professor_for_allocation(graph, allocation)
        if professor_id is not None:
            professor_groups[professor_id].extend(allocation_vertices)

    for group in curricular_groups.values():
        _connect_group(adjacency, group)
    for group in professor_groups.values():
        _connect_group(adjacency, group)
    return adjacency


def validate_coloring(
    adjacency: Dict[str, Set[str]], colors: Dict[str, int]
) -> None:
    missing = set(adjacency) - set(colors)
    if missing:
        raise ValueError(f"Aulas sem cor: {', '.join(sorted(missing))}")

    for vertex, neighbors in adjacency.items():
        for neighbor in neighbors:
            if colors[vertex] == colors[neighbor]:
                raise ValueError(
                    f"Conflito: {vertex} e {neighbor} receberam "
                    f"a cor {colors[vertex]}."
                )


def color_allocations(
    graph: GraphDatabase, max_colors: Optional[int] = None
) -> Dict[str, int]:
    """Color meeting vertices with deterministic DSatur, using DB slot count."""
    if max_colors is not None and max_colors < 1:
        raise ValueError("max_colors deve ser maior que zero.")

    adjacency = build_conflict_graph(graph)
    available_slots = len(graph.get_nodes_by_type(SLOT_NODE_TYPE))
    if max_colors is None:
        max_colors = available_slots
    if adjacency and max_colors < 1:
        raise ValueError("O banco não contém horários para alocar as aulas.")

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
            (
                candidate
                for candidate in range(1, max_colors + 1)
                if candidate not in unavailable
            ),
            None,
        )
        if color is None:
            raise ValueError(
                f"Não foi possível colorir as aulas com até {max_colors} horários."
            )
        colors[vertex] = color
        uncolored.remove(vertex)

    validate_coloring(adjacency, colors)
    _store_assignments(graph, colors)
    return colors


def _store_assignments(graph: GraphDatabase, colors: Dict[str, int]) -> None:
    """Store color results on allocation nodes, grouped by allocation."""
    grouped: Dict[str, List[Dict[str, int]]] = defaultdict(list)
    for vertex, color in colors.items():
        allocation_id = vertex.split("#50min:", maxsplit=1)[0]
        grouped[allocation_id].append({"vertex": vertex, "color": color})

    for allocation_id, assignments in grouped.items():
        assignments.sort(
            key=lambda assignment: int(
                assignment["vertex"].rsplit(":", maxsplit=1)[1]
            )
        )
        graph.nodes[allocation_id]["properties"]["assignments"] = assignments


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
        hours, minutes = str(value).split(":")[:2]
        return int(hours) * 60 + int(minutes)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Horário inválido: {value!r}.") from exc


def _day(slot: Dict) -> str:
    properties = slot["properties"]
    return str(properties.get("dia_semana", properties.get("dia", "")))


def _slot_id(slot: Dict) -> int:
    raw_id = slot["properties"].get(
        "hor_id", slot["id"].removeprefix("hor:")
    )
    try:
        return int(raw_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"O nó de horário {slot['id']} não tem hor_id inteiro."
        ) from exc


def _adjacent(first: Dict, second: Dict) -> bool:
    return _day(first) == _day(second) and (
        _minute(first["properties"].get("hora_fim", ""))
        == _minute(second["properties"].get("hora_inicio", ""))
        or _minute(second["properties"].get("hora_fim", ""))
        == _minute(first["properties"].get("hora_inicio", ""))
    )


def _consecutive(slots: List[Dict]) -> bool:
    if not slots or len({_day(slot) for slot in slots}) != 1:
        return False
    ordered = sorted(
        slots, key=lambda slot: _minute(slot["properties"].get("hora_inicio", ""))
    )
    return all(_adjacent(left, right) for left, right in zip(ordered, ordered[1:]))


def _allocation_groups(
    graph: GraphDatabase,
) -> List[Tuple[List[str], int]]:
    vertices_by_allocation = _vertices_by_allocation(graph)
    groups = []
    for allocation in graph.get_nodes_by_type(VERTEX_TYPE):
        discipline = _discipline_for_allocation(graph, allocation)
        groups.append(
            (
                vertices_by_allocation[allocation["id"]],
                _discipline_workload(discipline),
            )
        )
    return groups


def _valid_allocation_slots(slots: List[Dict], workload: int) -> bool:
    if workload == 30:
        return len(slots) == 2 and _consecutive(slots)
    if workload == 45:
        return len(slots) == 3 and _consecutive(slots)
    if workload == 60:
        if len(slots) != 4:
            return False
        if _consecutive(slots):
            return True
        first_pair = slots[:2]
        second_pair = slots[2:]
        return (
            _consecutive(first_pair)
            and _consecutive(second_pair)
            and _day(first_pair[0]) != _day(second_pair[0])
        )
    return True


def _has_consecutive_completion(
    group_colors: List[int], mapped: Dict[int, Dict], all_slots: List[Dict]
) -> bool:
    group_color_set = set(group_colors)
    assigned = {
        color: mapped[color]
        for color in group_colors
        if color in mapped
    }
    if not assigned:
        return True

    day_slots: Dict[str, List[Dict]] = defaultdict(list)
    for slot in all_slots:
        day_slots[_day(slot)].append(slot)

    for slots_for_day in day_slots.values():
        slots_for_day.sort(
            key=lambda slot: _minute(slot["properties"].get("hora_inicio", ""))
        )
        for start in range(len(slots_for_day) - len(group_colors) + 1):
            run = slots_for_day[start : start + len(group_colors)]
            if not _consecutive(run):
                continue
            run_ids = {_slot_id(slot) for slot in run}
            if not all(_slot_id(slot) in run_ids for slot in assigned.values()):
                continue
            occupied_by_other_color = any(
                _slot_id(slot) in {
                    _slot_id(mapped_slot)
                    for color, mapped_slot in mapped.items()
                    if color not in group_color_set
                }
                for slot in run
            )
            if not occupied_by_other_color:
                return True
    return False


def _partial_allocation_slots_valid(
    group_colors: List[int],
    workload: int,
    mapped: Dict[int, Dict],
    all_slots: List[Dict],
) -> bool:
    if workload in (30, 45):
        consecutive_groups = [group_colors]
    elif workload == 60:
        consecutive_groups = [group_colors[:2], group_colors[2:]]
    else:
        consecutive_groups = []

    for consecutive_group in consecutive_groups:
        if not _has_consecutive_completion(consecutive_group, mapped, all_slots):
            return False

    if workload == 60 and all(color in mapped for color in group_colors):
        assigned = [mapped[color] for color in group_colors]
        first_day = _day(assigned[0])
        second_day = _day(assigned[2])
        if first_day == second_day and not _consecutive(assigned):
            return False
    return True


def map_colors_to_slots(
    graph: GraphDatabase, colors: Mapping[str, int]
) -> Dict[int, int]:
    """Assign each color a real 50-minute slot ID from the loaded SQLite graph."""
    slots = sorted(graph.get_nodes_by_type(SLOT_NODE_TYPE), key=_slot_sort_key)
    color_ids = sorted(set(colors.values()))
    if len(color_ids) > len(slots):
        raise ValueError(
            f"O grafo usa {len(color_ids)} cores, mas o banco só tem "
            f"{len(slots)} horários."
        )
    if any(color < 1 for color in color_ids):
        raise ValueError("As cores precisam ser índices inteiros a partir de 1.")

    groups = []
    for vertices, workload in _allocation_groups(graph):
        if any(vertex not in colors for vertex in vertices):
            raise ValueError("Uma aula está sem cor atribuída.")
        group_colors = [colors[vertex] for vertex in vertices]
        if len(set(group_colors)) != len(group_colors):
            raise ValueError("Aulas da mesma alocação receberam a mesma cor.")
        groups.append((group_colors, workload))

    mapped: Dict[int, Dict] = {}
    used_slot_ids: Set[int] = set()
    groups_by_color: Dict[int, int] = defaultdict(int)
    for group_colors, workload in groups:
        if workload in (30, 60):
            for color in group_colors:
                groups_by_color[color] += 1

    def search() -> bool:
        if len(mapped) == len(color_ids):
            return all(
                _valid_allocation_slots(
                    [mapped[color] for color in group_colors], workload
                )
                for group_colors, workload in groups
            )

        remaining = [color for color in color_ids if color not in mapped]
        color = max(remaining, key=lambda item: (groups_by_color[item], -item))
        for slot in slots:
            slot_id = _slot_id(slot)
            if slot_id in used_slot_ids:
                continue
            mapped[color] = slot
            used_slot_ids.add(slot_id)
            if all(
                _partial_allocation_slots_valid(
                    group_colors, workload, mapped, slots
                )
                for group_colors, workload in groups
                if workload in (30, 45, 60)
            ) and search():
                return True
            used_slot_ids.remove(slot_id)
            del mapped[color]
        return False

    if not search():
        raise ValueError(
            "Não há combinação de horários reais que respeite os padrões "
            "de 30h e 60h."
        )
    return {color: _slot_id(mapped[color]) for color in color_ids}


def color_and_assign_slots(
    graph: GraphDatabase,
    max_colors: Optional[int] = None,
) -> Dict[str, Dict[str, int]]:
    """Color DB-backed class meetings and attach their real ``hor_id`` values."""
    colors = color_allocations(graph, max_colors=max_colors)
    slot_ids = map_colors_to_slots(graph, colors)
    results: Dict[str, Dict[str, int]] = {}
    for vertex, color in colors.items():
        assignment = {"color": color, "horario_id": slot_ids[color]}
        results[vertex] = assignment
        allocation_id = vertex.split("#50min:", maxsplit=1)[0]
        stored = graph.nodes[allocation_id]["properties"]["assignments"]
        next(item for item in stored if item["vertex"] == vertex).update(assignment)
    return results
