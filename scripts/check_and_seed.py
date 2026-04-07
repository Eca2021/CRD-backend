# scripts/check_and_seed.py
import sys
import os

# Añadir el directorio raíz al path para poder importar la app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.catalog import Usuario, Rol, UsuarioRol
from app.utils.seed import seed_db

def run():
    app = create_app()
    with app.app_context():
        print("[CHECK] Iniciando verificacion y seed...")
        seed_db()
        
        users = Usuario.query.all()
        print(f"\n[OK] Usuarios encontrados: {len(users)}")
        for u in users:
            roles = [ur.rol.nombre for ur in u.roles]
            print(f" - ID: {u.id_usuario} | User: {u.nombre_usuario} | Empresa: {u.id_empresa} | Roles: {roles}")
            
        print("\n[FIN] Verificacion completada.")

if __name__ == "__main__":
    run()
