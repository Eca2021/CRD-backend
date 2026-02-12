# app/api/roles.py
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, exists
from app.extensions import db
from app.models.catalog import Rol, Permiso, RolPermiso, UsuarioRol
# usa el decorador ya definido en users.py para no duplicar
from app.api.users import roles_required

bp = Blueprint("roles", __name__)

# --------- helpers ---------
def _role_to_dict(r: Rol):
    # Si tu modelo ya tiene to_dict con permisos, úsalo
    if hasattr(r, "to_dict"):
        try:
            return r.to_dict()
        except Exception:
            pass
    # Fallback: construirlo aquí
    # intentamos acceder a relación si existe (e.g., r.permisos_asociados),
    # si no, consultamos por RolPermiso.
    permisos_ids = []
    try:
        if hasattr(r, "permisos_asociados") and r.permisos_asociados is not None:
            permisos_ids = [rp.id_permiso for rp in r.permisos_asociados]
        else:
            permisos_ids = [row[0] for row in db.session.query(RolPermiso.id_permiso).filter_by(id_rol=r.id_rol).all()]
    except Exception:
        permisos_ids = [row[0] for row in db.session.query(RolPermiso.id_permiso).filter_by(id_rol=r.id_rol).all()]

    return {
        "id_rol": r.id_rol,
        "nombre": r.nombre,
        "descripcion": getattr(r, "descripcion", None),
        "permisos": permisos_ids,
    }

# --------- endpoints ---------

# POST /api/roles
@bp.post("/")
@roles_required(["Admin"])
def create_role():
    data = request.get_json() or {}
    nombre  = (data.get("nombre") or data.get("nombre_rol") or "").strip()
    descripcion = data.get("descripcion")
    permisos_ids = list({int(x) for x in (data.get("permisos") or [])})  # dedup

    if not nombre:
        return jsonify({"message": "El nombre del rol es requerido"}), 400

    # unicidad case-insensitive
    existing_role = (
        Rol.query.filter(func.lower(Rol.nombre) == nombre.lower()).first()
    )
    if existing_role:
        return jsonify({"message": "El nombre de rol ya existe"}), 409

    # validar permisos
    if permisos_ids:
        existentes = {p.id_permiso for p in Permiso.query.filter(Permiso.id_permiso.in_(permisos_ids)).all()}
        faltantes = [pid for pid in permisos_ids if pid not in existentes]
        if faltantes:
            return jsonify({"message": f"Permisos inexistentes: {faltantes}"}), 400

    try:
        new_role = Rol(nombre=nombre, descripcion=descripcion)
        db.session.add(new_role)
        db.session.flush()  # obtener id_rol

        for pid in permisos_ids:
            db.session.add(RolPermiso(id_rol=new_role.id_rol, id_permiso=pid))

        db.session.commit()
        return jsonify({"message": "Rol creado exitosamente", "role": _role_to_dict(new_role)}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creando rol")
        return jsonify({"message": "Error interno del servidor al crear rol", "error": str(e)}), 500


# GET /api/roles
@bp.get("/")
@roles_required(["Admin", "Vendedor", "Gerente"])
def get_roles():
    roles = Rol.query.order_by(Rol.id_rol.asc()).all()
    return jsonify([_role_to_dict(r) for r in roles]), 200


# PUT /api/roles/<id_rol>
@bp.put("/<int:id_rol>")
@roles_required(["Admin"])
def update_role(id_rol):
    role = Rol.query.get(id_rol)
    if not role:
        return jsonify({"message": "Rol no encontrado"}), 404

    data = request.get_json() or {}
    new_nombre = (data.get("nombre") or data.get("nombre_rol") or "").strip() or None
    new_desc   = data.get("descripcion", None)
    new_permisos_ids = set(int(x) for x in (data.get("permisos") or []))

    # nombre único si cambió
    if new_nombre and new_nombre != role.nombre:
        dup = (
            Rol.query.filter(
                func.lower(Rol.nombre) == new_nombre.lower(),
                Rol.id_rol != id_rol
            ).first()
        )
        if dup:
            return jsonify({"message": "El nombre de rol ya existe"}), 409
        role.nombre = new_nombre

    if new_desc is not None:
        role.descripcion = new_desc

    # permisos: calcular diff
    current_ids = {row[0] for row in db.session.query(RolPermiso.id_permiso).filter_by(id_rol=id_rol).all()}
    to_add    = new_permisos_ids - current_ids
    to_remove = current_ids - new_permisos_ids

    # validar a añadir
    if to_add:
        existentes = {p.id_permiso for p in Permiso.query.filter(Permiso.id_permiso.in_(to_add)).all()}
        faltantes = [pid for pid in to_add if pid not in existentes]
        if faltantes:
            return jsonify({"message": f"El/los permiso(s) {faltantes} no existen para añadir."}), 400

    try:
        # remove en bloque
        if to_remove:
            (RolPermiso.query
                .filter(RolPermiso.id_rol == id_rol, RolPermiso.id_permiso.in_(to_remove))
                .delete(synchronize_session=False))

        # add
        for pid in to_add:
            db.session.add(RolPermiso(id_rol=id_rol, id_permiso=pid))

        db.session.commit()
        return jsonify({"message": "Rol actualizado exitosamente", "role": _role_to_dict(role)}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error actualizando rol")
        return jsonify({"message": "Error interno del servidor al actualizar rol", "error": str(e)}), 500


# DELETE /api/roles/<id_rol>
@bp.delete("/<int:id_rol>")
@roles_required(["Admin"])
def delete_role(id_rol):
    role = Rol.query.get(id_rol)
    if not role:
        return jsonify({"message": "Rol no encontrado"}), 404

    if role.nombre == "Admin":
        return jsonify({"message": "No se puede eliminar el rol 'Admin'"}), 400

    # proteger si hay usuarios con este rol
    asignado = db.session.query(exists().where(UsuarioRol.id_rol == id_rol)).scalar()
    if asignado:
        return jsonify({"message": "No se puede eliminar: el rol está asignado a usuarios"}), 400

    try:
        db.session.delete(role)
        db.session.commit()
        return jsonify({"message": "Rol eliminado exitosamente"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error eliminando rol")
        return jsonify({"message": "Error interno del servidor al eliminar rol", "error": str(e)}), 500
