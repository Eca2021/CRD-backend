# app/api/permisos.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import asc, func
from app.extensions import db
from app.models.catalog import Permiso  # ajusta si tu ruta de modelos difiere
from app.api.users import roles_required  # mismo decorador que usas en roles

bp = Blueprint("permisos", __name__)

def perm_to_dto(p: Permiso):
    """
    Transforma el modelo a lo que espera el frontend:
    - codigo          -> viene de p.nombre_permiso (DB)
    - nombre_permiso  -> viene de p.descripcion (DB)
    """
    return {
        "id_permiso": p.id_permiso,
        "codigo": p.nombre,
        "nombre_permiso": p.descripcion,
    }

@bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def list_permissions():
    try:
        rows = Permiso.query.order_by(asc(Permiso.id_permiso)).all()
        return jsonify([perm_to_dto(p) for p in rows]), 200
    except Exception:
        current_app.logger.exception("Error listando permisos")
        return jsonify({"error": "Error interno al listar permisos"}), 500

@bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required(["Admin"])
def create_permission():
    data = request.get_json() or {}

    # Lo que envía el front:
    codigo = (data.get("codigo") or "").strip()
    nombre_legible = (data.get("nombre_permiso") or "").strip()
    # Acepta también 'descripcion' por si alguna UI lo manda así:
    if not nombre_legible:
        nombre_legible = (data.get("descripcion") or "").strip()

    if not codigo or not nombre_legible:
        return jsonify({"error": "codigo y nombre_permiso (descripción) son obligatorios"}), 400

    try:
        # Unicidad sobre el código (DB.nombre)
        dup = Permiso.query.filter(func.lower(Permiso.nombre) == codigo.lower()).first()
        if dup:
            return jsonify({"error": "El código ya existe"}), 409

        p = Permiso(
            nombre=codigo,   # <-- código (slug)
            descripcion=nombre_legible  # <-- texto legible
        )
        db.session.add(p)
        db.session.commit()
        return jsonify(perm_to_dto(p)), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error creando permiso")
        return jsonify({"error": "Error interno al crear permiso"}), 500

@bp.route("/<int:id_permiso>", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_permission(id_permiso):
    try:
        p = Permiso.query.get(id_permiso)
        if not p:
            return jsonify({"error": "Permiso no encontrado"}), 404
        return jsonify(perm_to_dto(p)), 200
    except Exception:
        current_app.logger.exception("Error obteniendo permiso")
        return jsonify({"error": "Error interno al obtener permiso"}), 500

@bp.route("/<int:id_permiso>", methods=["PUT"], strict_slashes=False)
@roles_required(["Admin"])
def update_permission(id_permiso):
    data = request.get_json() or {}
    try:
        p = Permiso.query.get(id_permiso)
        if not p:
            return jsonify({"error": "Permiso no encontrado"}), 404

        new_codigo = (data.get("codigo") or p.nombre or "").strip()
        new_nombre_legible = (data.get("nombre_permiso") or data.get("descripcion") or p.descripcion or "").strip()

        if not new_codigo or not new_nombre_legible:
            return jsonify({"error": "codigo y nombre_permiso (descripción) son obligatorios"}), 400

        # Si cambió el código, validar unicidad
        if new_codigo.lower() != (p.nombre or "").lower():
            dup = Permiso.query.filter(
                func.lower(Permiso.nombre) == new_codigo.lower(),
                Permiso.id_permiso != id_permiso
            ).first()
            if dup:
                return jsonify({"error": "El código ya existe"}), 409

        p.nombre = new_codigo
        p.descripcion = new_nombre_legible
        db.session.commit()
        return jsonify(perm_to_dto(p)), 200
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error actualizando permiso")
        return jsonify({"error": "Error interno al actualizar permiso"}), 500

@bp.route("/<int:id_permiso>", methods=["DELETE"], strict_slashes=False)
@roles_required(["Admin"])
def delete_permission(id_permiso):
    try:
        p = Permiso.query.get(id_permiso)
        if not p:
            return jsonify({"error": "Permiso no encontrado"}), 404
        db.session.delete(p)
        db.session.commit()
        return jsonify({"msg": "Permiso eliminado"}), 200
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error eliminando permiso")
        return jsonify({"error": "Error interno al eliminar permiso"}), 500
