# app/__init__.py
import os
from datetime import timedelta
from flask import Flask
from dotenv import load_dotenv

# usa SIEMPRE las instancias compartidas desde app.extensions
from app.extensions import db, jwt, cors, migrate
from app.utils.seed import seed_db


def create_app():
    # 1) Cargar variables de entorno
    load_dotenv()

    app = Flask(__name__)

    # 2) Base de datos
    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"options": "-c client_encoding=utf8"}
    }

    # 3) JWT (Flask-JWT-Extended espera timedelta)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    )
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 86400))
    )

    # 4) CORS
    # Permitir orígenes dinámicos desde .env + fallback seguro
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://187.77.37.231",
        "http://187.77.37.231:3000",
        "https://sistema-pos-25.vercel.app"
    ]
    
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS")
    if env_origins:
        allowed_origins.extend([o.strip() for o in env_origins.split(",")])

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": list(set(allowed_origins))}},
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
        # Inicialización automática de SuperAdmin
        seed_db()

    return app
