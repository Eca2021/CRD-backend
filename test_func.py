from app import create_app
from app.api.dashboard import get_dashboard_summary
import traceback
from flask import Flask

app = create_app()
with app.app_context():
    print("Iniciando prueba de get_dashboard_summary...")
    try:
        # No necesito request real porque la función no usa request.args/json para el summary básico
        # Pero usa @jwt_required(), así que podría fallar si no hay un contexto de request con token
        # Sin embargo, el error 500 sugiere que el error ocurre ANTES o DURANTE la ejecución de la lógica,
        # o tal vez en la validación del token.
        # Pero @jwt_required() normalmente lanza 401 si falta el token. 500 es algo en el código.
        
        # Simulamos que no hay JWT para ver si lanza 500 (lo cual sería raro)
        # O mejor, quitamos el decorador temporalmente en dashboard.py si sospechamos de él.
        
        # Probemos llamar la lógica interna directamente
        # Pero get_dashboard_summary es la función decorada.
        
        # Vamos a intentar importar TODO el módulo de nuevo de forma aislada
        print("Llamando a la función...")
        res = get_dashboard_summary()
        print("Respuesta:", res)
    except Exception:
        print("ERROR:")
        traceback.print_exc()
