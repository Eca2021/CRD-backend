from app.extensions import db, jwt, cors

def register_blueprints(app):
    """
    Importa y registra todos los blueprints de forma perezosa para evitar
    importaciones circulares (partially initialized module 'app.api').
    """

    # ---- IMPORTS LOCALES (lazy) ----
    from .auth import bp as auth_bp
    from .users import bp as users_bp
    from app.api.roles import bp as roles_bp
    from app.api.permisos import bp as permisos_bp
    from app.api.company_settings import bp as company_settings_bp
    from app.api.clientes import bp as clientes_bp
    from app.api.tasas import bp as tasas_bp
    from app.api.creditos import bp as creditos_bp
    from app.api.pagos import bp as pagos_bp
    from app.api.contabilidad import bp as contabilidad_bp


    # ---- REGISTROS ----
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/usuarios")
    app.register_blueprint(roles_bp, url_prefix="/api/roles")
    app.register_blueprint(permisos_bp, url_prefix="/api/permisos")
    app.register_blueprint(company_settings_bp, url_prefix="/api/company-settings")
    app.register_blueprint(clientes_bp, url_prefix="/api/clientes")
    app.register_blueprint(tasas_bp, url_prefix="/api/tasas")
    app.register_blueprint(creditos_bp, url_prefix="/api/creditos")
    app.register_blueprint(pagos_bp, url_prefix="/api/pagos")
    app.register_blueprint(contabilidad_bp, url_prefix="/api/contabilidad")
