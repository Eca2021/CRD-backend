from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.catalog import AsientoContable, MovimientoContable, Usuario
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, case

bp = Blueprint('contabilidad', __name__)

@bp.get("/dashboard")
@jwt_required()
def get_dashboard_data():
    """
    Retorna los saldos actuales de las cuentas principales y datos para el gráfico de flujo de caja.
    """
    try:
        # 1. Saldo CAJA (Debe - Haber)
        saldo_caja = db.session.query(
            func.coalesce(func.sum(MovimientoContable.debe - MovimientoContable.haber), 0)
        ).filter(MovimientoContable.cuenta == 'Caja').scalar()

        # 2. Saldo CUENTAS POR COBRAR (Debe - Haber)
        saldo_cxc = db.session.query(
            func.coalesce(func.sum(MovimientoContable.debe - MovimientoContable.haber), 0)
        ).filter(MovimientoContable.cuenta == 'Cuentas por Cobrar').scalar()

        # 3. Saldo GANANCIAS POR INTERESES (Haber - Debe) [Ganancia es Acreedora]
        saldo_ganancias = db.session.query(
            func.coalesce(func.sum(MovimientoContable.haber - MovimientoContable.debe), 0)
        ).filter(MovimientoContable.cuenta == 'Ganancias por Intereses').scalar()

        # 4. Datos para Gráfico (Últimos 7 días) - Flujo de CAJA
        today = datetime.now().date()
        start_date = today - timedelta(days=6)
        
        # Agrupar entradas (Debe) y salidas (Haber) de Caja por fecha
        chart_data_query = db.session.query(
            func.date(AsientoContable.fecha).label('fecha'),
            func.sum(case((MovimientoContable.debe > 0, MovimientoContable.debe), else_=0)).label('ingresos'),
            func.sum(case((MovimientoContable.haber > 0, MovimientoContable.haber), else_=0)).label('egresos')
        ).join(AsientoContable)\
         .filter(MovimientoContable.cuenta == 'Caja')\
         .filter(AsientoContable.fecha >= start_date)\
         .group_by(func.date(AsientoContable.fecha))\
         .order_by(func.date(AsientoContable.fecha)).all()

        chart_data = []
        for row in chart_data_query:
            chart_data.append({
                "fecha": row.fecha.strftime('%Y-%m-%d'),
                "ingresos": float(row.ingresos or 0),
                "egresos": float(row.egresos or 0)
            })

        return jsonify({
            "capital_operativo": float(saldo_caja),
            "cuentas_por_cobrar": float(saldo_cxc),
            "ganancias_reales": float(saldo_ganancias),
            "chart_data": chart_data
        }), 200

    except Exception as e:
        return jsonify({"message": "Error cargando dashboard contable", "error": str(e)}), 500

@bp.get("/asientos")
@jwt_required()
def get_asientos():
    """
    Listar asientos contables con sus movimientos.
    Filtros opcionales: fecha_inicio, fecha_fin, glosa
    """
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    glosa = request.args.get('glosa')

    query = AsientoContable.query.order_by(AsientoContable.fecha.desc())

    if fecha_inicio:
        query = query.filter(AsientoContable.fecha >= fecha_inicio)
    if fecha_fin:
        # Ajustar fin del día para fecha_fin
        query = query.filter(AsientoContable.fecha <= f"{fecha_fin} 23:59:59")
    if glosa:
        query = query.filter(AsientoContable.glosa.ilike(f"%{glosa}%"))

    asientos = query.limit(100).all() # Limitar a los últimos 100 por defecto para rendimiento

    return jsonify([a.to_dict() for a in asientos]), 200

@bp.post("/asientos")
@jwt_required()
def create_asiento_manual():
    """
    Permite registrar un movimiento manual (ej: Gastos de Luz, Inyección de Capital).
    Se asume que afecta 'Caja' y otra cuenta especificada.
    """
    data = request.json
    glosa = data.get('glosa')
    tipo = data.get('tipo') # 'INGRESO' o 'EGRESO' de Caja
    monto = data.get('monto')
    otra_cuenta = data.get('otra_cuenta') # Ej: 'Gastos Generales', 'Capital Social'

    if not all([glosa, tipo, monto, otra_cuenta]):
        return jsonify({"message": "Datos incompletos"}), 400

    try:
        user_id = get_jwt_identity()
        monto = float(monto)

        asiento = AsientoContable(
            glosa=glosa,
            id_usuario=user_id,
            fecha=datetime.now()
        )
        db.session.add(asiento)
        db.session.flush()

        if tipo == 'INGRESO':
            # Caja: Debe (Entra plata)
            # Otra Cuenta: Haber (Contrapartida)
            mov_caja = MovimientoContable(id_asiento=asiento.id_asiento, cuenta='Caja', debe=monto, haber=0)
            mov_contra = MovimientoContable(id_asiento=asiento.id_asiento, cuenta=otra_cuenta, debe=0, haber=monto)
        
        elif tipo == 'EGRESO':
            # Caja: Haber (Sale plata)
            # Otra Cuenta: Debe (Gasto/Activo)
            mov_contra = MovimientoContable(id_asiento=asiento.id_asiento, cuenta=otra_cuenta, debe=monto, haber=0)
            mov_caja = MovimientoContable(id_asiento=asiento.id_asiento, cuenta='Caja', debe=0, haber=monto)
        
        else:
            return jsonify({"message": "Tipo debe ser INGRESO o EGRESO"}), 400

        db.session.add(mov_caja)
        db.session.add(mov_contra)
        db.session.commit()

        return jsonify({"message": "Movimiento registrado exitosamente"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error registrando movimiento", "error": str(e)}), 500
@bp.post("/apertura")
@jwt_required()
def apertura_capital():
    """
    Endpoint para Apertura de Capital (Caja Inicial).
    Crea un asiento y movimientos:
    - Caja: Debe (Entrada)
    - Capital Propio: Haber (Contrapartida)
    """
    data = request.json
    monto = data.get('monto')
    
    if not monto:
        return jsonify({"message": "El monto es obligatorio"}), 400

    try:
        user_id = get_jwt_identity()
        monto = float(monto)

        asiento = AsientoContable(
            glosa="Apertura de Capital",
            id_usuario=user_id,
            fecha=datetime.now()
        )
        db.session.add(asiento)
        db.session.flush()

        # Movimiento 1: Ingreso a Caja
        mov_caja = MovimientoContable(
            id_asiento=asiento.id_asiento, 
            cuenta='Caja', 
            debe=monto, 
            haber=0
        )
        
        # Movimiento 2: Capital Propio (Contrapartida)
        mov_capital = MovimientoContable(
            id_asiento=asiento.id_asiento, 
            cuenta='Capital Propio', 
            debe=0, 
            haber=monto
        )

        db.session.add(mov_caja)
        db.session.add(mov_capital)
        db.session.commit()

        return jsonify({"message": "Apertura de capital registrada exitosamente."}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error en apertura de capital", "error": str(e)}), 500
