# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
print(f"DATABASE_URL found: {db_url}")

# Try to connect if it's postgres
if db_url:
    # Remove SQLAlchemy dialec if present for direct psycopg connection
    conn_str = db_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        import psycopg
        print(f"Attempting connection with: {conn_str}")
        conn = psycopg.connect(conn_str)
        cur = conn.cursor()
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'historial_accesos')")
        exists = cur.fetchone()[0]
        print(f"Table 'historial_accesos' exists: {exists}")
        
        # Also check current alembic version
        try:
            cur.execute("SELECT version_num FROM alembic_version")
            version = cur.fetchone()[0]
            print(f"Current Alembic version: {version}")
        except:
            print("Alembic version table not found or empty.")
            
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
