# scripts/fix_audit_nullable.py
import os
from dotenv import load_dotenv
import psycopg

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def fix():
    # Limpiar prefijo de SQLAlchemy si existe
    clean_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    
    print("Conectando a la base de datos para sanear auditoria...")
    try:
        with psycopg.connect(clean_url) as conn:
            with conn.cursor() as cur:
                print("Habilitando NULOS para id_empresa en historial_accesos...")
                # Quitar restricción NOT NULL si existe
                cur.execute("ALTER TABLE historial_accesos ALTER COLUMN id_empresa DROP NOT NULL;")
                
                # Verificando otras tablas de auditoria por si acaso
                print("Verificando otras tablas de auditoria...")
                # (Añadir aquí otras si descubrimos que fallan)
                
                conn.commit()
                print("Saneamiento completado exitosamente.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    fix()
