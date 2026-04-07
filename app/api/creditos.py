from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.extensions import db
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from app.models.catalog import Credito, DetalleCredito, TasaInteres, Cliente, Usuario, AsientoContable, MovimientoContable, ReglaCredito

bp = Blueprint("creditos", __name__)

def permission_required(permission_name):
    from functools import wraps
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            user_id = get_jwt_identity()
            user = Usuario.query.get(user_id)
            if not user:
                return jsonify({"message": "Usuario no encontrado"}), 404
            
            is_admin = any(r.rol.nombre.upper() == 'ADMIN' for r in user.roles)
            if is_admin:
                 return fn(*args, **kwargs)

            has_perm = False
            for ur in user.roles:
                for rp in ur.rol.permisos_asociados:
                    if rp.permiso.nombre == permission_name:
                        has_perm = True
                        break
                if has_perm: break
            
            if not has_perm:
                return jsonify({"message": f"Permiso denegado. Se requiere '{permission_name}'"}), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper

def calculate_plan(monto, cuotas, tasa_porcentaje, dias_intervalo=7, fecha_primer_pago=None, usar_redondeo=False, monto_redondeado=0):
    # Modelo de Negocio "José":
    # 1. Interés Total = Monto * (Tasa / 100)
    # 2. Deuda Final = Monto + Interés Total
    
    monto = float(monto)
    cuotas = int(cuotas)
    tasa_val = float(tasa_porcentaje)
    
    interes_total = monto * (tasa_val / 100.0)
    deuda_total = monto + interes_total
    
    # Desglose por cuota estándar o redondeada
    interes_por_cuota_fijo = interes_total / cuotas
    
    plan = []
    
    # Manejo de Fechas
    if fecha_primer_pago and str(fecha_primer_pago).strip():
        if isinstance(fecha_primer_pago, str):
            try:
                fecha_inicio = date.fromisoformat(fecha_primer_pago)
            except (ValueError, TypeError):
                fecha_inicio = date.today() + timedelta(days=int(dias_intervalo or 7))
        else:
            fecha_inicio = fecha_primer_pago
    else:
        fecha_inicio = date.today() + timedelta(days=int(dias_intervalo or 7))
    
    acumulado_total = 0
    
    if usar_redondeo and monto_redondeado > 0:
        # Lógica de Redondeo: Cuotas 2 a N son fijas. Cuota 1 absorbe el residuo.
        cuota_fija = float(monto_redondeado)
        total_cuotas_2_a_n = cuota_fija * (cuotas - 1)
        cuota_1 = deuda_total - total_cuotas_2_a_n
        
        for i in range(cuotas):
            vencimiento = fecha_inicio + timedelta(days=dias_intervalo * i)
            
            if i == 0:
                val_c = cuota_1
            else:
                val_c = cuota_fija
            
            # El interés se mantiene proporcional
            int_c = interes_por_cuota_fijo
            cap_c = val_c - int_c
            
            plan.append({
                "numero_cuota": i + 1,
                "monto_cuota": round(val_c, 2),
                "capital_cuota": round(cap_c, 2),
                "interes_cuota": round(int_c, 2),
                "cuota_total": round(val_c, 2),
                "fecha_vencimiento": vencimiento.isoformat()
            })
        valor_cuota_ref = cuota_fija
    else:
        # Cálculo estándar
        capital_por_cuota = monto / cuotas
        cuota_val = deuda_total / cuotas
        
        for i in range(cuotas):
            vencimiento = fecha_inicio + timedelta(days=dias_intervalo * i)
            plan.append({
                "numero_cuota": i + 1,
                "monto_cuota": round(cuota_val, 2),
                "capital_cuota": round(capital_por_cuota, 2),
                "interes_cuota": round(interes_por_cuota_fijo, 2),
                "cuota_total": round(cuota_val, 2),
                "fecha_vencimiento": vencimiento.isoformat()
            })
        valor_cuota_ref = cuota_val
        
    return {
        "monto_solicitado": round(monto, 2),
        "tasa_usada": tasa_val,
        "interes_total": round(interes_total, 2),
        "monto_total": round(deuda_total, 2),
        "cuotas": cuotas,
        "valor_cuota": round(valor_cuota_ref, 2),
        "plan": plan
    }

@bp.post("/preview")
@jwt_required()
def preview_credito():
    data = request.get_json() or {}
    try:
        try:
            monto = float(data.get("monto") or 0)
            cuotas = int(data.get("cuotas") or 0)
            # Asegurar que id_regla sea un entero para evitar error de tipos en PostgreSQL
            id_regla_raw = data.get("id_regla")
            id_regla = int(id_regla_raw) if id_regla_raw else None
            
            fecha_primer_pago = data.get("fecha_primer_pago")
            usar_redondeo = data.get("usar_redondeo", False)
            monto_redondeado = float(data.get("monto_cuota_redondeado") or 0)
        except (ValueError, TypeError):
             return jsonify({"message": "Datos numéricos inválidos"}), 400

        id_empresa = get_jwt().get("id_empresa")
        regla = ReglaCredito.query.filter_by(id_regla=id_regla, id_empresa=id_empresa).first()
        if not regla:
            return jsonify({"message": "Regla no encontrada o acceso denegado"}), 404
            
        if monto <= 0 or cuotas <= 0:
            return jsonify({"message": "Monto y cuotas deben ser mayores a 0"}), 400
            
        result = calculate_plan(monto, cuotas, regla.porcentaje, regla.dias_intervalo, fecha_primer_pago, usar_redondeo, monto_redondeado)
        return jsonify(result), 200
    except Exception as e:
        # En caso de error inesperado, retornamos 500 con el mensaje
        return jsonify({"message": "Error interno en cálculo", "error": str(e)}), 500

@bp.post("/")
@permission_required("credito.gestionar") # Assuming permission 'credito.gestionar' from user request
def create_credito():
    import traceback
    try:
        data = request.get_json() or {}
        
        # Validate inputs
        try:
            id_cliente_raw = data.get("id_cliente")
            id_cliente = int(id_cliente_raw) if id_cliente_raw else None
            
            id_regla_raw = data.get("id_regla")
            id_regla = int(id_regla_raw) if id_regla_raw else None
            
            monto = float(data.get("monto") or 0)
            cuotas = int(data.get("cuotas") or 0)
            fecha_primer_pago = data.get("fecha_primer_pago")
            usar_redondeo = data.get("usar_redondeo", False)
            monto_redondeado = float(data.get("monto_cuota_redondeado") or 0)
        except (ValueError, TypeError):
            return jsonify({"message": "Datos inválidos"}), 400

        if monto <= 0 or cuotas <= 0:
            return jsonify({"message": "Monto y cuotas deben ser mayores a 0"}), 400
            
        id_empresa = get_jwt().get("id_empresa")
        
        cliente = Cliente.query.filter_by(id_cliente=id_cliente, id_empresa=id_empresa).first()
        if not cliente: return jsonify({"message": "Cliente no encontrado o acceso denegado"}), 404
        
        regla = ReglaCredito.query.filter_by(id_regla=id_regla, id_empresa=id_empresa).first()
        if not regla: return jsonify({"message": "Regla no encontrada o acceso denegado"}), 404
        
        user_id = get_jwt_identity()
        
        # Calculate
        calc = calculate_plan(monto, cuotas, regla.porcentaje, regla.dias_intervalo, fecha_primer_pago, usar_redondeo, monto_redondeado)
        
        # Create Entities
        nuevo_credito = Credito(
            id_empresa=id_empresa,
            id_cliente=id_cliente,
            id_usuario=user_id,
            id_regla=id_regla,
            monto_solicitado=monto,
            monto_total_a_pagar=calc["monto_total"],
            cantidad_cuotas=cuotas,
            fecha_desembolso=date.today(),
            estado='PENDIENTE'
        )
        
        db.session.add(nuevo_credito)
        db.session.flush() # Get ID
        
        # Create Details
        for p in calc["plan"]:
            det = DetalleCredito(
                id_credito=nuevo_credito.id_credito,
                numero_cuota=p["numero_cuota"],
                monto_cuota=p["monto_cuota"],
                fecha_vencimiento=date.fromisoformat(p["fecha_vencimiento"]),
                monto_pagado=0,
                estado_cuota='PENDIENTE',
                capital_cuota=p["capital_cuota"],
                interes_cuota=p["interes_cuota"],
                cuota_total=p["cuota_total"]
            )
            db.session.add(det)
            
        # ---------------------------------------------------------
        # Asiento Contable de Apertura
        # ---------------------------------------------------------
        try:
            # 1. Crear Asiento
            asiento = AsientoContable(
                id_empresa=id_empresa,
                glosa=f"Desembolso Crédito #{nuevo_credito.id_credito} - {cliente.nombre} {cliente.apellido}",
                id_usuario=user_id,
                fecha=datetime.now()
            )
            db.session.add(asiento)
            db.session.flush()

            # 2. Movimientos
            
            # A) DEBE: Cuentas por Cobrar (Total Deuda = Capital + Interés)
            mov_cxc = MovimientoContable(
                id_asiento=asiento.id_asiento,
                id_empresa=id_empresa,
                cuenta='Cuentas por Cobrar',
                debe=calc["monto_total"],
                haber=0
            )
            db.session.add(mov_cxc)
            
            # B) HABER: Caja (Dinero entregado = Capital)
            mov_caja = MovimientoContable(
                id_asiento=asiento.id_asiento,
                id_empresa=id_empresa,
                cuenta='Caja',
                debe=0,
                haber=monto
            )
            db.session.add(mov_caja)
            
            # C) HABER: Intereses por Cobrar (Ganancia Futura)
            if calc["interes_total"] > 0:
                mov_int = MovimientoContable(
                    id_asiento=asiento.id_asiento,
                    id_empresa=id_empresa,
                    cuenta='Intereses por Cobrar',
                    debe=0,
                    haber=calc["interes_total"]
                )
                db.session.add(mov_int)
                
        except Exception as e_cont:
            print(f"Error al generar asiento contable: {e_cont}")

        db.session.commit()
        return jsonify({"message": "Crédito creado exitosamente", "credito": nuevo_credito.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        with open("error_diag.log", "a") as f:
            f.write(f"\n--- ERROR CREATE {datetime.now()} ---\n")
            f.write(traceback.format_exc())
            f.write("-------------------------------------\n")
        return jsonify({"message": "Error creando crédito", "error": str(e)}), 500

@bp.post("/<int:id_credito>/anular")
@permission_required("credito.gestionar")
def anular_credito(id_credito):
    id_empresa = get_jwt().get("id_empresa")
    credito = Credito.query.filter_by(id_credito=id_credito, id_empresa=id_empresa).first()
    if not credito:
        return jsonify({"message": "Crédito no encontrado o acceso denegado"}), 404

    if credito.estado == 'ANULADO':
        return jsonify({"message": "El crédito ya está anulado"}), 400

    # Validar pagos
    total_pagado = sum((d.monto_pagado or 0) for d in credito.detalles)
    if total_pagado > 0:
        return jsonify({"message": "No se puede anular un crédito con pagos registrados. Anule los pagos primero."}), 400

    try:
        # Estado
        credito.estado = 'ANULADO'
        
        # Obtener usuario
        user_id = get_jwt_identity()
        
        # ---------------------------------------------------------
        # Asiento de Reversión (Anulación)
        # ---------------------------------------------------------
        # Original: 
        #   Debe: CxC (Total)
        #   Haber: Caja (Capital)
        #   Haber: Intereses x Cobrar (Interés)
        
        # Reversión:
        #   Debe: Caja (Capital) - Reingreso lógico del dinero
        #   Debe: Intereses x Cobrar (Interés) - Cancelación del pasivo
        #   Haber: CxC (Total) - Cancelación de la deuda
        
        # Recalcular montos originales para exactitud
        original_monto = float(credito.monto_solicitado)
        original_total = float(credito.monto_total_a_pagar)
        original_interes = original_total - original_monto

        asiento = AsientoContable(
            id_empresa=id_empresa,
            glosa=f"ANULACIÓN Crédito #{credito.id_credito}",
            id_usuario=user_id,
            fecha=datetime.now()
        )
        db.session.add(asiento)
        db.session.flush()

        # A) DEBE: Caja (Devolución del Capital)
        mov_caja = MovimientoContable(
            id_asiento=asiento.id_asiento,
            id_empresa=id_empresa,
            cuenta='Caja',
            debe=original_monto,
            haber=0
        )
        db.session.add(mov_caja)

        # B) DEBE: Intereses por Cobrar (Cancelación)
        if original_interes > 0:
            mov_int = MovimientoContable(
                id_asiento=asiento.id_asiento,
                id_empresa=id_empresa,
                cuenta='Intereses por Cobrar',
                debe=original_interes,
                haber=0
            )
            db.session.add(mov_int)

        # C) HABER: Cuentas por Cobrar (Cancelación de Deuda)
        mov_cxc = MovimientoContable(
            id_asiento=asiento.id_asiento,
            id_empresa=id_empresa,
            cuenta='Cuentas por Cobrar',
            debe=0,
            haber=original_total
        )
        db.session.add(mov_cxc)

        db.session.commit()
        return jsonify({"message": "Crédito anulado exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error anulando crédito", "error": str(e)}), 500

@bp.get("/")
@permission_required("credito.gestionar")
def get_creditos():
    id_empresa = get_jwt().get("id_empresa")
    # Filtramos para no mostrar créditos ANULADOS en la operativa diaria
    creditos = Credito.query.filter(
        Credito.id_empresa == id_empresa,
        Credito.estado != 'ANULADO'
    ).order_by(Credito.id_credito.desc()).all()
    return jsonify([c.to_dict() for c in creditos]), 200

@bp.get("/cliente/<int:id_cliente>")
@permission_required("credito.gestionar")
def get_creditos_by_cliente(id_cliente):
    id_empresa = get_jwt().get("id_empresa")
    # Filtramos para no mostrar créditos ANULADOS en la operativa diaria del cliente
    creditos = Credito.query.filter(
        Credito.id_cliente == id_cliente,
        Credito.id_empresa == id_empresa,
        Credito.estado != 'ANULADO'
    ).order_by(Credito.id_credito.desc()).all()
    return jsonify([c.to_dict() for c in creditos]), 200

@bp.get("/anulados")
@permission_required("credito.gestionar")
def get_creditos_anulados():
    id_empresa = get_jwt().get("id_empresa")
    # Filtramos exclusivamente créditos ANULADOS para auditoría
    creditos = Credito.query.filter(
        Credito.id_empresa == id_empresa,
        Credito.estado == 'ANULADO'
    ).order_by(Credito.id_credito.desc()).all()
    return jsonify([c.to_dict() for c in creditos]), 200

@bp.get("/<int:id_credito>")
@permission_required("credito.gestionar")
def get_credito_by_id(id_credito):
    id_empresa = get_jwt().get("id_empresa")
    credito = Credito.query.filter_by(id_credito=id_credito, id_empresa=id_empresa).first()
    if not credito:
        return jsonify({"message": "Crédito no encontrado o acceso denegado"}), 404
    return jsonify(credito.to_dict()), 200
