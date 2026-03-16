from app import create_app
from app.extensions import db
from app.models.catalog import MovimientoAdmin

app = create_app()
with app.app_context():
    print("Verificando tablas...")
    db.create_all()
    print("Tablas verificadas/creadas exitosamente.")
