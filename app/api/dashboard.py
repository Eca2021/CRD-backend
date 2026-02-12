# app/api/dashboard.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, date, timedelta
from sqlalchemy import func, case, extract

from app.extensions import db
from app.models.catalog import (
    Credito, DetalleCredito, Pago, MovimientoContable, AsientoContable
)

bp = Blueprint("dashboard", __name__)

@bp.get("/summary")
@jwt_required()
def get_dashboard_summary():
    try:
        today = date.today()
        
        # ---------------------------------------------------------
        # KPI 1: Disponibilidad en Caja (Capital Operativo)
        # ---------------------------------------------------------
        # SELECT SUM(debe) - SUM(haber) FROM movimientos_contables WHERE cuenta = 'Caja'
        capital_operativo = db.session.query(
            func.coalesce(func.sum(MovimientoContable.debe - MovimientoContable.haber), 0)
        ).filter(MovimientoContable.cuenta == 'Caja').scalar()

        # ---------------------------------------------------------
        # KPI 2: Salud de la Cartera
        # ---------------------------------------------------------
        
        # A) Total Colocado (Cartera Activa)
        # Suma de monto_total_a_pagar de creditos donde estado = 'PENDIENTE'
        cartera_activa = db.session.query(
            func.coalesce(func.sum(Credito.monto_total_a_pagar), 0)
        ).filter(Credito.estado == 'PENDIENTE').scalar()

        # B) Índice de Mora (Crítico)
        # Suma de cuota_total de detalles_credito donde fecha_vencimiento < HOY y estado_cuota = 'PENDIENTE'
        mora_vencida = db.session.query(
            func.coalesce(func.sum(DetalleCredito.cuota_total), 0)
        ).filter(
            DetalleCredito.estado_cuota == 'PENDIENTE',
            DetalleCredito.fecha_vencimiento < today
        ).scalar()

        # C) Recaudación Mensual
        # Suma de monto_pagado en la tabla pagos filtrado por el mes actual
        current_month = today.month
        current_year = today.year
        recaudacion_mensual = db.session.query(
            func.coalesce(func.sum(Pago.monto_pagado), 0)
        ).filter(
            extract('month', Pago.fecha_pago) == current_month,
            extract('year', Pago.fecha_pago) == current_year
        ).scalar()

        # ---------------------------------------------------------
        # KPI 4: Gráfico de Flujo de Caja (Últimos 30 días)
        # ---------------------------------------------------------
        # Eje X: Fecha.
        # Serie 1 (Ingresos): Suma del debe de 'Caja' por día.
        # Serie 2 (Egresos): Suma del haber de 'Caja' por día.
        
        start_date = today - timedelta(days=30)
        
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

        # ---------------------------------------------------------
        # EXTRA: Estado de Cartera (Para PieChart)
        # ---------------------------------------------------------
        # Al Día vs En Mora
        # Vamos a aproximarlo con los totales que ya tenemos
        # Al Día = Cartera Activa - Mora Vencida (aprox, asumiendo que cartera activa incluye todo lo pendiente)
        # Nota: Cartera Activa es monto_total_a_pagar del Credito. Mora es suma de cuotas. 
        # Puede haber discrepancias si un credito está parcialmente pagado.
        # Mejor calculamos Mora Total (ya lo tenemos) y Cartera al Día (Cartera Activa - Mora Total ? No exacto).
        # Vamos a sumar todas las cuotas pendientes que NO están vencidas para "Al Día".
        
        cartera_al_dia = db.session.query(
            func.coalesce(func.sum(DetalleCredito.cuota_total), 0)
        ).filter(
            DetalleCredito.estado_cuota == 'PENDIENTE',
            DetalleCredito.fecha_vencimiento >= today
        ).scalar()

        portfolio_status = [
            {"name": "Al Día", "value": float(cartera_al_dia)},
            {"name": "En Mora", "value": float(mora_vencida)}
        ]

        # ---------------------------------------------------------
        # EXTRA: Ganancias (Intereses)
        # ---------------------------------------------------------
        # 1. Ganancia TOTAL que ya cobraste (Dinero real ganado históricamente)
        ganancia_cobrada = db.session.query(
            func.coalesce(func.sum(DetalleCredito.interes_cuota), 0)
        ).filter(DetalleCredito.estado_cuota == 'PAGADO').scalar()

        # 2. Ganancia que falta cobrar (Dinero futuro)
        ganancia_futura = db.session.query(
            func.coalesce(func.sum(DetalleCredito.interes_cuota), 0)
        ).filter(DetalleCredito.estado_cuota == 'PENDIENTE').scalar()

        return jsonify({
            "capital_operativo": float(capital_operativo),
            "cartera_activa": float(cartera_activa),
            "mora_vencida": float(mora_vencida),
            "recaudacion_mensual": float(recaudacion_mensual),
            "cash_flow_chart": chart_data,
            "portfolio_status": portfolio_status,
            "ganancia_cobrada": float(ganancia_cobrada),
            "ganancia_futura": float(ganancia_futura)
        }), 200

    except Exception as e:
        print(f"Error in dashboard summary: {str(e)}") # Log error for debug
        return jsonify({"message": "Error cargando dashboard", "error": str(e)}), 500
