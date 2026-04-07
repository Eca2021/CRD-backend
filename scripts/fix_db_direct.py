# scripts/fix_db_direct.py
import os
from dotenv import load_dotenv
import psycopg

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def fix():
    # Limpiar prefijo de SQLAlchemy si existe
    clean_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    
    print("Conectando a la base de datos...")
    try:
        # Conexión directa con psycopg
        with psycopg.connect(clean_url) as conn:
            with conn.cursor() as cur:
                print("Verificando columna 'is_global'...")
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='usuarios' AND column_name='is_global';
                """)
                if not cur.fetchone():
                    print("Anadiendo columna 'is_global'...")
                    cur.execute("ALTER TABLE usuarios ADD COLUMN is_global BOOLEAN DEFAULT FALSE;")
                    cur.execute("UPDATE usuarios SET is_global = FALSE;")
                    print("Columna anadida exitosamente.")
                else:
                    print("La columna 'is_global' ya existe.")
                
                # Configuracion de maestros
                print("Configurando administradores...")
                # admin_global: Global (Empresa NULL) y is_global = True
                cur.execute("UPDATE usuarios SET is_global = TRUE, id_empresa = NULL WHERE nombre_usuario = 'admin_global';")
                # admin: Empresa 1 y is_global = True (Poder absoluto desde Empresa 1)
                cur.execute("UPDATE usuarios SET is_global = TRUE, id_empresa = 1 WHERE nombre_usuario = 'admin';")
                
                conn.commit()
                print("Proceso completado exitosamente.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    fix()
