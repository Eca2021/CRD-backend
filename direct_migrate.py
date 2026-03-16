# -*- coding: utf-8 -*-
import os
from sqlalchemy import create_all, text, create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

# Fix for potential postgresql:// vs postgresql+psycopg://
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, connect_args={"options": "-c client_encoding=utf8"})

sql_commands = [
    "ALTER TABLE pagos ADD COLUMN id_usuario INTEGER;",
    "ALTER TABLE pagos ADD CONSTRAINT fk_pagos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario);"
]

with engine.connect() as connection:
    for sql in sql_commands:
        try:
            print(f"Executing: {sql}")
            connection.execute(text(sql))
            connection.commit()
            print("Success")
        except Exception as e:
            print(f"Error: {e}")
