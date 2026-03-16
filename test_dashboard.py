import requests
import json
import traceback

BASE_URL = "http://localhost:5000/api"

def test_dashboard_summary():
    # 1. Login to get token
    print("Iniciando sesión...")
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"Error en login: {response.status_code} - {response.text}")
            return
            
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get Dashboard Summary
        print("Obteniendo resumen del dashboard...")
        response = requests.get(f"{BASE_URL}/dashboard/summary", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("Datos recibidos exitosamente:")
            print(json.dumps(data, indent=2))
            
            # Verificar campos requeridos
            required_fields = [
                "capital_disponible", 
                "caja_total", 
                "por_cobrar_capital", 
                "ganancia_pendiente", 
                "ganancia_realizada"
            ]
            
            for field in required_fields:
                if field in data:
                    print(f"[OK] Campo {field} presente: {data[field]}")
                else:
                    print(f"[FAIL] Campo {field} ausente")
        else:
            print(f"ERROR en dashboard summary: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error de conexión: {e}")
        # traceback.print_exc()

if __name__ == "__main__":
    test_dashboard_summary()
