import os
from flask import Flask
from app import create_app
from app.extensions import db
from sqlalchemy import text

def fix_database():
    app = create_app()
    with app.app_context():
        print("Iniciando reparacion de base de datos...")

        # Conectar a la base de datos
        with db.engine.connect() as connection:
            # 1. Agregar columnas a detalles_credito si no existen
            try:
                connection.execute(text("ALTER TABLE detalles_credito ADD COLUMN capital_cuota NUMERIC(15, 2) DEFAULT 0"))
                print("Agregada columna capital_cuota")
            except Exception as e:
                print("Columna capital_cuota ya existe o error:", e)

            try:
                connection.execute(text("ALTER TABLE detalles_credito ADD COLUMN interes_cuota NUMERIC(15, 2) DEFAULT 0"))
                print("Agregada columna interes_cuota")
            except Exception as e:
                print("Columna interes_cuota ya existe o error:", e)

            try:
                connection.execute(text("ALTER TABLE detalles_credito ADD COLUMN cuota_total NUMERIC(15, 2) DEFAULT 0"))
                print("Agregada columna cuota_total")
            except Exception as e:
                print("Columna cuota_total ya existe o error:", e)

            # 2. Crear tabla asientos_contables si no existe
            try:
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS asientos_contables (
                        id SERIAL PRIMARY KEY,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        glosa TEXT,
                        id_usuario INTEGER,
                        FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
                    )
                """))
                print("Tabla asientos_contables verificada")
            except Exception as e:
                print("Error creando tabla asientos_contables:", e)

            # 3. Crear tabla movimientos_contables si no existe
            try:
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS movimientos_contables (
                        id SERIAL PRIMARY KEY,
                        id_asiento INTEGER NOT NULL,
                        cuenta_nombre VARCHAR(100) NOT NULL,
                        debe NUMERIC(15, 2) DEFAULT 0,
                        haber NUMERIC(15, 2) DEFAULT 0,
                        FOREIGN KEY (id_asiento) REFERENCES asientos_contables(id) ON DELETE CASCADE
                    )
                """))
                print("Tabla movimientos_contables verificada")
            except Exception as e:
                print("Error creando tabla movimientos_contables:", e)

            connection.commit()
            print("Reparacion completada exitosamente.")

if __name__ == "__main__":
    fix_database()
