# -*- coding: utf-8 -*-
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

clean_url = DATABASE_URL
if clean_url and "+psycopg" in clean_url:
    clean_url = clean_url.replace("+psycopg", "")

try:
    with psycopg.connect(clean_url) as conn:
        conn.execute("SET client_encoding TO 'UTF8';")
        with conn.cursor() as cur:
            # Check if column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='pagos' AND column_name='estado';
            """)
            if cur.fetchone():
                print("Column estado already exists in pagos table.")
            else:
                print("Adding estado column to pagos table...")
                cur.execute("ALTER TABLE pagos ADD COLUMN estado VARCHAR(20) DEFAULT 'ACTIVO';")
                conn.commit()
                print("Migration successful: estado added to pagos table.")
except Exception as e:
    print(f"Migration failed: {e}")
