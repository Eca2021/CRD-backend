import os
import sys
import traceback

# Aseguramos que el script encuentre la carpeta 'app'
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from flask import request

app = create_app()

def test_login_diagnostic(username, password):
    """
    Simula un intento de login capturando el error real del servidor.
    """
    print(f"\n🔍 --- INICIANDO DIAGNÓSTICO DE LOGIN ---")
    print(f"👤 Intentando con usuario: {username}")
    
    with app.test_request_context(json={'username': username, 'password': password}):
        try:
            # Obtenemos la función de login del blueprint registrado
            login_func = app.view_functions['auth.login']
            
            print("⚙️ Ejecutando función login()...")
            response = login_func()
            
            print(f"\n📊 [RESULTADO HTTP]: {response.status_code}")
            print(f"📄 [RESPUESTA JSON]: {response.get_data(as_text=True)}")
            
            if response.status_code == 500:
                print("\n⚠️ El servidor retornó un 500 pero no lanzó una excepción de Python visible aquí.")
                print("Esto puede ser un error en la configuración de la extensión (ej: JWT_SECRET_KEY mal configurada).")

        except Exception:
            print("\n❌ [ERROR DETECTADO - TRACEBACK]:")
            print("-" * 50)
            print(traceback.format_exc())
            print("-" * 50)

if __name__ == "__main__":
    print("====================================================")
    print("🛠️  DEPURADOR DE AUTENTICACIÓN - CREDITO SQUID")
    print("====================================================")
    
    user = input("Introduce usuario (ej: admin_global): ").strip() or "admin_global"
    passwd = input(f"Introduce contraseña para '{user}': ").strip()
    
    if not passwd:
        print("❌ Debes introducir una contraseña para la prueba.")
        sys.exit(1)
        
    test_login_diagnostic(user, passwd)
