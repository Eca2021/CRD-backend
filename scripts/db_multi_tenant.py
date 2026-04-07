import os
import sys
from sqlalchemy import text

# Añadir el directorio raíz al path para importar la app
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app import create_app
from app.extensions import db

def migrate():
    app = create_app()
    with app.app_context():
        print("Iniciando migración multi-tenant...")
        
        # 1. Crear tabla de empresas si no existe
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS empresa (
                id_empresa SERIAL PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                ruc VARCHAR(50) UNIQUE NOT NULL,
                direccion TEXT,
                telefono VARCHAR(50),
                email VARCHAR(100),
                logo_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # 2. Insertar las dos empresas iniciales
        db.session.execute(text("""
            INSERT INTO empresa (id_empresa, nombre, ruc)
            VALUES (1, 'Edison Cabrera', '5614261-7')
            ON CONFLICT (ruc) DO UPDATE SET nombre = EXCLUDED.nombre;
            
            INSERT INTO empresa (id_empresa, nombre, ruc)
            VALUES (2, 'Matias Paredes', '5976291-8')
            ON CONFLICT (ruc) DO UPDATE SET nombre = EXCLUDED.nombre;
            
            SELECT setval('empresa_id_empresa_seq', 2);
        """))
        
        # 3. Añadir id_empresa a las tablas principales
        tables = [
            'usuarios', 'clientes', 'creditos', 'reglas_credito', 
            'tasas_interes', 'pagos', 'formas_pago', 'asientos_contables', 
            'movimientos_contables', 'movimientos_admin'
        ]
        
        for table in tables:
            print(f"Migrando tabla: {table}")
            
            # Verificar si la tabla existe antes de intentar alterarla
            check_table = db.session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            """)).scalar()
            
            if not check_table:
                print(f"  ⚠️ Tabla '{table}' no existe, saltando...")
                continue

            # Añadir columna id_empresa si no existe
            db.session.execute(text(f"""
                ALTER TABLE {table} 
                ADD COLUMN IF NOT EXISTS id_empresa INTEGER;
            """))
            
            # Asignar a la empresa 1 por defecto para datos existentes
            db.session.execute(text(f"""
                UPDATE {table} SET id_empresa = 1 WHERE id_empresa IS NULL;
            """))
            
            # Hacerlo NOT NULL y añadir FK
            db.session.execute(text(f"""
                ALTER TABLE {table} 
                ALTER COLUMN id_empresa SET NOT NULL;
                
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_{table}_empresa'
                    ) THEN
                        ALTER TABLE {table} 
                        ADD CONSTRAINT fk_{table}_empresa 
                        FOREIGN KEY (id_empresa) REFERENCES empresa(id_empresa);
                    END IF;
                END $$;
            """))
        
        db.session.commit()
        print("Migración completada exitosamente.")

if __name__ == "__main__":
    migrate()
