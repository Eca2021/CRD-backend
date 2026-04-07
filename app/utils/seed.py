# app/utils/seed.py
import os
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.catalog import Usuario, Rol, UsuarioRol

def seed_db():
    """
    Función para inicializar el Administrador Global maestro y roles básicos.
    Se ejecuta al iniciar el servidor si no existen los datos.
    """
    try:
        # 1. Asegurar existencia del rol SuperAdmin
        super_admin_role = Rol.query.filter_by(nombre='SuperAdmin').first()
        if not super_admin_role:
            super_admin_role = Rol(
                nombre='SuperAdmin', 
                descripcion='Administrador Global del Sistema - Acceso Total e Independiente'
            )
            db.session.add(super_admin_role)
            db.session.flush()
            print("✨ Rol SuperAdmin creado exitosamente.")

        # 2. Asegurar existencia del Admin Global Maestro
        # Usuario: admin_global
        # Contraseña: de variable de entorno o admin123 por defecto
        username = 'admin_global'
        admin_user = Usuario.query.filter_by(nombre_usuario=username).first()
        
        if not admin_user:
            initial_password = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
            hashed_pw = generate_password_hash(initial_password, method="pbkdf2:sha256")
            
            admin_user = Usuario(
                nombre_usuario=username,
                nombre='SuperAdmin Global',
                email='admin@creditosquid.com',
                password_hash=hashed_pw,
                estado='ACTIVO',
                id_empresa=None  # CLAVE:id_empresa NULL para ser Global
            )
            db.session.add(admin_user)
            db.session.flush()
            print(f"👤 Usuario Maestro '{username}' creado exitosamente.")

        # 3. Vincular Usuario con Rol
        link = UsuarioRol.query.filter_by(
            id_usuario=admin_user.id_usuario, 
            id_rol=super_admin_role.id_rol
        ).first()
        
        if not link:
            db.session.add(UsuarioRol(
                id_usuario=admin_user.id_usuario, 
                id_rol=super_admin_role.id_rol
            ))
            print(f"🔗 Rol SuperAdmin vinculado a '{username}'.")

        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error en inicialización de DB (Seed): {e}")
