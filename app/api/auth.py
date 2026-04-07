# app/api/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from app.extensions import db, jwt  # usa las extensiones inicializadas
from app.models.catalog import Usuario, Rol, Permiso, UsuarioRol, HistorialAcceso

bp = Blueprint("auth", __name__)

# -----------------------------
# Decorador de roles
# -----------------------------
# -----------SE AGREGA COMENTARIO PARA SABER SI EL PUSH AUTOMATICO FUNCIONE------------------ 
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
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    
    print(f"🕵️ Intento de login - User: [{username}] | PassLen: {len(password)}")
    
    from werkzeug.security import check_password_hash
    from sqlalchemy import func
    
    # Búsqueda insensible a mayúsculas y espacios
    user = Usuario.query.filter(func.lower(Usuario.nombre_usuario) == username.lower()).first()
    ip_cliente = request.remote_addr
    user_agent = request.headers.get('User-Agent')

    if not user:
        print(f"❌ Login FALLIDO: Usuario '{username}' no existe en la DB.")
        new_log = HistorialAcceso(
            username_intentado=username,
            evento='LOGIN_FALLIDO',
            ip_cliente=ip_cliente,
            user_agent=user_agent,
            motivo_fallo='Usuario no encontrado'
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"msg": "Credenciales inválidas"}), 401

    if not check_password_hash(user.password_hash, password):
        print(f"❌ Login FALLIDO: Contraseña incorrecta para el usuario '{username}'.")
        new_log = HistorialAcceso(
            id_usuario=user.id_usuario,
            id_empresa=user.id_empresa,
            username_intentado=username,
            evento='LOGIN_FALLIDO',
            ip_cliente=ip_cliente,
            user_agent=user_agent,
            motivo_fallo='Contraseña incorrecta'
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"msg": "Credenciales inválidas"}), 401

    if user.estado != 'ACTIVO':
        new_log = HistorialAcceso(
            id_usuario=user.id_usuario,
            id_empresa=user.id_empresa,
            username_intentado=username,
            evento='LOGIN_FALLIDO',
            ip_cliente=ip_cliente,
            user_agent=user_agent,
            motivo_fallo=f'Usuario con estado: {user.estado}'
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"msg": f"El usuario se encuentra {user.estado}"}), 403

    access  = create_access_token(identity=str(user.id_usuario))
    refresh = create_refresh_token(identity=str(user.id_usuario))

    # permisos desde roles
    permisos = []
    for ur in user.roles:
        for rp in ur.rol.permisos_asociados:
            p = rp.permiso
            if p.nombre not in permisos:
                permisos.append(p.nombre)

    # Registro de login exitoso
    new_log = HistorialAcceso(
        id_usuario=user.id_usuario,
        id_empresa=user.id_empresa,
        username_intentado=username,
        evento='LOGIN_EXITOSO',
        ip_cliente=ip_cliente,
        user_agent=user_agent
    )
    db.session.add(new_log)
    db.session.commit()

    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "username": user.nombre_usuario,
        "user_roles": [r.rol.nombre for r in user.roles],
        "user_permissions": permisos,
        "user_id": str(user.id_usuario),
        "id_empresa": user.id_empresa,
        "empresa_nombre": user.empresa.nombre if user.empresa else None,
        "is_global": getattr(user, 'is_global', False)
    })

@bp.post("/logout")
@jwt_required()
def logout():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    
    new_log = HistorialAcceso(
        id_usuario=user.id_usuario if user else None,
        username_intentado=user.nombre_usuario if user else None,
        evento='LOGOUT',
        ip_cliente=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(new_log)
    db.session.commit()
    return jsonify({"msg": "Sesión cerrada correctamente"}), 200

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
        id_empresa = user.id_empresa if user else None
        is_global = getattr(user, 'is_global', False)
        return {"roles": roles, "id_empresa": id_empresa, "is_global": is_global}

    @jwt_manager.user_lookup_loader
    def user_lookup_callback(jwt_header, jwt_data):
        identity = jwt_data.get("sub")
        try:
            identity_int = int(identity)
        except Exception:
            return None
        return Usuario.query.filter_by(id_usuario=identity_int).one_or_none()
