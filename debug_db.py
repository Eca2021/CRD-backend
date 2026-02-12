import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
print(f"DATABASE_URL found: {db_url}")

# Try to connect if it's postgres
if db_url and "postgresql" in db_url:
    try:
        import psycopg
        print("Attempting connection with psycopg...")
        conn = psycopg.connect(db_url)
        print("Connection successful!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
