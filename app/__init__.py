# app/__init__.py
import os
from datetime import timedelta
from flask import Flask
from dotenv import load_dotenv

# usa SIEMPRE las instancias compartidas desde app.extensions
from app.extensions import db, jwt, cors, migrate


def create_app():
    # 1) Cargar variables de entorno
    load_dotenv()

    app = Flask(__name__)

    # 2) Base de datos
    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 3) JWT (Flask-JWT-Extended espera timedelta)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    )
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 86400))
    )

    # 4) CORS
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": [
            "http://localhost:3000",
            "https://sistema-pos-25.vercel.app",
        ]}},
        supports_credentials=True,
    )

    # 5) Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # 6) Registrar blueprints
    from app.api import register_blueprints
    register_blueprints(app)

    # 7) (Opcional) callbacks JWT centralizados si existen
    try:
        from app.api.auth import register_jwt_callbacks
        register_jwt_callbacks(jwt)
    except Exception as e:
        print("JWT callbacks no cargados:", e)

    # Debug: ver rutas cargadas
    with app.app_context():
        print(app.url_map)

    return app
