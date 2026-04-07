# scripts/test_login_diagnostic.py
import sys
import os
from werkzeug.security import check_password_hash, generate_password_hash

# Añadir el directorio raíz al path para poder importar la app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.catalog import Usuario

def run():
    app = create_app()
    with app.app_context():
        print("--- DIAGNOSTICO DE LOGIN ---")
        usernames = ['superusuario', 'admin_global']
        password_to_test = 'admin123'
        
        for name in usernames:
            user = Usuario.query.filter_by(nombre_usuario=name).first()
            if not user:
                print(f"[ERROR] Usuario '{name}' NO encontrado en la base de datos.")
                continue
                
            match = check_password_hash(user.password_hash, password_to_test)
            print(f"[INFO] Usuario: {name}")
            print(f"       - ID: {u.id_usuario if 'u' in locals() else user.id_usuario}")
            print(f"       - Hash en DB: {user.password_hash[:20]}...")
            print(f"       - Prueba con 'admin123': {'EXITO' if match else 'FALLO'}")
            
            # Si fallo, vamos a intentar generar uno nuevo y comparar
            if not match:
                new_hash = generate_password_hash(password_to_test, method="pbkdf2:sha256")
                match_new = check_password_hash(new_hash, password_to_test)
                print(f"       - Nuevo hash generado para prueba: {match_new}")

if __name__ == "__main__":
    run()
