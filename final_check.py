from app import create_app
from app.extensions import db
from app.api.dashboard import get_dashboard_summary
import json

app = create_app()
with app.app_context():
    print("Calculando métricas del dashboard directamente...")
    try:
        # La función get_dashboard_summary() intenta retornar un jsonify()
        # En un test sin request context, jsonify() podría fallar.
        # Vamos a extraer la lógica o simplemente envolverla.
        
        # Pero wait, la función en dashboard.py ya está terminada.
        # Vamos a ver qué devuelve.
        res = get_dashboard_summary()
        # res es un objeto Response de Flask
        print("Métricas obtenidas correctamente.")
        print("Data:", res.get_json())
    except Exception as e:
        print("Error calculando métricas:", e)
        import traceback
        traceback.print_exc()
