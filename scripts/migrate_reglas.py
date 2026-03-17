import os
import sys

# Agregar ruta para importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.extensions import db
from app.models.catalog import ReglaCredito, Credito, TasaInteres
from flask import Flask
from app.config import settings
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(settings())
db.init_app(app)

def migrate_db():
    with app.app_context():
        # Get raw connection to avoid some session wrappers that might fail with execute(text) without commit in newer SQLAlchemy versions if misused
        conn = db.engine.connect()
        try:
            print("1. Agregando columna porcentaje a reglas_credito...")
            conn.execute(text("ALTER TABLE reglas_credito ADD COLUMN IF NOT EXISTS porcentaje numeric;"))
            
            print("2. Poblando reglas_credito con las iniciales...")
            tasas = TasaInteres.query.all()
            for tasa in tasas:
                if tasa.id_tasa == 1:
                    cod, nom, dias, pct = "SEM", "Semanal", 7, tasa.porcentaje
                elif tasa.id_tasa == 2:
                    cod, nom, dias, pct = "QUIN", "Quincenal", 15, tasa.porcentaje
                elif tasa.id_tasa == 3:
                     cod, nom, dias, pct = "MENS", "Mensual", 30, tasa.porcentaje
                else: continue
                
                # Check if exists
                existing = ReglaCredito.query.filter_by(codigo=cod).first()
                if not existing:
                     conn.execute(text(f"INSERT INTO reglas_credito (codigo, nombre, id_tasa, dias_intervalo, activo, porcentaje) VALUES ('{cod}', '{nom}', {tasa.id_tasa}, {dias}, true, {pct}) ON CONFLICT (codigo) DO UPDATE SET porcentaje = {pct};"))
                else:
                     conn.execute(text(f"UPDATE reglas_credito SET porcentaje = {pct} WHERE codigo = '{cod}';"))

            print("3. Actualizando creditos con id_regla basado en id_tasa...")
            creditos = Credito.query.all()
            for c in creditos:
                 if c.id_regla is not None: continue 
                 tasa = TasaInteres.query.get(c.id_tasa)
                 if tasa:
                     regla = ReglaCredito.query.filter_by(id_tasa=tasa.id_tasa).first()
                     if regla:
                          conn.execute(text(f"UPDATE creditos SET id_regla = {regla.id_regla} WHERE id_credito = {c.id_credito};"))

            print("4. Haciendo id_regla NOT NULL en creditos...")
            conn.execute(text("ALTER TABLE creditos ALTER COLUMN id_regla SET NOT NULL;"))
            
            print("5. Eliminando id_tasa de creditos...")
            conn.execute(text("ALTER TABLE creditos DROP CONSTRAINT IF EXISTS creditos_id_tasa_fkey;"))
            conn.execute(text("ALTER TABLE creditos DROP COLUMN IF EXISTS id_tasa;"))
            
            print("6. Eliminando id_tasa de reglas_credito y NOT NULL porcentaje...")
            conn.execute(text("ALTER TABLE reglas_credito DROP CONSTRAINT IF EXISTS reglas_credito_id_tasa_fkey;"))
            conn.execute(text("ALTER TABLE reglas_credito DROP COLUMN IF EXISTS id_tasa;"))
            conn.execute(text("ALTER TABLE reglas_credito ALTER COLUMN porcentaje SET NOT NULL;"))
            
            conn.commit()
            print("Migración completada exitosamente.")
        except Exception as e:
            conn.rollback()
            print(f"Error durante migración: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    migrate_db()
