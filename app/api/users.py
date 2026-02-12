# app/api/users.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_
from functools import wraps
from app.extensions import db
from app.models.catalog import Usuario, Rol, UsuarioRol

bp = Blueprint("users", __name__)

# ---- Decorador de roles ----
def roles_required(required_roles):
    """
    Uso: @roles_required(['Admin'])
    Requiere que el JWT tenga claim "roles" con alguno de required_roles.
    """
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            claims = get_jwt() or {}
            roles = [r.upper() for r in (claims.get("roles", []) or [])]
            required_upper = [r.upper() for r in required_roles]
            if any(r in roles for r in required_upper):
                return fn(*args, **kwargs)
            
            # Log failure for debugging
            current_app.logger.warning(f"Access denied. User roles: {roles}, Required: {required_upper}")
            return jsonify({"message": "No autorizado"}), 403
        return decorated
    return wrapper

# ---- Helpers ----
def _user_to_dict(u: Usuario):
    if hasattr(u, "to_dict"):
        return u.to_dict()
    role_ids = [r[0] for r in db.session.query(UsuarioRol.id_rol).filter_by(id_usuario=u.id_usuario).all()]
    return {
        "id_usuario": getattr(u, "id_usuario", None),
        "nombre_usuario": u.nombre_usuario,
        "nombre": u.nombre,
        "email": u.email,
        "estado": u.estado,
        "roles": role_ids,  # ids; el front ya los mapea a nombres
    }

def _get_current_role_ids(id_usuario: int) -> set:
    rows = db.session.query(UsuarioRol.id_rol).filter_by(id_usuario=id_usuario).all()
    return {r[0] for r in rows}

# ---- Endpoints ----

# CREATE
@bp.post("/")
@roles_required(["Admin"])
def create_user():
    data = request.get_json() or {}
    nombre_usuario = (data.get("nombre_usuario") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    email = (data.get("email") or "").strip() or None
    password = data.get("password")
    estado = (data.get("estado") or "ACTIVO").strip()
    roles_ids = data.get("roles", []) or []

    if not nombre_usuario or not password:
        return jsonify({"message": "Nombre de usuario y contraseña son requeridos"}), 400

    # Unicidad username (case-insensitive)
    if Usuario.query.filter(func.lower(Usuario.nombre_usuario) == nombre_usuario.lower()).first():
        return jsonify({"message": "El nombre de usuario ya existe"}), 409

    # Unicidad email (si viene)
    if email:
        if Usuario.query.filter(func.lower(Usuario.email) == email.lower()).first():
            return jsonify({"message": "El email ya está registrado para otro usuario"}), 409

    # Validar roles
    if roles_ids:
        existentes = {r.id_rol for r in Rol.query.filter(Rol.id_rol.in_(roles_ids)).all()}
        faltantes = [rid for rid in roles_ids if rid not in existentes]
        if faltantes:
            return jsonify({"message": f"Roles inexistentes: {faltantes}"}), 400

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

    try:
        nuevo = Usuario(
            nombre_usuario=nombre_usuario,
            nombre=nombre,
            email=email,
            password_hash=hashed_password,
            estado=estado,
        )
        db.session.add(nuevo)
        db.session.flush()  # genera id_usuario

        for role_id in roles_ids:
            db.session.add(UsuarioRol(id_usuario=nuevo.id_usuario, id_rol=role_id))

        db.session.commit()
        return jsonify({"message": "Usuario creado exitosamente", "user": _user_to_dict(nuevo)}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creando usuario")
        return jsonify({"message": "Error interno del servidor al crear usuario", "error": str(e)}), 500

# READ (única ruta GET con filtros)
@bp.get("/")
@roles_required(["Admin"])
def get_users():
    q       = (request.args.get("q") or "").strip()
    estado  = (request.args.get("estado") or "").strip().upper()
    deleted = (request.args.get("deleted") or "").strip().lower()

    qry = Usuario.query

    # /api/usuarios/?deleted=true  → solo eliminados
    if deleted in ("1", "true", "t", "si", "sí", "yes", "y"):
        qry = qry.filter(func.upper(Usuario.estado) == "ELIMINADO")
    # /api/usuarios/?estado=ACTIVO|INACTIVO|ELIMINADO
    elif estado:
        qry = qry.filter(func.upper(Usuario.estado) == estado)

    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(
            Usuario.nombre_usuario.ilike(like),
            Usuario.nombre.ilike(like),
            Usuario.email.ilike(like),
        ))

    usuarios = qry.order_by(Usuario.id_usuario.asc()).all()
    return jsonify([_user_to_dict(u) for u in usuarios]), 200

# (Opcional) alias claro para eliminados
@bp.get("/deleted")
@roles_required(["Admin"])
def get_deleted_users():
    usuarios = (Usuario.query
                .filter(func.upper(Usuario.estado) == "ELIMINADO")
                .order_by(Usuario.id_usuario.asc())
                .all())
    return jsonify([_user_to_dict(u) for u in usuarios]), 200

# UPDATE
@bp.put("/<int:id_usuario>")
@roles_required(["Admin"])
def update_user(id_usuario):
    user = Usuario.query.get(id_usuario)
    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404

    data = request.get_json() or {}

    user.nombre = data.get("nombre", user.nombre)
    user.estado = data.get("estado", user.estado)

    # Email con unicidad
    new_email = (data.get("email") or "").strip() or None
    if new_email and new_email != (user.email or None):
        exists_email = (
            Usuario.query.filter(
                func.lower(Usuario.email) == new_email.lower(),
                Usuario.id_usuario != id_usuario
            ).first()
        )
        if exists_email:
            return jsonify({"message": "El email ya está registrado para otro usuario"}), 409
        user.email = new_email

    # Password (si viene)
    new_password = data.get("password")
    if new_password:
        user.password_hash = generate_password_hash(new_password, method="pbkdf2:sha256")

    # Roles (añadir / quitar)
    new_roles_ids = set(data.get("roles", []))
    current_roles_ids = _get_current_role_ids(id_usuario)
    roles_to_add = new_roles_ids - current_roles_ids
    roles_to_remove = current_roles_ids - new_roles_ids

    if roles_to_add:
        existentes = {r.id_rol for r in Rol.query.filter(Rol.id_rol.in_(roles_to_add)).all()}
        faltantes = [rid for rid in roles_to_add if rid not in existentes]
        if faltantes:
            return jsonify({"message": f"El/los rol(es) {faltantes} no existen para añadir."}), 400

    try:
        if roles_to_remove:
            (UsuarioRol.query
                .filter(UsuarioRol.id_usuario == id_usuario, UsuarioRol.id_rol.in_(roles_to_remove))
                .delete(synchronize_session=False))

        for rid in roles_to_add:
            db.session.add(UsuarioRol(id_usuario=id_usuario, id_rol=rid))

        db.session.commit()
        return jsonify({"message": "Usuario actualizado exitosamente", "user": _user_to_dict(user)}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error actualizando usuario")
        return jsonify({"message": "Error interno del servidor al actualizar usuario", "error": str(e)}), 500

# DELETE (eliminación lógica)
@bp.delete("/<int:id_usuario>")
@roles_required(["Admin"])
def delete_user(id_usuario):
    user = Usuario.query.get(id_usuario)
    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # Impedir eliminarse a sí mismo
    current_user_id = str(get_jwt_identity())
    if str(getattr(user, "id_usuario", None)) == current_user_id:
        return jsonify({"message": "No puedes eliminar tu propio usuario mientras estás logueado."}), 400

    # Idempotente si ya está eliminado
    if user.estado == "ELIMINADO":
        return jsonify({"message": "Usuario ya estaba eliminado lógicamente"}), 200

    try:
        user.estado = "ELIMINADO"
        db.session.commit()
        return jsonify({"message": "Usuario eliminado lógicamente"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en eliminación lógica de usuario")
        return jsonify({"message": "Error interno del servidor al eliminar usuario", "error": str(e)}), 500
