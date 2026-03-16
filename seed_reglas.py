from app import create_app
from app.extensions import db
from app.models.catalog import TasaInteres, ReglaCredito

app = create_app()
with app.app_context():
    print("Verificando tasas existentes...")
    tasas = TasaInteres.query.all()
    if not tasas:
        print("No hay tasas. Creando una tasa por defecto...")
        tasa_def = TasaInteres(nombre_tasa="Tasa Estándar", porcentaje=10, descripcion="Tasa del 10%")
        db.session.add(tasa_def)
        db.session.commit()
        tasas = [tasa_def]
    
    tasa_id = tasas[0].id_tasa
    
    reglas_data = [
        {"codigo": "SEM_10", "nombre": "Semanal 10%", "dias_intervalo": 7},
        {"codigo": "QUIN_10", "nombre": "Quincenal 10%", "dias_intervalo": 15},
        {"codigo": "MENS_10", "nombre": "Mensual 10%", "dias_intervalo": 30},
    ]
    
    print("Creando reglas iniciales...")
    for rd in reglas_data:
        exist = ReglaCredito.query.filter_by(codigo=rd["codigo"]).first()
        if not exist:
            nueva = ReglaCredito(
                codigo=rd["codigo"],
                nombre=rd["nombre"],
                id_tasa=tasa_id,
                dias_intervalo=rd["dias_intervalo"]
            )
            db.session.add(nueva)
            print(f"Regla '{rd['nombre']}' creada.")
        else:
            print(f"Regla '{rd['nombre']}' ya existe.")
            
    db.session.commit()
    print("Proceso de sembrado finalizado.")
