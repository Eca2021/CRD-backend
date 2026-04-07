# scripts/add_is_global.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        print("--- INICIANDO MIGRACIÓN: ADD IS_GLOBAL ---")
        
        try:
            # 1. Añadir la columna is_global si no existe
            # Usamos una consulta para verificar la existencia (PostgreSQL compatible)
            check_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='usuarios' AND column_name='is_global';
            """)
            result = db.session.execute(check_column).fetchone()
            
            if not result:
                print("➕ Añadiendo columna 'is_global' a la tabla 'usuarios'...")
                db.session.execute(text("ALTER TABLE usuarios ADD COLUMN is_global BOOLEAN DEFAULT FALSE;"))
                db.session.execute(text("UPDATE usuarios SET is_global = FALSE;")) # Asegurar default
                print("✅ Columna añadida.")
            else:
                print("ℹ️ La columna 'is_global' ya existe.")

            # 2. Configurar usuarios maestros como Globales
            print("⚙️ Configurando privilegios globales para administradores...")
            
            # admin_global -> Global (Empresa NULL) y is_global = True
            db.session.execute(text("""
                UPDATE usuarios 
                SET is_global = TRUE, id_empresa = NULL 
                WHERE nombre_usuario = 'admin_global';
            """))
            
            # admin -> Empresa 1 y is_global = True (Poder absoluto desde Empresa 1)
            db.session.execute(text("""
                UPDATE usuarios 
                SET is_global = TRUE, id_empresa = 1 
                WHERE nombre_usuario = 'admin';
            """))
            
            db.session.commit()
            print("🚀 Migración completada exitosamente.")
            print("   - admin_global: GLOBAL (id_empresa=NULL, is_global=True)")
            print("   - admin: EMPRESA 1 (id_empresa=1, is_global=True)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR durante la migración: {str(e)}")

if __name__ == "__main__":
    migrate()
