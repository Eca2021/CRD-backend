# scripts/rename_table_fix.py
import sys
import os

# Añadir el directorio raíz al path para poder importar la app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def run_fix():
    app = create_app()
    with app.app_context():
        try:
            print("[FIX] Iniciando reparacion de base de datos...")
            
            # 1. Renombrar la tabla de t_empresas a empresa
            try:
                db.session.execute(text("ALTER TABLE t_empresas RENAME TO empresa;"))
                print("[OK] Tabla 't_empresas' renombrada a 'empresa' correctamente.")
            except Exception as e:
                if "no existe" in str(e).lower() or "does not exist" in str(e).lower():
                    print("[INFO] La tabla 't_empresas' ya no existe (probablemente ya fue renombrada).")
                else:
                    raise e
            
            # 2. Renombrar la secuencia
            try:
                db.session.execute(text("ALTER SEQUENCE t_empresas_id_empresa_seq RENAME TO empresa_id_empresa_seq;"))
                print("[OK] Secuencia de ID renombrada correctamente.")
            except Exception as e:
                print(f"[INFO] Aviso sobre secuencia: {e}")

            # 3. Renombrar indices
            try:
                db.session.execute(text("ALTER INDEX t_empresas_ruc_key RENAME TO empresa_ruc_key;"))
                print("[OK] Indice de RUC renombrado.")
            except Exception: pass

            db.session.commit()
            print("\n[FIN] Base de datos sincronizada con el nuevo codigo!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error critico durante la reparacion: {e}")

if __name__ == "__main__":
    run_fix()
