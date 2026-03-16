from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Sincronizando modelos con la base de datos...")
    
    # 1. Crear todas las tablas que falten (incluyendo reglas_credito)
    db.create_all()
    print("[OK] Tablas verificadas/creadas.")

    # 2. Añadir columna id_regla a la tabla creditos si no existe
    # (Usamos SQL crudo porque db.create_all no altera tablas existentes)
    try:
        with db.engine.connect() as conn:
            # Check if column exists (PostgreSQL syntax)
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='creditos' AND column_name='id_regla';
            """))
            if not result.fetchone():
                print("Añadiendo columna 'id_regla' a la tabla 'creditos'...")
                conn.execute(text("ALTER TABLE creditos ADD COLUMN id_regla INTEGER REFERENCES reglas_credito(id_regla);"))
                conn.commit()
                print("[OK] Columna añadida.")
            else:
                print("[SKIP] La columna 'id_regla' ya existe.")
    except Exception as e:
        print(f"[ERROR] No se pudo alterar la tabla creditos: {e}")

    print("Proceso de base de datos finalizado.")
