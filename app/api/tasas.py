from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.catalog import TasaInteres, Usuario

bp = Blueprint("tasas", __name__)

def permission_required(permission_name):
    # Reusing the logic (could be centralized, but keeping independent for now)
    from functools import wraps
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            user_id = get_jwt_identity()
            user = Usuario.query.get(user_id)
            if not user:
                return jsonify({"message": "Usuario no encontrado"}), 404
            
            # Admin Bypass
            is_admin = any(r.rol.nombre.upper() == 'ADMIN' for r in user.roles)
            if is_admin:
                 return fn(*args, **kwargs)

            # Check permissions
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
@jwt_required() # Allow read for all authenticated users (needed for dropdowns)
def get_tasas():
    tasas = TasaInteres.query.order_by(TasaInteres.porcentaje.asc()).all()
    return jsonify([t.to_dict() for t in tasas]), 200

@bp.post("/")
@permission_required("tasa.gestionar") # Assuming this permission exists or will be created/used by Admin
def create_tasa():
    data = request.get_json() or {}
    nombre = (data.get("nombre_tasa") or "").strip()
    try:
        porcentaje = float(data.get("porcentaje", 0))
    except:
        return jsonify({"message": "Porcentaje inválido"}), 400
        
    if not nombre:
        return jsonify({"message": "Nombre de tasa es obligatorio"}), 400
    
    nuevo = TasaInteres(
        nombre_tasa=nombre,
        porcentaje=porcentaje,
        descripcion=data.get("descripcion")
    )
    
    try:
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"message": "Tasa creada", "tasa": nuevo.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creando tasa", "error": str(e)}), 500

@bp.put("/<int:id_tasa>")
@permission_required("tasa.gestionar")
def update_tasa(id_tasa):
    tasa = TasaInteres.query.get(id_tasa)
    if not tasa:
        return jsonify({"message": "Tasa no encontrada"}), 404
        
    data = request.get_json() or {}
    tasa.nombre_tasa = data.get("nombre_tasa", tasa.nombre_tasa)
    tasa.descripcion = data.get("descripcion", tasa.descripcion)
    if "porcentaje" in data:
         try:
            tasa.porcentaje = float(data["porcentaje"])
         except:
             return jsonify({"message": "Porcentaje inválido"}), 400

    try:
        db.session.commit()
        return jsonify({"message": "Tasa actualizada", "tasa": tasa.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error actualizando tasa", "error": str(e)}), 500

@bp.delete("/<int:id_tasa>")
@permission_required("tasa.gestionar")
def delete_tasa(id_tasa):
    tasa = TasaInteres.query.get(id_tasa)
    if not tasa:
        return jsonify({"message": "Tasa no encontrada"}), 404
        
    try:
        db.session.delete(tasa)
        db.session.commit()
        return jsonify({"message": "Tasa eliminada"}), 200
    except Exception as e:
        db.session.rollback()
        # Likely constraint violation if used in credits
        return jsonify({"message": "Error eliminando tasa (¿está en uso?)", "error": str(e)}), 500
