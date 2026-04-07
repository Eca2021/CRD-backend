from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func, or_
from app.extensions import db
from app.models.catalog import Cliente, Usuario

bp = Blueprint("clientes", __name__)

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
@permission_required("cliente.gestionar")
def get_clientes():
    q = (request.args.get("q") or "").strip()
    
    id_empresa = get_jwt().get("id_empresa")
    query = Cliente.query.filter_by(id_empresa=id_empresa)
    
    if q:
        search = f"%{q}%"
        query = query.filter(or_(
            Cliente.nombre.ilike(search),
            Cliente.apellido.ilike(search),
            Cliente.documento.ilike(search)
        ))
    
    # Order by creation (ID) so new clients go to the bottom
    clientes = query.order_by(Cliente.id_cliente.asc()).all()
    return jsonify([c.to_dict() for c in clientes]), 200

@bp.post("/")
@permission_required("cliente.gestionar")
def create_cliente():
    data = request.get_json() or {}
    nombre = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    documento = (data.get("documento") or "").strip()
    
    id_empresa = get_jwt().get("id_empresa")
    if not nombre or not apellido or not documento:
        return jsonify({"message": "Nombre, Apellido y Documento son obligatorios"}), 400
        
    if Cliente.query.filter(Cliente.documento == documento, Cliente.id_empresa == id_empresa).first():
        return jsonify({"message": "Ya existe un cliente con ese documento para esta empresa"}), 409
        
    nuevo = Cliente(
        id_empresa=id_empresa,
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        direccion=data.get("direccion"),
        telefono=data.get("telefono")
    )
    
    try:
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"message": "Cliente creado", "cliente": nuevo.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creando cliente", "error": str(e)}), 500

@bp.put("/<int:id_cliente>")
@permission_required("cliente.gestionar")
def update_cliente(id_cliente):
    id_empresa = get_jwt().get("id_empresa")
    cliente = Cliente.query.filter_by(id_cliente=id_cliente, id_empresa=id_empresa).first()
    if not cliente:
        return jsonify({"message": "Cliente no encontrado o acceso denegado"}), 404
        
    data = request.get_json() or {}
    
    # Update fields
    cliente.nombre = data.get("nombre", cliente.nombre)
    cliente.apellido = data.get("apellido", cliente.apellido)
    cliente.direccion = data.get("direccion", cliente.direccion)
    cliente.telefono = data.get("telefono", cliente.telefono)
    
    # Check Document uniqueness if changed
    new_doc = (data.get("documento") or "").strip()
    if new_doc and new_doc != cliente.documento:
        if Cliente.query.filter(Cliente.documento == new_doc, Cliente.id_empresa == id_empresa).first():
            return jsonify({"message": "Ya existe otro cliente con ese documento en esta empresa"}), 409
        cliente.documento = new_doc
        
    try:
        db.session.commit()
        return jsonify({"message": "Cliente actualizado", "cliente": cliente.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error actualizando cliente", "error": str(e)}), 500

@bp.delete("/<int:id_cliente>")
@permission_required("cliente.gestionar")
def delete_cliente(id_cliente):
    id_empresa = get_jwt().get("id_empresa")
    cliente = Cliente.query.filter_by(id_cliente=id_cliente, id_empresa=id_empresa).first()
    if not cliente:
        return jsonify({"message": "Cliente no encontrado o acceso denegado"}), 404
        
    try:
        # Physical delete as per new schema (no 'estado' column)
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({"message": "Cliente eliminado permanentemente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error eliminando cliente", "error": str(e)}), 500
