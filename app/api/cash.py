# app/api/cash.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import func, exists
from app.extensions import db
from app.models.catalog import Cash, CashRegister
from app.api.users import roles_required  # reutilizamos tu decorador

bp = Blueprint("cash", __name__)

# --- Helpers ---
def _cash_to_dict(c: Cash):
    if hasattr(c, "to_dict"):
        try:
            return c.to_dict()
        except Exception:
            pass
    return {
        "id": getattr(c, "id", None),
        "description": getattr(c, "description", None),
        "p_expedition": getattr(c, "p_expedition", None),
        "status": getattr(c, "status", None),
    }

def _to_int(value, field_name):
    """Convierte a int o lanza ValueError con mensaje claro."""
    if value is None or value == "":
        raise ValueError(f"{field_name} es obligatorio")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} debe ser numérico")

# GET /api/cash/
@bp.get("/")
@jwt_required()
def get_cash_list():
    items = Cash.query.order_by(Cash.id.asc()).all()
    return jsonify([_cash_to_dict(c) for c in items]), 200

# GET /api/cash/<cash_id>
@bp.get("/<int:cash_id>")
@jwt_required()
def get_cash(cash_id):
    c = Cash.query.get_or_404(cash_id)
    return jsonify(_cash_to_dict(c)), 200

# POST /api/cash/
@bp.post("/")
@roles_required(["Admin"])
def create_cash():
    data = request.get_json() or {}
    desc   = (data.get("description") or "").strip()
    status = (data.get("status") or "OPEN").strip() or "OPEN"

    try:
        pexp = _to_int(data.get("p_expedition"), "p_expedition")
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    # Unicidad por p_expedition (ajusta la regla si lo quieres por sucursal, etc.)
    dup = Cash.query.filter(Cash.p_expedition == pexp).first()
    if dup:
        return jsonify({"error": "Ya existe una caja con ese p_expedition"}), 400

    try:
        new_cash = Cash(description=desc, p_expedition=pexp, status=status)
        db.session.add(new_cash)
        db.session.commit()
        return jsonify(_cash_to_dict(new_cash)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creando Cash")
        return jsonify({"error": "No se pudo crear", "details": str(e)}), 400

# PUT /api/cash/<cash_id>
@bp.put("/<int:cash_id>")
@roles_required(["Admin"])
def update_cash(cash_id):
    c = Cash.query.get_or_404(cash_id)
    data = request.get_json() or {}

    new_desc = (data.get("description", c.description) or "").strip()
    new_stat = (data.get("status", c.status) or "").strip() or c.status

    try:
        new_pexp = _to_int(data.get("p_expedition", c.p_expedition), "p_expedition")
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    # Si cambia p_expedition, controlar unicidad con enteros
    if new_pexp != c.p_expedition:
        dup = Cash.query.filter(Cash.p_expedition == new_pexp, Cash.id != cash_id).first()
        if dup:
            return jsonify({"error": "Ya existe otra caja con ese p_expedition"}), 400

    try:
        c.description  = new_desc
        c.status       = new_stat
        c.p_expedition = new_pexp
        db.session.commit()
        return jsonify(_cash_to_dict(c)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error actualizando Cash")
        return jsonify({"error": "No se pudo actualizar", "details": str(e)}), 400

# DELETE /api/cash/<cash_id>
@bp.delete("/<int:cash_id>")
@roles_required(["Admin"])
def delete_cash(cash_id):
    c = Cash.query.get_or_404(cash_id)

    # Evitar borrar si se usa en CashRegister (ajusta si prefieres soft delete)
    en_uso = db.session.query(exists().where(CashRegister.cash_id == cash_id)).scalar()
    if en_uso:
        return jsonify({"error": "No se puede eliminar: existen registros de caja asociados"}), 400

    try:
        db.session.delete(c)
        db.session.commit()
        return jsonify({"msg": "Caja eliminada"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error eliminando Cash")
        return jsonify({"error": "No se pudo eliminar", "details": str(e)}), 400
