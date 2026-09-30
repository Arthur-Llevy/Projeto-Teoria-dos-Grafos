from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for


courses_bp = Blueprint("courses", __name__)


def _wants_json() -> bool:
    preferred = request.accept_mimetypes.best_match(
        ["application/json", "text/html"], default="application/json"
    )
    return preferred == "application/json"


@courses_bp.route("/courses/new", methods=["GET"])
def new_course():
    return render_template("course_new.html", errors=[], values={})


@courses_bp.route("/courses", methods=["GET", "POST"])
def courses():
    repository = current_app.extensions["course_repository"]

    if request.method == "GET":
        course_list = repository.list_all()
        if _wants_json():
            return jsonify(course_list)
        return render_template(
            "courses.html",
            courses=course_list,
            created=request.args.get("created") == "1",
        )

    payload = request.get_json(silent=True)
    is_form = not request.is_json
    if is_form:
        payload = request.form.to_dict()
    if not isinstance(payload, dict):
        return jsonify({"error": "Envie os dados do curso como formulário ou JSON"}), 400

    nome = payload.get("nome")
    descricao = payload.get("descricao", "")
    errors = []
    if not isinstance(nome, str) or not nome.strip():
        errors.append("Informe o nome do curso.")
    if descricao is None:
        descricao = ""
    if not isinstance(descricao, str):
        errors.append("A descrição deve ser texto.")
        descricao = ""
    if isinstance(nome, str) and len(nome.strip()) > 100:
        errors.append("O nome deve ter no máximo 100 caracteres.")
    if isinstance(descricao, str) and len(descricao.strip()) > 100:
        errors.append("A descrição deve ter no máximo 100 caracteres.")

    if errors:
        if is_form:
            return (
                render_template(
                    "course_new.html",
                    errors=errors,
                    values={"nome": nome or "", "descricao": descricao},
                ),
                400,
            )
        return jsonify({"errors": errors}), 400

    course = repository.create(nome.strip(), descricao.strip())
    if is_form:
        return redirect(url_for("courses.courses", created="1"), code=303)
    return jsonify(course), 201
