# app/api/empresas.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from app.extensions import db
from app.models.catalog import Empresa
from app.api.users import roles_required

bp = Blueprint("empresas", __name__)

@bp.get("/", strict_slashes=False)
@roles_required(["SuperAdmin", "Admin"])
def get_empresas():
    """Listar todas las empresas registradas."""
    empresas = Empresa.query.order_by(Empresa.id_empresa.asc()).all()
    return jsonify([e.to_dict() for e in empresas]), 200

@bp.post("/", strict_slashes=False)
@roles_required(["SuperAdmin"])
def create_empresa():
    """Registrar una nueva empresa (Tenant)."""
    data = request.get_json() or {}
    nombre = (data.get("nombre") or "").strip()
    ruc = (data.get("ruc") or "").strip()
    direccion = data.get("direccion")
    phone = data.get("phone")
    email = data.get("email")
    logo_url = data.get("logo_url")

    if not nombre or not ruc:
        return jsonify({"message": "Nombre y RUC son requeridos"}), 400

    # Unicidad RUC
    if Empresa.query.filter(Empresa.ruc == ruc).first():
        return jsonify({"message": f"El RUC {ruc} ya está registrado"}), 409

    try:
        nueva = Empresa(
            nombre=nombre,
            ruc=ruc,
            direccion=direccion,
            phone=phone,
            email=email,
            logo_url=logo_url
        )
        db.session.add(nueva)
        db.session.commit()
        return jsonify({"message": "Empresa creada exitosamente", "empresa": nueva.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error al crear empresa")
        return jsonify({"message": "Error interno al crear empresa", "error": str(e)}), 500

@bp.put("/<int:id_empresa>", strict_slashes=False)
@roles_required(["SuperAdmin", "Admin"])
def update_empresa(id_empresa):
    """Actualizar datos de una empresa."""
    # Si es Admin (no SuperAdmin), solo puede editar SU propia empresa
    claims = get_jwt()
    is_super = "SUPERADMIN" in [r.upper() for r in claims.get("roles", [])]
    
    if not is_super and claims.get("id_empresa") != id_empresa:
        return jsonify({"message": "No tienes permiso para editar esta empresa"}), 403

    empresa = Empresa.query.get(id_empresa)
    if not empresa:
        return jsonify({"message": "Empresa no encontrada"}), 404

    data = request.get_json() or {}
    
    if "nombre" in data: empresa.nombre = data["nombre"].strip()
    if "ruc" in data: empresa.ruc = data["ruc"].strip()
    if "direccion" in data: empresa.direccion = data["direccion"]
    if "phone" in data: empresa.phone = data["phone"]
    if "email" in data: empresa.email = data["email"]
    if "logo_url" in data: empresa.logo_url = data["logo_url"]

    try:
        db.session.commit()
        return jsonify({"message": "Datos de empresa actualizados", "empresa": empresa.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error al actualizar empresa", "error": str(e)}), 500
