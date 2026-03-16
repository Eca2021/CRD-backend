from app.extensions import db
from app import create_app

def apply_migration():
    app = create_app()
    with app.app_context():
        try:
            # SQL to add id_usuario column to pagos table
            # Adjust according to the actual database type (PostgreSQL in .env)
            db.session.execute(db.text("ALTER TABLE pagos ADD COLUMN id_usuario INTEGER;"))
            db.session.execute(db.text("ALTER TABLE pagos ADD CONSTRAINT fk_pagos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario);"))
            db.session.commit()
            print("Migration successful: id_usuario added to pagos table.")
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    apply_migration()
