import sqlite3

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from src.graph.graph_db import GraphDatabase
from src.graph.sqlite_loader import load_from_sqlite


professors_bp = Blueprint("professors", __name__)


def _form_context(errors=None, values=None):
    repository = current_app.extensions["professor_repository"]
    return {
        "errors": errors or [],
        "values": values or {},
        "courses": repository.list_courses(),
    }


def _reload_graph():
    repository = current_app.extensions["professor_repository"]
    graph = GraphDatabase()
    if load_from_sqlite(graph, repository.database_path):
        current_app.extensions["graph_db"] = graph


def _professor_detail_context(
    professor_id, errors=None, selected_slot_ids=None
):
    repository = current_app.extensions["professor_repository"]
    professor = repository.get_professor(professor_id)
    if professor is None:
        abort(404)

    slots = repository.list_slots()
    slot_groups = []
    for slot in slots:
        day = slot["hor_dia_semana"]
        if not slot_groups or slot_groups[-1]["day"] != day:
            slot_groups.append({"day": day, "slots": []})
        slot_groups[-1]["slots"].append(slot)
    preferred_slot_ids = repository.list_preferred_slot_ids(professor_id)
    if selected_slot_ids is None:
        selected_slot_ids = preferred_slot_ids

    try:
        required_slot_count = repository.required_slot_count(professor_id)
        workload_error = None
    except ValueError as exc:
        required_slot_count = 0
        workload_error = str(exc)

    min_extra = repository.get_min_extra_slots()
    context_errors = list(errors or [])
    if workload_error:
        context_errors.append(workload_error)

    return {
        "professor": professor,
        "allocations": repository.list_allocated_disciplines(professor_id),
        "available_disciplines": repository.list_available_disciplines(professor_id),
        "slots": slots,
        "slot_groups": slot_groups,
        "selected_slot_ids": set(selected_slot_ids),
        "required_slot_count": required_slot_count,
        "min_extra_slots": min_extra,
        "minimum_preference_count": (
            required_slot_count + min_extra if min_extra is not None else None
        ),
        "errors": context_errors,
        "allocation_created": request.args.get("alocada") == "1",
        "preferences_saved": request.args.get("preferencias") == "salvas",
    }


@professors_bp.get("/professors/new")
def new_professor():
    return render_template("professor_new.html", **_form_context())


@professors_bp.route("/professors", methods=["GET", "POST"])
def professors():
    repository = current_app.extensions["professor_repository"]

    if request.method == "GET":
        return render_template(
            "professors.html",
            professors=repository.list_all(),
            created=request.args.get("created") == "1",
            min_extra_slots=repository.get_min_extra_slots(),
        )

    nome = request.form.get("nome", "").strip()
    matricula = request.form.get("matricula", "").strip()
    curso_raw = request.form.get("curso_id", "").strip()
    errors = []

    if not nome:
        errors.append("Informe o nome do professor.")
    elif len(nome) > 100:
        errors.append("O nome deve ter no máximo 100 caracteres.")

    if not matricula:
        errors.append("Informe a matrícula do professor.")
    elif len(matricula) > 20:
        errors.append("A matrícula deve ter no máximo 20 caracteres.")
    elif repository.has_matricula(matricula):
        errors.append("Já existe um professor com essa matrícula.")

    try:
        curso_id = int(curso_raw)
    except (TypeError, ValueError):
        curso_id = None
    courses = repository.list_courses()
    valid_course_ids = {course["id"] for course in courses}
    if curso_id not in valid_course_ids:
        errors.append("Selecione um curso válido.")

    values = {"nome": nome, "matricula": matricula, "curso_id": curso_raw}
    if errors:
        return render_template(
            "professor_new.html", **_form_context(errors, values)
        ), 400

    try:
        repository.create(nome, matricula, curso_id)
    except sqlite3.IntegrityError:
        return render_template(
            "professor_new.html",
            **_form_context(["Não foi possível cadastrar o professor."], values),
        ), 400

    return redirect(url_for("professors.professors", created="1"), code=303)


@professors_bp.route("/professors/<int:professor_id>/alocacoes", methods=["GET", "POST"])
def professor_allocations(professor_id):
    repository = current_app.extensions["professor_repository"]
    if repository.get_professor(professor_id) is None:
        abort(404)

    if request.method == "POST":
        try:
            discipline_id = int(request.form.get("dis_id", ""))
            repository.add_allocation(professor_id, discipline_id)
        except (ValueError, sqlite3.IntegrityError) as exc:
            message = str(exc) or "Não foi possível alocar a disciplina."
            return render_template(
                "professor_detail.html",
                **_professor_detail_context(professor_id, errors=[message]),
            ), 400
        _reload_graph()
        return redirect(
            url_for("professors.professor_allocations", professor_id=professor_id,
                    alocada="1"),
            code=303,
        )

    return render_template(
        "professor_detail.html",
        **_professor_detail_context(professor_id),
    )


@professors_bp.post("/professors/<int:professor_id>/preferencias")
def save_professor_preferences(professor_id):
    repository = current_app.extensions["professor_repository"]
    if repository.get_professor(professor_id) is None:
        abort(404)

    raw_slot_ids = request.form.getlist("hor_ids")
    selected_slot_ids = set()
    errors = []

    try:
        selected_slot_ids = {int(slot_id) for slot_id in raw_slot_ids}
    except ValueError:
        errors.append("A seleção contém um horário inválido.")
        selected_slot_ids = set()

    using_preferences = bool(selected_slot_ids)
    if using_preferences:
        min_extra = repository.get_min_extra_slots()
        if min_extra is None:
            errors.append(
                "O coordenador precisa configurar N antes de cadastrar preferências."
            )

        valid_slot_ids = {slot["hor_id"] for slot in repository.list_slots()}
        if not selected_slot_ids.issubset(valid_slot_ids):
            errors.append("Selecione apenas horários existentes no banco.")

        try:
            required_slot_count = repository.required_slot_count(professor_id)
        except ValueError as exc:
            required_slot_count = 0
            errors.append(str(exc))

        if min_extra is not None:
            minimum_count = required_slot_count + min_extra
            if minimum_count > len(valid_slot_ids):
                errors.append(
                    "Não há horários cadastrados suficientes para cobrir a carga "
                    "do professor mais o excedente mínimo configurado."
                )
            elif len(selected_slot_ids) < minimum_count:
                errors.append(
                    f"Selecione pelo menos {minimum_count} horários: "
                    f"{required_slot_count} para a carga alocada e {min_extra} excedentes."
                )

    if errors:
        return render_template(
            "professor_detail.html",
            **_professor_detail_context(
                professor_id,
                errors=errors,
                selected_slot_ids=selected_slot_ids,
            ),
        ), 400

    repository.save_preferred_slots(
        professor_id, sorted(selected_slot_ids) if using_preferences else []
    )
    return redirect(
        url_for("professors.professor_allocations", professor_id=professor_id,
                preferencias="salvas"),
        code=303,
    )


@professors_bp.route("/settings/horarios-preferidos", methods=["GET", "POST"])
def configure_min_extra_slots():
    repository = current_app.extensions["professor_repository"]
    errors = []
    value = repository.get_min_extra_slots()

    if request.method == "POST":
        raw_value = request.form.get("min_horarios_excedentes", "").strip()
        try:
            new_value = int(raw_value)
            if new_value < 0:
                raise ValueError
        except ValueError:
            new_value = None
            errors.append("N deve ser um número inteiro maior ou igual a zero.")

        if new_value is not None:
            slot_count = len(repository.list_slots())
            if new_value > slot_count:
                errors.append(
                    f"N não pode ser maior que a quantidade de horários cadastrados ({slot_count})."
                )

        if new_value is not None and not errors:
            for professor in repository.professors_with_preferences():
                try:
                    required = repository.required_slot_count(professor["pro_id"])
                except ValueError as exc:
                    errors.append(str(exc))
                    break
                if professor["slot_count"] < required + new_value:
                    errors.append(
                        "O novo N invalidaria as preferências de "
                        f"{professor['pro_nome']}; atualize-as antes de alterar o parâmetro."
                    )
                    break

        if new_value is not None and not errors:
            repository.set_min_extra_slots(new_value)
            return redirect(url_for("professors.configure_min_extra_slots", salvo="1"), code=303)
        value = raw_value

    return render_template(
        "preference_settings.html",
        errors=errors,
        value=value,
        saved=request.args.get("salvo") == "1",
        slot_count=len(repository.list_slots()),
    ), 400 if errors else 200
