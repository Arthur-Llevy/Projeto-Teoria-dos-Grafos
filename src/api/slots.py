from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for


slots_bp = Blueprint("slots", __name__)


def _wants_json() -> bool:
    preferred = request.accept_mimetypes.best_match(
        ["application/json", "text/html"], default="application/json"
    )
    return preferred == "application/json"


@slots_bp.route("/slots/new", methods=["GET"])
def new_slot():
    return render_template("slot_new.html", errors=[], values={})


@slots_bp.route("/slots", methods=["GET", "POST"])
def slots():
    repository = current_app.extensions["slot_repository"]

    if request.method == "GET":
        slot_list = repository.list_all()
        if _wants_json():
            return jsonify(slot_list)
        return render_template(
            "slots.html",
            slots=slot_list,
            created=request.args.get("created") == "1",
        )

    is_form = not request.is_json
    payload = request.form.to_dict() if is_form else request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Envie os dados do slot como formulário ou JSON"}), 400

    try:
        slot = repository.create(
            payload.get("dia_semana"),
            payload.get("bloco"),
            payload.get("hora_inicio"),
            payload.get("hora_fim"),
        )
    except ValueError as exc:
        if is_form:
            return (
                render_template(
                    "slot_new.html",
                    errors=[str(exc)],
                    values=payload,
                ),
                400,
            )
        return jsonify({"errors": [str(exc)]}), 400

    if is_form:
        return redirect(url_for("slots.slots", created="1"), code=303)
    return jsonify(slot), 201
