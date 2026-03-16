# -*- coding: utf-8 -*-
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

# PostgreSQL usually starts with postgresql:// or postgres://
# psycopg works with both.

try:
    print(f"Connecting to database...")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("SET client_encoding TO 'UTF8';")
        with conn.cursor() as cur:
            print("Adding id_usuario column...")
            cur.execute("ALTER TABLE pagos ADD COLUMN id_usuario INTEGER;")
            
            print("Adding foreign key constraint...")
            cur.execute("ALTER TABLE pagos ADD CONSTRAINT fk_pagos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario);")
            
            conn.commit()
            print("Migration successful: id_usuario added to pagos table.")
except Exception as e:
    print(f"Migration failed: {e}")
