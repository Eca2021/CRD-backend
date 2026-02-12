import os

class BaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret")
    CORS_ORIGINS = [
        "http://localhost:3000",
        "https://sistema-pos-25.vercel.app"
    ]
    JSON_SORT_KEYS = False

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False

def settings():
    env = os.getenv("FLASK_ENV", "development").lower()
    return ProdConfig if env == "production" else DevConfig
