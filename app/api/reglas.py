from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.catalog import ReglaCredito, TasaInteres, Usuario

bp = Blueprint("reglas", __name__)

def permission_required(permission_name):
    from functools import wraps
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            user_id = get_jwt_identity()
            user = Usuario.query.get(user_id)
            if not user:
                return jsonify({"message": "Usuario no encontrado"}), 404
            
            is_admin = any(r.rol.nombre.upper() == 'ADMIN' for r in user.roles)
            if is_admin:
                 return fn(*args, **kwargs)

            has_perm = False
            for ur in user.roles:
                for rp in ur.rol.permisos_asociados:
                    if rp.permiso.nombre == permission_name:
                        has_perm = True
                        break
                if has_perm: break
            
            if not has_perm:
                return jsonify({"message": f"Permiso denegado. Se requiere '{permission_name}'"}), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper

@bp.get("/")
@jwt_required()
def get_reglas():
    reglas = ReglaCredito.query.filter_by(activo=True).all()
    return jsonify([r.to_dict() for r in reglas]), 200

@bp.post("/")
@permission_required("regla.gestionar")
def create_regla():
    data = request.get_json() or {}
    try:
        codigo = data.get("codigo")
        nombre = data.get("nombre")
        porcentaje = float(data.get("porcentaje"))
        dias_intervalo = int(data.get("dias_intervalo", 7))
    except:
        return jsonify({"message": "Datos inválidos"}), 400
        
    if not codigo or not nombre or porcentaje is None:
        return jsonify({"message": "Faltan campos obligatorios"}), 400
        
    nueva = ReglaCredito(
        codigo=codigo,
        nombre=nombre,
        porcentaje=porcentaje,
        dias_intervalo=dias_intervalo
    )
    
    try:
        db.session.add(nueva)
        db.session.commit()
        return jsonify({"message": "Regla creada", "regla": nueva.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creando regla", "error": str(e)}), 500

@bp.put("/<int:id_regla>")
@permission_required("regla.gestionar")
def update_regla(id_regla):
    regla = ReglaCredito.query.get(id_regla)
    if not regla:
        return jsonify({"message": "Regla no encontrada"}), 404
        
    data = request.get_json() or {}
    regla.nombre = data.get("nombre", regla.nombre)
    regla.codigo = data.get("codigo", regla.codigo)
    if "porcentaje" in data:
        regla.porcentaje = float(data.get("porcentaje"))
    regla.dias_intervalo = data.get("dias_intervalo", regla.dias_intervalo)
    regla.activo = data.get("activo", regla.activo)
    
    try:
        db.session.commit()
        return jsonify({"message": "Regla actualizada", "regla": regla.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error actualizando regla", "error": str(e)}), 500

@bp.delete("/<int:id_regla>")
@permission_required("regla.gestionar")
def delete_regla(id_regla):
    regla = ReglaCredito.query.get(id_regla)
    if not regla:
        return jsonify({"message": "Regla no encontrada"}), 404
    
    try:
        regla.activo = False # Soft delete
        db.session.commit()
        return jsonify({"message": "Regla desactivada"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error desactivando regla", "error": str(e)}), 500
