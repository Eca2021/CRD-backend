from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.catalog import Pago, FormaPago, DetalleCredito, Credito, AsientoContable, MovimientoContable, PagoAudit
from datetime import datetime

bp = Blueprint("pagos", __name__)

@bp.get("/formas_pago")
@jwt_required()
def get_formas_pago():
    formas = FormaPago.query.all()
    return jsonify([f.to_dict() for f in formas]), 200

@bp.post("/")
@jwt_required()
def registrar_pago():
    print(">>> ¡PETICIÓN RECIBIDA EN /PAGOS/! <<<") # Sensor
    data = request.get_json() or {}
    print(f">>> Datos recibidos: {data}")          # Sensor de datos
    
    try:
        id_detalle = data.get("id_detalle_credito")
        id_forma = data.get("id_forma_pago")
        # Robust parsing for monto
        raw_monto = data.get("monto_pagado")
        if raw_monto is None or str(raw_monto).strip() == "":
            monto = 0.0
        else:
            monto = float(raw_monto)
        comprobante = data.get("comprobante_nro")
    except (ValueError, TypeError):
        return jsonify({"message": "Formato de monto inválido", "error": "Invalid numeric format"}), 400
    except Exception as e:
        return jsonify({"message": "Error al procesar datos", "error": str(e)}), 400

    if monto <= 0:
        return jsonify({"message": "El monto debe ser mayor a 0"}), 400

    print(f">>> Analizando pago para Detalle #{id_detalle}, Forma #{id_forma}, Monto {monto}")
    
    try:
        detalle = DetalleCredito.query.get(id_detalle)
        if not detalle:
            print(f">>> ERROR: Cuota #{id_detalle} no encontrada")
            return jsonify({"message": "Cuota no encontrada"}), 404

        credito = Credito.query.get(detalle.id_credito)
        print(f">>> Crédito asociado: #{credito.id_credito if credito else 'N/A'}")

        forma = FormaPago.query.get(id_forma)
        if not forma:
            print(f">>> ERROR: Forma de pago #{id_forma} no encontrada")
            return jsonify({"message": "Forma de pago no encontrada"}), 404
            
        # Registrar Pago
        user_id = get_jwt_identity()
        nuevo_pago = Pago(
            id_detalle_credito=id_detalle,
            id_forma_pago=id_forma,
            id_usuario=user_id,
            monto_pagado=monto,
            fecha_pago=datetime.now(),
            comprobante_nro=comprobante
        )
        db.session.add(nuevo_pago)
        print(">>> Pago agregado a la sesión")
    except Exception as e:
        print(f">>> ERROR AL INICIAR PAGO: {str(e)}")
        db.session.rollback()
        return jsonify({"message": "Error al iniciar proceso de pago", "error": str(e)}), 500
    
    # ---------------------------------------------------------
    # Generación de Asiento Contable Automático
    # ---------------------------------------------------------
    try:
        user_id = get_jwt_identity()
        
        # 1. Crear Asiento
        asiento = AsientoContable(
            glosa=f"Pago de Cuota #{detalle.numero_cuota} - Crédito #{credito.id_credito} - {forma.nombre}",
            id_usuario=user_id,
            fecha=datetime.now()
        )
        db.session.add(asiento)
        db.session.flush() # Para tener el ID del asiento
        
        # 2. Calcular proporción de Capital vs Interés
        # Si el crédito es antiguo y no tiene desglosado, asumimos todo a capital por defecto o 0 interés.
        total_esperado = float(detalle.cuota_total or 0)
        cap_esperado = float(detalle.capital_cuota or 0)
        int_esperado = float(detalle.interes_cuota or 0)
        
        pago_capital = 0.0
        pago_interes = 0.0
        
        if total_esperado > 0:
            # Proporcional
            ratio_cap = cap_esperado / total_esperado
            ratio_int = int_esperado / total_esperado
            
            pago_capital = monto * ratio_cap
            pago_interes = monto * ratio_int
        else:
            # Fallback para créditos antiguos o sin datos: Todo a Capital (Cuentas por Cobrar)
            pago_capital = monto
            pago_interes = 0.0
            
        # 3. Movimientos Contables
        
        # Movimientos Contables
        
        # A) Entrada a CAJA (Debe: Total Pagado)
        mov_caja = MovimientoContable(
            id_asiento=asiento.id_asiento,
            cuenta='Caja',
            debe=monto,
            haber=0
        )
        db.session.add(mov_caja)
        
        # B) Salida de CUENTAS POR COBRAR (Haber: Total Pagado - para rebajar la deuda bruta creada al inicio)
        # En el modelo "José", CxC nace con Capital + Interés. Al pagar, CxC baja.
        mov_cxp = MovimientoContable(
            id_asiento=asiento.id_asiento,
            cuenta='Cuentas por Cobrar',
            debe=0,
            haber=monto
        )
        db.session.add(mov_cxp)
            
        # C) Devengación de Intereses (Ajuste)
        if pago_interes > 0:
            # 1. Damos de baja el "Interés por Cobrar" (Pasivo Diferido) que creamos al inicio (Debe)
            mov_int_deferred = MovimientoContable(
                id_asiento=asiento.id_asiento,
                cuenta='Intereses por Cobrar',
                debe=round(pago_interes, 2),
                haber=0
            )
            db.session.add(mov_int_deferred)

            # 2. Reconocemos la Ganancia Real (Haber)
            mov_int_income = MovimientoContable(
                id_asiento=asiento.id_asiento,
                cuenta='Ganancias por Intereses',
                debe=0,
                haber=round(pago_interes, 2)
            )
            db.session.add(mov_int_income)
            
    except Exception as e:
        print(f">>> ERROR CRÍTICO CONTABILIDAD: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"message": "Error generando contabilidad", "error": str(e)}), 500
        
    # ---------------------------------------------------------
    
    try:
        # Actualizar Detalle
        detalle.monto_pagado = float(detalle.monto_pagado or 0) + monto
        if detalle.monto_pagado >= float(detalle.monto_cuota or 0):
            detalle.estado_cuota = 'PAGADO'
        
        # Verificar si el Crédito se paga por completo
        credito = Credito.query.get(detalle.id_credito)
        all_detalles = DetalleCredito.query.filter_by(id_credito=credito.id_credito).all()
        
        todas_pagadas = True
        for d in all_detalles:
            if d.estado_cuota != 'PAGADO':
                todas_pagadas = False
                break
                
        if todas_pagadas:
            credito.estado = 'PAGADO'
    except Exception as update_err:
        print(f">>> ERROR ACTUALIZANDO ESTADOS: {str(update_err)}")
        db.session.rollback()
        return jsonify({"message": "Error al actualizar estados de cuota/crédito", "error": str(update_err)}), 500

    try:
        db.session.commit()
        
        # 4. Registrar Auditoría (después del commit para tener el id_pago final)
        try:
            audit = PagoAudit(
                id_pago=nuevo_pago.id_pago,
                id_usuario=user_id,
                accion='CREACION',
                monto_registrado=monto,
                id_detalle_credito=id_detalle,
                estado_pago_momento='ACTIVO',
                direccion_ip=request.remote_addr,
                observacion=f"Pago registrado vía Caja. Comprobante: {comprobante or 'N/A'}"
            )
            db.session.add(audit)
            db.session.commit()
        except Exception as audit_err:
            print(f"Error en auditoría (no bloqueante): {audit_err}")

        return jsonify({"message": "Pago registrado exitosamente", "pago": nuevo_pago.to_dict()}), 201
    except Exception as e:
        print(f">>> ERROR FINAL COMMIT: {str(e)}")
        db.session.rollback()
        return jsonify({"message": "Error registrando pago", "error": str(e)}), 500
@bp.get("/")
@jwt_required()
def get_pagos():
    pagos = Pago.query.order_by(Pago.id_pago.desc()).all()
    return jsonify([p.to_dict() for p in pagos]), 200

@bp.get("/detalle/<int:id_detalle>")
@jwt_required()
def get_pagos_by_detalle(id_detalle):
    pagos = Pago.query.filter_by(id_detalle_credito=id_detalle).order_by(Pago.id_pago.desc()).all()
    return jsonify([p.to_dict() for p in pagos]), 200

@bp.post("/<int:id_pago>/anular")
@jwt_required()
def anular_pago(id_pago):
    pago = Pago.query.get(id_pago)
    if not pago:
        return jsonify({"message": "Pago no encontrado"}), 404

    if pago.estado == 'ANULADO':
        return jsonify({"message": "El pago ya está anulado"}), 400

    detalle = DetalleCredito.query.get(pago.id_detalle_credito)
    credito = Credito.query.get(detalle.id_credito)
    forma = FormaPago.query.get(pago.id_forma_pago)
    
    monto = float(pago.monto_pagado or 0)
    user_id = get_jwt_identity()

    try:
        # 1. Anular el registro del pago
        pago.estado = 'ANULADO'
        
        # 2. Revertir montos en el Detalle
        detalle.monto_pagado = float(detalle.monto_pagado or 0) - monto
        if detalle.estado_cuota == 'PAGADO' and detalle.monto_pagado < float(detalle.monto_cuota or 0):
            detalle.estado_cuota = 'PENDIENTE'
            
        # 3. Revertir estado del Crédito
        if credito.estado == 'PAGADO':
            credito.estado = 'PENDIENTE'
            
        # 4. Asiento Contable de Reversión
        asiento = AsientoContable(
            glosa=f"REVERSIÓN Pago #{pago.id_pago} - Cuota #{detalle.numero_cuota} - Crédito #{credito.id_credito}",
            id_usuario=user_id,
            fecha=datetime.now()
        )
        db.session.add(asiento)
        db.session.flush()

        # Calcular proporciones para reversión contable (igual que al registrar)
        total_esperado = float(detalle.cuota_total or 0)
        cap_esperado = float(detalle.capital_cuota or 0)
        int_esperado = float(detalle.interes_cuota or 0)
        
        pago_interes = 0.0
        if total_esperado > 0:
            ratio_int = int_esperado / total_esperado
            pago_interes = monto * ratio_int

        # A) SALIDA de CAJA (Haber)
        mov_caja = MovimientoContable(
            id_asiento=asiento.id_asiento,
            cuenta='Caja',
            debe=0,
            haber=monto
        )
        db.session.add(mov_caja)
        
        # B) REPOSICIÓN de CUENTAS POR COBRAR (Debe)
        mov_cxc = MovimientoContable(
            id_asiento=asiento.id_asiento,
            cuenta='Cuentas por Cobrar',
            debe=monto,
            haber=0
        )
        db.session.add(mov_cxc)
        
        # C) Reversión de Ganancia de Interés
        if pago_interes > 0:
            # Revertimos el Pasivo Diferido (Haber: vuelve a estar por cobrar)
            mov_int_deferred = MovimientoContable(
                id_asiento=asiento.id_asiento,
                cuenta='Intereses por Cobrar',
                debe=0,
                haber=round(pago_interes, 2)
            )
            db.session.add(mov_int_deferred)

            # Revertimos la Ganancia Real (Debe: ya no es ganancia)
            mov_int_income = MovimientoContable(
                id_asiento=asiento.id_asiento,
                cuenta='Ganancias por Intereses',
                debe=round(pago_interes, 2),
                haber=0
            )
            db.session.add(mov_int_income)

        db.session.commit()

        # 5. Registrar Auditoría
        try:
            audit = PagoAudit(
                id_pago=pago.id_pago,
                id_usuario=user_id,
                accion='ANULACION',
                monto_registrado=monto,
                id_detalle_credito=pago.id_detalle_credito,
                estado_pago_momento='ANULADO',
                direccion_ip=request.remote_addr,
                observacion="Anulación de pago realizada por el usuario."
            )
            db.session.add(audit)
            db.session.commit()
        except Exception as audit_err:
            print(f"Error en auditoría (no bloqueante): {audit_err}")

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error anulando pago", "error": str(e)}), 500

@bp.get("/auditoria")
@jwt_required()
def get_auditoria_pagos():
    query = PagoAudit.query.order_by(PagoAudit.id_audit.desc()).all()
    return jsonify([a.to_dict() for a in query]), 200
