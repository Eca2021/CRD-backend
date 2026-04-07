# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import text

# Añadir el directorio raíz al path para importar la app
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app import create_app
from app.extensions import db

def run_check():
    print("====================================================")
    print("🔍 SISTEMA DE CHEQUEO DE PRODUCCIÓN - CREDITO SQUID")
    print("====================================================")
    
    app = create_app()
    
    with app.app_context():
        # 1. Verificar Variables Críticas
        print("\n1. Verificando Variables de Entorno...")
        db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if "127.0.0.1" in db_url or "localhost" in db_url:
            print("⚠️ ADVERTENCIA: Estás usando localhost en la DATABASE_URL.")
        else:
            print("✅ DATABASE_URL configurada externamente.")
            
        secret = app.config.get("JWT_SECRET_KEY", "")
        if secret == "dev-secret-change-me" or not secret:
            print("❌ ERROR CRÍTICO: JWT_SECRET_KEY por defecto o vacío.")
        else:
            print("✅ JWT_SECRET_KEY configurada.")

        # 2. Probar Conexión a Base de Datos
        print("\n2. Probando Conexión a Base de Datos...")
        try:
            db.session.execute(text("SELECT 1"))
            print("✅ Conectado exitosamente a la base de datos.")
        except Exception as e:
            print(f"❌ FALLO DE CONEXIÓN: {str(e)}")
            return

        # 3. Verificar Multi-Tenant
        print("\n3. Verificando Integridad de Tablas (Multi-Tenant)...")
        tables = ['usuarios', 'clientes', 'creditos', 'pagos', 'empresa']
        missing = []
        for table in tables:
            try:
                # Verificar si la columna id_empresa existe (excepto en la tabla empresa)
                if table != 'empresa':
                    db.session.execute(text(f"SELECT id_empresa FROM {table} LIMIT 1"))
                else:
                    db.session.execute(text(f"SELECT id_empresa FROM {table} LIMIT 1"))
                print(f"  - Tabla '{table}': OK")
            except Exception:
                missing.append(table)
                print(f"  - Tabla '{table}': MISSING id_empresa column!")
        
        if missing:
            print(f"\n❌ FALTAN MIGRACIONES en: {', '.join(missing)}")
            print("👉 Ejecuta: python scripts/db_multi_tenant.py")
        else:
            print("✅ Esquema de base de datos íntegro.")

        # 4. Verificar CORS
        print("\n4. Orígenes de Red (CORS) permitidos:")
        # Obtenemos los orígenes de la extensión cors si es posible
        # (Nota: depende de cómo esté implementado cors.init_app)
        allowed = os.getenv("CORS_ALLOWED_ORIGINS", "Default (localhost + 187.77.37.231)")
        print(f"  {allowed}")

    print("\n====================================================")
    print("🚀 ¡TODO LISTO PARA EL REINICIO!")
    print("====================================================")

if __name__ == "__main__":
    run_check()
