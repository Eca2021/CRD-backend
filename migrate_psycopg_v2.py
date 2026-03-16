# -*- coding: utf-8 -*-
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

# Clean up the DATABASE_URL for psycopg
# SQLAlchemy often uses postgresql+psycopg:// but psycopg expects postgresql://
clean_url = DATABASE_URL
if clean_url:
    if "+psycopg" in clean_url:
        clean_url = clean_url.replace("+psycopg", "")
    if "postgresql://" not in clean_url and "postgres://" not in clean_url:
        # If it's a raw string without scheme, assume postgresql
        if not clean_url.startswith("postgres"):
            clean_url = "postgresql://" + clean_url
else:
    print("Error: DATABASE_URL is None")
    exit(1)

print(f"Connecting to database...")

try:
    with psycopg.connect(clean_url) as conn:
        conn.execute("SET client_encoding TO 'UTF8';")
        with conn.cursor() as cur:
            # Check if column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='pagos' AND column_name='id_usuario';
            """)
            if cur.fetchone():
                print("Column id_usuario already exists.")
            else:
                print("Adding id_usuario column...")
                cur.execute("ALTER TABLE pagos ADD COLUMN id_usuario INTEGER;")
                
                print("Adding foreign key constraint...")
                # We use a try-except here in case the constraint already exists
                try:
                    cur.execute("ALTER TABLE pagos ADD CONSTRAINT fk_pagos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario);")
                except Exception as e:
                    print(f"Note: Could not add constraint (might already exist): {e}")
                
                conn.commit()
                print("Migration successful: id_usuario added to pagos table.")
except Exception as e:
    print(f"Migration failed: {e}")
