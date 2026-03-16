# -*- coding: utf-8 -*-
import psycopg
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Error: DATABASE_URL no encontrada en .env")
    exit(1)

# Clean up the DATABASE_URL for psycopg
clean_url = DATABASE_URL
if clean_url:
    if "+psycopg" in clean_url:
        clean_url = clean_url.replace("+psycopg", "")
    if "postgresql://" not in clean_url and "postgres://" not in clean_url:
        if not clean_url.startswith("postgres"):
            clean_url = "postgresql://" + clean_url
else:
    print("Error: DATABASE_URL is None")
    exit(1)

def run_migration():
    conn = None
    try:
        print(f"Conectando a la base de datos...")
        conn = psycopg.connect(clean_url)
        conn.execute("SET client_encoding TO 'UTF8';")
        cur = conn.cursor()

        # SQL para crear la tabla de auditoría
        audit_sql = """
        CREATE TABLE IF NOT EXISTS public.historial_pagos_audit (
            id_audit SERIAL PRIMARY KEY,
            id_pago INTEGER,
            id_usuario INTEGER REFERENCES public.usuarios(id_usuario),
            accion VARCHAR(20),
            fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            monto_registrado NUMERIC(15,2),
            id_detalle_credito INTEGER,
            estado_pago_momento VARCHAR(10),
            direccion_ip VARCHAR(45),
            observacion TEXT
        );
        """
        
        print("Creando tabla historial_pagos_audit...")
        cur.execute(audit_sql)
        
        conn.commit()
        print("Migración completada con éxito.")
        
    except Exception as e:
        print(f"Error durante la migración: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
