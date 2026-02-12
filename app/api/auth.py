# app/api/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from app.extensions import db, jwt  # usa las extensiones inicializadas
from app.models.catalog import Usuario, Rol, Permiso, UsuarioRol

bp = Blueprint("auth", __name__)

# -----------------------------
# Decorador de roles
# -----------------------------
def roles_required(roles):
    """
    Uso: @roles_required(['Admin', 'Gerente'])
    """
    from functools import wraps
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            roles = [r.upper() for r in (claims.get("roles", []) or [])]
            required_upper = [r.upper() for r in (roles or [])]
            if not any(r in roles for r in required_upper):
                return jsonify({"msg": "Permiso denegado: No tienes los roles necesarios."}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# -----------------------------
# Endpoints Auth
# -----------------------------
@bp.post("/login")
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    user = Usuario.query.filter_by(nombre_usuario=username).first()
    from werkzeug.security import check_password_hash

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Credenciales inválidas"}), 401

    access  = create_access_token(identity=str(user.id_usuario))
    refresh = create_refresh_token(identity=str(user.id_usuario))

    # permisos desde roles
    permisos = []
    for ur in user.roles:
        for rp in ur.rol.permisos_asociados:
            p = rp.permiso
            if p.nombre not in permisos:
                permisos.append(p.nombre)

    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "username": user.nombre_usuario,
        "user_roles": [r.rol.nombre for r in user.roles],
        "user_permissions": permisos,
        "user_id": str(user.id_usuario),
    })

@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh_token():
    current_user = get_jwt_identity()
    return jsonify(access_token=create_access_token(identity=current_user))

# -----------------------------
# Callbacks de JWT centralizados
# -----------------------------
def register_jwt_callbacks(jwt_manager):
    @jwt_manager.additional_claims_loader
    def add_claims_to_access_token(identity):
        user = Usuario.query.filter_by(id_usuario=int(identity)).first()
        roles = [ur.rol.nombre for ur in user.roles] if user else []
        return {"roles": roles}

    @jwt_manager.user_lookup_loader
    def user_lookup_callback(jwt_header, jwt_data):
        identity = jwt_data.get("sub")
        try:
            identity_int = int(identity)
        except Exception:
            return None
        return Usuario.query.filter_by(id_usuario=identity_int).one_or_none()
