# app/api/company_settings.py

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.catalog import CompanySetting

bp = Blueprint("company_settings", __name__)

def _cors_preflight_response():
    resp = make_response("", 204)
    # Si usás Flask-CORS global, estos headers no son necesarios
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, PUT, OPTIONS"
    return resp

@bp.route("/company_settings", methods=["OPTIONS"], strict_slashes=False)
@bp.route("/company-settings", methods=["OPTIONS"], strict_slashes=False)
def company_settings_preflight():
    return _cors_preflight_response()

@bp.route("/company_settings", methods=["GET"], strict_slashes=False)
@bp.route("/company-settings", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_company_settings():
    cs = CompanySetting.query.first()
    if not cs:
        return jsonify({"message": "Configuración de la empresa no encontrada."}), 404
    return jsonify(cs.to_dict()), 200

@bp.route("/company_settings", methods=["PUT"], strict_slashes=False)
@bp.route("/company-settings", methods=["PUT"], strict_slashes=False)
@jwt_required()
def update_company_settings():
    data = request.get_json(silent=True) or {}
    allowed = {"name", "ruc", "address", "phone", "email", "logo_url"}

    cs = CompanySetting.query.first()
    if not cs:
        cs = CompanySetting()
        db.session.add(cs)

    for k in allowed:
        if k in data:
            setattr(cs, k, data[k])

    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "No se pudo guardar la configuración.", "error": str(e)}), 400

    return jsonify(cs.to_dict()), 200
