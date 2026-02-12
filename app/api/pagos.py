from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.catalog import Pago, FormaPago, DetalleCredito, Credito, AsientoContable, MovimientoContable
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
    data = request.get_json() or {}
    
    try:
        id_detalle = data.get("id_detalle_credito")
        id_forma = data.get("id_forma_pago")
        monto = float(data.get("monto_pagado", 0))
        comprobante = data.get("comprobante_nro")
    except:
        return jsonify({"message": "Datos inválidos"}), 400

    if monto <= 0:
        return jsonify({"message": "El monto debe ser mayor a 0"}), 400

    detalle = DetalleCredito.query.get(id_detalle)
    if not detalle:
        return jsonify({"message": "Cuota no encontrada"}), 404

    credito = Credito.query.get(detalle.id_credito)

    forma = FormaPago.query.get(id_forma)
    if not forma:
        return jsonify({"message": "Forma de pago no encontrada"}), 404
        
    # Validar que no pague de más (opcional, pero recomendado)
    saldo_pendiente = float(detalle.monto_cuota) - float(detalle.monto_pagado)
    # Permitemos pagar lo que sea, pero si supera, el estado será PAGADO igual.
    # Podríamos validar: if monto > saldo_pendiente: return error...
    
    # Registrar Pago
    nuevo_pago = Pago(
        id_detalle_credito=id_detalle,
        id_forma_pago=id_forma,
        monto_pagado=monto,
        fecha_pago=datetime.now(),
        comprobante_nro=comprobante
    )
    db.session.add(nuevo_pago)
    
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
        # Si falla la contabilidad, ¿fallamos todo el pago? 
        # Generalmente sí para mantener integridad.
        db.session.rollback()
        return jsonify({"message": "Error generando contabilidad", "error": str(e)}), 500
        
    # ---------------------------------------------------------
    
    # Actualizar Detalle
    detalle.monto_pagado = float(detalle.monto_pagado) + monto
    if detalle.monto_pagado >= float(detalle.monto_cuota):
        detalle.estado_cuota = 'PAGADO'
    
    # Verificar si el Crédito se paga por completo
    credito = Credito.query.get(detalle.id_credito)
    all_detalles = DetalleCredito.query.filter_by(id_credito=credito.id_credito).all()
    
    # Si TODAS las cuotas están PAGADAS -> Crédito PAGADO
    # Ojo: acabamos de actualizar 'detalle' en session, así que all_detalles (si es query fresca) 
    # podría no tener el cambio si no hacemos flush, pero como es el mismo objeto en identidad SQLAlchemy, debería estar bien.
    # Para estar seguros, verificamos lógica:
    
    todas_pagadas = True
    for d in all_detalles:
        # Usamos los valores actuales (incluyendo el cambio en 'detalle')
        if d.estado_cuota != 'PAGADO':
            todas_pagadas = False
            break
            
    if todas_pagadas:
        credito.estado = 'PAGADO'

    try:
        db.session.commit()
        return jsonify({"message": "Pago registrado exitosamente", "pago": nuevo_pago.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error registrando pago", "error": str(e)}), 500
