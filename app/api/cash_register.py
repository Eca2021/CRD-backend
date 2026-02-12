# app/api/cash_register.py  (versión alineada al monolito)
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import func, or_
from decimal import Decimal
from app.extensions import db
from datetime import datetime, timedelta
from app.models.catalog import (
    CashRegister, CashRegisterStatus, CashRegisterMovement,
    MovementType, Cash, Branch, PaymentMethod, Usuario
)

# Helper para clasificar métodos de pago (fallback simple si falta util)
try:
    from app.utils import clasificar_forma_pago
except Exception:
    def clasificar_forma_pago(nombre: str) -> str:
        n = (nombre or "").strip().lower()
        if "efectivo" in n or n == "cash": return "efectivo"
        if "tarjeta" in n or "credit" in n or "debit" in n: return "tarjeta"
        if "crédito" in n or "credito" in n: return "credito"
        if "transfer" in n or "transferencia" in n: return "transferencia"
        if "qr" in n or "pix" in n: return "qr"
        return "otro"

bp = Blueprint("cash_register", __name__)

@bp.get("/ping")
def ping():
    return jsonify({"cash_register": "ok"}), 200


# ---------------------- helpers de estados ----------------------

def _status_row_ci(nombre_busqueda: str):
    """Busca por nombre case-insensitive (admite 'abierta', 'open', 'cerrada', etc.)."""
    nombre_busqueda = (nombre_busqueda or "").strip()
    return db.session.execute(
        db.select(CashRegisterStatus)
        .where(func.lower(CashRegisterStatus.status_name) == func.lower(nombre_busqueda))
    ).scalar_one_or_none()

def _status_id_ci(nombre_busqueda: str) -> int | None:
    """Retorna el ID de estado."""
    status_row = _status_row_ci(nombre_busqueda)
    return getattr(status_row, "id", None)

def _find_active_cash_register_for_cash_id(cash_id: int):
    """
    Busca la caja activa (status 'ABIERTA') para un registro físico específico (cash_id).
    """
    st_abierta_id = _status_id_ci("ABIERTO")
    if not st_abierta_id:
        return None

    # Ordenar por fecha_apertura DESC para asegurar que obtenemos la MÁS reciente
    return db.session.execute(
        db.select(CashRegister)
        .where(
            CashRegister.cash_id == cash_id,
            CashRegister.status_id == st_abierta_id,
        )
        .order_by(CashRegister.opened_at.desc())
    ).scalar_one_or_none()


# ---------------------- NUEVOS ENDPOINTS PARA CONTROL DE USUARIO ----------------------

@bp.get("/active_status")
@jwt_required()
def get_active_cash_register():
    """
    ENDPOINT CRUCIAL: Verifica si el usuario logueado ya tiene una
    caja abierta a su nombre. Esto resuelve el problema de la sesión compartida.
    """
    user_id = get_jwt_identity()

    # 1. CORRECCIÓN: Estás buscando la cadena "1" en lugar del nombre "ABIERTO".
    # st_abierta_id = _status_id_ci("1")  <-- ANTES
    
    # Después: Usar el nombre de estado que existe en tu DB, que es "ABIERTO".
    st_abierta_id = _status_id_ci("ABIERTO")

    if not st_abierta_id:
        # 2. CORRECCIÓN: También corregimos el mensaje de error por consistencia.
        return jsonify({"message": "Error de configuración: Estado 'ABIERTO' no encontrado."}), 500

    # Buscar la caja ABIERTA, abierta por ESTE usuario.
    active_register = db.session.execute(
        db.select(CashRegister)
        .where(
            # Nota: Si el campo de la DB es 'id_usuario' (como en el POST)
            # o 'opened_by_user_id' (como en el find_active), asegúrate de usar el correcto.
            # En tu código usas id_usuario, lo mantendremos así por ahora.
            CashRegister.id_usuario == int(user_id),
            CashRegister.status_id == st_abierta_id
        )
        .order_by(CashRegister.opened_at.desc())
    ).scalar_one_or_none()

    if active_register:
        # Devuelve los datos de la caja activa (solo lo necesario)
        return jsonify({
            "active_cash_register_id": active_register.id,
            "branch_id": active_register.branch_id,
            "cash_id": active_register.cash_id,
            "opening_date": active_register.opened_at.isoformat(),
            # 3. CORRECCIÓN/AJUSTE: opened_by_username debe mostrar el ID o el nombre.
            # Como estás usando id_usuario en el WHERE, es mejor llamarlo id_usuario en el retorno
            "opened_by_user_id": active_register.id_usuario # <-- Ajuste del nombre
        }), 200
    else:
        # No hay caja activa para este usuario
        return jsonify({"active_cash_register_id": None}), 200


# ---------------------- LOGICA DE APERTURA DE CAJA ----------------------

# ---------------------- LOGICA DE APERTURA DE CAJA ----------------------

@bp.post("/")
@jwt_required()
def open_cash_register():
    """Abre una nueva caja."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    cash_id = data.get("cash_id")
    branch_id = data.get("branch_id")
    opening_amount = Decimal(data.get("opening_amount", 0))

    if not cash_id or not branch_id or opening_amount is None:
        return jsonify({"message": "Faltan campos obligatorios: cash_id, branch_id y opening_amount."}), 400

    # 1. VERIFICAR si el USUARIO ya tiene una caja abierta (CRÍTICO)
    st_abierta_id = _status_id_ci("ABIERTO")
    if not st_abierta_id:
        return jsonify({"message": "Error de configuración: Estado 'ABIERTO' no encontrado."}), 500

    active_register = db.session.execute(
        db.select(CashRegister)
        .where(
            # 🛑 CORRECCIÓN 1: Usar el atributo correcto del modelo: 'id_usuario'
            CashRegister.id_usuario == int(user_id), 
            CashRegister.status_id == st_abierta_id,
            CashRegister.closed_at.is_(None)
        )
    ).scalar_one_or_none()
    
    if active_register:
        # Si encuentra, el usuario ya tiene una sesión.
        return jsonify({
            "message": f"El usuario {user_id} ya tiene una caja abierta (ID: {active_register.id}) y debe cerrarla antes de abrir otra.",
            "active_cash_register_id": active_register.id
        }), 409 # Conflicto

    # 2. VERIFICAR si la CAJA FISICA (cash_id) ya está siendo usada por OTRO usuario
    cash_used = _find_active_cash_register_for_cash_id(cash_id)

    # 🛑 CORRECCIÓN 2: El error actual. Usar 'id_usuario' en lugar de 'opened_by_user_id'
    if cash_used and cash_used.id_usuario != int(user_id):
        # Si la caja física está abierta por otro usuario, se bloquea.
        # También corregimos el acceso a 'opened_by_user' ya que no lo has definido en el modelo.
        return jsonify({
            "message": f"La caja (ID: {cash_id}) ya está en uso por otro usuario. Debe esperar a que cierren o elegir otra caja.",
            # No podemos obtener el nombre de usuario sin hacer un join. Eliminamos la línea conflictiva.
        }), 409 # Conflicto

    # 3. Crear el nuevo registro de caja
    try:
        new_register = CashRegister(
            cash_id=cash_id,
            branch_id=branch_id,
            opened_at=datetime.utcnow(),
            id_usuario=int(user_id),
            initial_amount=opening_amount,
            status_id=st_abierta_id
        )
        db.session.add(new_register)
        db.session.flush() # Para obtener el ID

        # 4. Registrar movimiento inicial de apertura
        
        # 🛑 CORRECCIÓN 3.1: Buscar APERTURA en MovementType (tabla correcta)
        apertura_mt = db.session.execute(
            db.select(MovementType).where(func.lower(MovementType.name) == func.lower('APERTURA'))
        ).scalar_one_or_none()

        if opening_amount > 0 and not apertura_mt:
            raise ValueError("Error de configuración: Tipo de Movimiento 'APERTURA' no encontrado en el catálogo MovementType.")
            
        st_apertura_id = apertura_mt.id if apertura_mt else None

        if st_apertura_id:
            # 🛑 CORRECCIÓN 3.2: Validar que 'efectivo' existe en PaymentMethod antes de acceder a .id
            efectivo_pm = db.session.execute(
                db.select(PaymentMethod).where(func.lower(PaymentMethod.name) == func.lower('efectivo'))
            ).scalar_one_or_none()

            if opening_amount > 0 and not efectivo_pm:
                 raise ValueError("Error de configuración: Método de Pago 'efectivo' no encontrado (necesario para la apertura).")

            db.session.add(CashRegisterMovement(
                cash_register_id=new_register.id,
                movement_type_id=st_apertura_id,
                amount=opening_amount,
                description="Apertura Caja",
                payment_method_id=efectivo_pm.id # Acceso seguro
            ))

        db.session.commit()
        return jsonify({
            "message": "Caja abierta exitosamente",
            "cash_register_id": new_register.id
        }), 201
    except Exception as e:
        db.session.rollback()
        # ⚠️ Devolver el mensaje de la excepción para un mejor diagnóstico
        return jsonify({"message": f"Error al abrir la caja: {str(e)}"}), 500

# ---------------------- abrir caja ----------------------
@bp.post("/open")
@jwt_required()
def open_register():
    data = request.get_json() or {}
    cash_id   = data.get("cash_id")
    branch_id = data.get("branch_id")
    user_id   = data.get("user_id") or get_jwt_identity()

    # ⛔ exigir que venga opening_amount (no aceptar por defecto 0 silencioso)
    if "opening_amount" not in data:
        return jsonify({"msg": "opening_amount requerido"}), 400
    try:
        opening = Decimal(str(data.get("opening_amount")))
        if opening < 0:
            return jsonify({"msg": "opening_amount no puede ser negativo"}), 400
    except Exception:
        return jsonify({"msg": "opening_amount inválido"}), 400

    if not cash_id:   return jsonify({"msg": "cash_id requerido"}), 400
    if not branch_id: return jsonify({"msg": "branch_id requerido"}), 400
    if not user_id:   return jsonify({"msg": "user_id (o JWT identity) requerido"}), 400
    if not Cash.query.get(cash_id):     return jsonify({"msg": "Caja (cash_id) inexistente"}), 404
    if not Branch.query.get(branch_id): return jsonify({"msg": "Sucursal (branch_id) inexistente"}), 404

    # Estados a considerar como "ocupando" una caja
    # ABIERTO, PENDIENTE y EN_REVISION (independientemente de cómo estén escritos)
    ocupados_ids = _status_id_any_ci(["ABIERTO", "PENDIENTE", "EN_REVISION", "EN REVISIÓN"])

    q = CashRegister.query.filter(
        CashRegister.cash_id == cash_id,
        CashRegister.branch_id == branch_id,
        CashRegister.id_usuario == int(user_id)
    )
    if ocupados_ids:
        q = q.filter(CashRegister.status_id.in_(ocupados_ids))

    ya_abierta = q.first()
    if ya_abierta:
        return jsonify({
            "msg": "No se puede abrir: existe una caja abierta o pendiente de auditoría para esa sucursal/caja.",
            "cash_register_id": ya_abierta.id
        }), 400

    st_abierto_id = _status_id_ci("ABIERTO") or _status_id_ci("Abierta") or 1
    cr = CashRegister(
        cash_id=cash_id,
        branch_id=branch_id,
        id_usuario=int(user_id),
        status_id=st_abierto_id,
        initial_amount=float(opening),
        opened_at=func.current_timestamp(),
        total_cash=0.0, total_sales=0.0, difference=0.0
    )
    db.session.add(cr)
    db.session.commit()
    return jsonify({"msg": "Caja abierta", "cash_register_id": cr.id}), 201



# ---------------------- cerrar (cajero) ----------------------

@bp.post("/close")
@jwt_required()
def close_register():
    """
    Cierre de CAJERO (solo si la caja está ABIERTO):
    - Calcula ventas por método (desde CashRegisterMovement tipo 'VENTA')
    - Calcula otros movimientos en efectivo (Ingresos/Egresos ≠ 'VENTA')
    - Esperado en caja = initial_amount + cash_sales + cash_ingresos_otros - cash_egresos_otros
    - difference = closing_amount - esperado_en_caja
    - Deja estado en PENDIENTE para auditoría
    Body:
    {
      "cash_register_id": 4,
      "closing_amount": 105000,           // alias: total_cash
      "note": "cierre fin de turno"
    }
    """
    from sqlalchemy import and_
    data = request.get_json() or {}
    cr_id = data.get("cash_register_id")
    if not cr_id:
        return jsonify({"msg": "cash_register_id requerido"}), 400

    cr = CashRegister.query.get(cr_id)
    if not cr:
        return jsonify({"msg": "CashRegister no encontrado"}), 404

    # --- Estados ---
    st_abierto = _status_id_ci("ABIERTO") or _status_id_ci("Abierta")
    st_pend    = (_status_id_ci("PENDIENTE")
                  or _status_id_ci("EN_REVISION")
                  or _status_id_ci("EN REVISIÓN"))
    if not st_abierto or not st_pend:
        return jsonify({"msg": "Estados 'ABIERTO'/'PENDIENTE' no configurados."}), 500

    # 🔒 Solo cerrar si está ABIERTO (evita re-cierres sobre PENDIENTE/CERRADO)
    if cr.status_id != st_abierto:
        return jsonify({
            "msg": "Solo se puede cerrar una caja en estado ABIERTO.",
            "estado_actual": getattr(cr.status, "status_name", None)
        }), 409

    # --- Monto declarado por el cajero ---
    raw_closing = data.get("closing_amount", data.get("total_cash"))
    if raw_closing is None:
        return jsonify({"msg": "closing_amount (o total_cash) requerido"}), 400
    try:
        closing_cash = float(Decimal(str(raw_closing)))
    except Exception:
        return jsonify({"msg": "closing_amount inválido"}), 400

    # --- Buscar tipo de movimiento 'VENTA' ---
    venta_tipo = MovementType.query.filter(func.lower(MovementType.name) == "venta").first()
    if not venta_tipo:
        return jsonify({"msg": "Tipo de movimiento 'VENTA' no configurado."}), 500

    # --- Traer todos los movimientos de esta caja (desde apertura) ---
    # Usamos opened_at como inicio del turno
    movimientos = CashRegisterMovement.query.filter(
        CashRegisterMovement.cash_register_id == cr.id
    ).all()

    # Mapear id -> nombre de método de pago
    all_methods = {pm.id: (pm.name or "").strip() for pm in PaymentMethod.query.all()}

    # Acumuladores
    sales_total_all_methods = 0.0
    cash_sales = card_sales = qr_sales = transfer_sales = credit_sales = other_sales = 0.0
    cash_ingresos_otros = cash_egresos_otros = 0.0

    # Preparamos un dict de MovementType id -> nombre para clasificar no-venta
    mt_names = {mt.id: (mt.name or "").strip().lower() for mt in MovementType.query.all()}

    for mov in movimientos:
        metodo = all_methods.get(getattr(mov, "payment_method_id", None), "")
        tipo_pago = clasificar_forma_pago(metodo)
        monto = float(mov.amount or 0)
        mt_name = mt_names.get(getattr(mov, "movement_type_id", None), "")

        if getattr(mov, "movement_type_id", None) == venta_tipo.id:
            # Es una venta
            sales_total_all_methods += monto
            if tipo_pago == "efectivo":   cash_sales += monto
            elif tipo_pago == "tarjeta":  card_sales += monto
            elif tipo_pago == "qr":       qr_sales += monto
            elif tipo_pago == "transferencia": transfer_sales += monto
            elif tipo_pago == "credito":  credit_sales += monto
            else:                         other_sales += monto
        else:
            # Otros movimientos en efectivo (ingresos/egresos que afectan la caja física)
            if tipo_pago == "efectivo":
                # criterios simples por nombre del MovementType
                if any(k in mt_name for k in ("egreso", "retiro", "salida")):
                    cash_egresos_otros += monto
                elif any(k in mt_name for k in ("ingreso", "entrada", "deposito", "depósito")):
                    cash_ingresos_otros += monto
                # si es otro nombre, no afecta (o podrías decidir sumarlo a ingresos)

    # --- Efectivo esperado en caja ---
    initial = float(cr.initial_amount or 0)
    expected_cash = initial + cash_sales + cash_ingresos_otros - cash_egresos_otros

    # --- Diferencia: lo declarado vs lo esperado en EFECTIVO ---
    difference = closing_cash - expected_cash

    # --- Persistir: total_sales = ventas totales (todos los métodos) ---
    cr.total_cash = closing_cash
    cr.total_sales = sales_total_all_methods
    cr.difference = difference
    cr.closed_at  = func.current_timestamp()
    cr.observacion_cierre = (data.get("note") or "").strip()
    cr.status_id  = st_pend  # queda PENDIENTE para auditoría

    db.session.commit()

    return jsonify({
        "msg": "Caja cerrada y enviada a revisión",
        "cash_register_id": cr.id,
        "resumen": {
            "initial_amount": initial,
            "sales": {
                "all_methods_total": sales_total_all_methods,
                "cash": cash_sales,
                "card": card_sales,
                "qr": qr_sales,
                "transfer": transfer_sales,
                "credit": credit_sales,
                "other": other_sales
            },
            "other_cash_movements": {
                "ingresos": cash_ingresos_otros,
                "egresos": cash_egresos_otros
            },
            "expected_cash_in_drawer": expected_cash,
            "declared_cash": closing_cash,
            "difference": difference
        }
    }), 200


# ---------------------- registrar movimiento manual ----------------------

@bp.post("/movements")
@jwt_required()
def add_movement():
    """
    Body:
    {
      "cash_register_id": 10,
      "movement_type": "Ingreso" | "Egreso",
      "payment_method_id": 1,
      "amount": 50000,
      "description": "Retiro chico"
    }
    """
    data = request.get_json() or {}
    cr_id   = data.get("cash_register_id")
    kind    = (data.get("movement_type") or "").strip() or "Ingreso"
    pm_id   = data.get("payment_method_id") or 1
    amount  = Decimal(str(data.get("amount", 0) or 0))

    cr = CashRegister.query.get(cr_id)
    if not cr: return jsonify({"msg": "CashRegister no encontrado"}), 404
    if not PaymentMethod.query.get(pm_id): return jsonify({"msg": "payment_method_id inválido"}), 400

    mt = MovementType.query.filter(func.lower(MovementType.name) == kind.lower()).first()
    mt_id = mt.id if mt else 1

    mov = CashRegisterMovement(
        cash_register_id=cr.id,
        payment_method_id=pm_id,
        movement_type_id=mt_id,
        amount=float(amount),
        description=data.get("description")
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({"msg": "Movimiento registrado", "movement_id": mov.id}), 201


# ---------------------- historial ----------------------

@bp.get("/history")
@jwt_required()
def get_cash_registers_history():
    """
    GET /api/cash-register/history?user_id=..&status_name=Abierto&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """
    q = (
        db.session.query(
            CashRegister,
            Usuario.nombre.label("user_name"),
            Usuario.nombre_usuario.label("username"),
            Cash.description.label("cash_name"),
            Branch.name.label("branch_name"),
            CashRegisterStatus.status_name.label("status")
        )
        .join(Usuario, CashRegister.id_usuario == Usuario.id_usuario)
        .join(Cash,   CashRegister.cash_id   == Cash.id)
        .join(Branch, CashRegister.branch_id == Branch.id)
        .join(CashRegisterStatus, CashRegister.status_id == CashRegisterStatus.id)
    )

    # Filtros
    user_id_filter     = request.args.get('user_id', type=int)
    status_name_filter = request.args.get('status_name')
    start_date_str     = request.args.get('start_date')
    end_date_str       = request.args.get('end_date')

    if user_id_filter:
        q = q.filter(CashRegister.id_usuario == user_id_filter)
    if status_name_filter:
        q = q.filter(func.lower(CashRegisterStatus.status_name) == status_name_filter.lower())
    if start_date_str:
        try:
            q = q.filter(CashRegister.opened_at >= datetime.strptime(start_date_str, '%Y-%m-%d'))
        except ValueError:
            return jsonify({"message": "Formato de fecha de inicio inválido. Use YYYY-MM-DD."}), 400
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(CashRegister.opened_at < end_dt)
        except ValueError:
            return jsonify({"message": "Formato de fecha de fin inválido. Use YYYY-MM-DD."}), 400

    q = q.order_by(CashRegister.opened_at.desc())

    all_methods = {pm.id: (pm.name or "").strip() for pm in PaymentMethod.query.all()}
    venta_tipo = MovementType.query.filter(func.lower(MovementType.name) == "venta").first()
    if not venta_tipo:
        return jsonify({"message": "Tipo de movimiento 'VENTA' no configurado."}), 500

    history = []
    for cr, user_name, username_alias, cash_name, branch_name, status in q.all():
        total_cash = total_card = total_credit = 0.0
        total_transfer = total_qr = total_other = 0.0

        movimientos = CashRegisterMovement.query.filter_by(
            cash_register_id=cr.id,
            movement_type_id=venta_tipo.id
        ).all()

        for mov in movimientos:
            metodo = all_methods.get(getattr(mov, "payment_method_id", None), "")
            tipo = clasificar_forma_pago(metodo)
            monto = float(mov.amount or 0)
            if tipo == "efectivo": total_cash += monto
            elif tipo == "tarjeta": total_card += monto
            elif tipo == "credito": total_credit += monto
            elif tipo == "transferencia": total_transfer += monto
            elif tipo == "qr": total_qr += monto
            else: total_other += monto

        history.append({
            "id": cr.id,
            "user_id": cr.id_usuario,
            "user_name": user_name,
            "username": username_alias,
            "cash_id": cr.cash_id,
            "cash_name": cash_name,
            "branch_id": cr.branch_id,
            "branch_name": branch_name,
            "initial_amount": float(cr.initial_amount or 0),
            "status": status,
            "opened_at": cr.opened_at.isoformat() if cr.opened_at else None,
            "closed_at": cr.closed_at.isoformat() if cr.closed_at else None,
            "total_cash_declared": float(cr.total_cash) if cr.total_cash is not None else None,
            "total_sales_system": float(cr.total_sales) if cr.total_sales is not None else None,
            "difference": float(cr.difference) if cr.difference is not None else None,
            "total_cash": total_cash,
            "total_card": total_card,
            "total_credit": total_credit,
            "total_transfer": total_transfer,
            "total_qr": total_qr,
            "total_other": total_other,
            "observacion_cierre": cr.observacion_cierre,
            "fecha_confirmacion": cr.fecha_confirmacion.isoformat() if cr.fecha_confirmacion else None,
        })

    return jsonify(history), 200


# Alias legacy
@bp.get("/registers/history")
@jwt_required()
def get_cash_registers_history_alias():
    return get_cash_registers_history()


# ---------------------- confirmar (admin) ----------------------

@bp.post("/<int:cash_id>/confirm")
@bp.post("/registers/<int:cash_id>/confirmar")
@jwt_required()
def confirmar_cierre_caja(cash_id):
    user_id = get_jwt_identity()
    roles = (get_jwt() or {}).get("roles", []) or []

    caja = CashRegister.query.get(cash_id)
    if not caja: return jsonify({"message": "Caja no encontrada."}), 404

    if not caja.closed_at:
        return jsonify({"message": "El cajero aún no ha cerrado esta caja. No se puede confirmar hasta que lo haga."}), 400

    # Permitir confirmar únicamente si está Cerrada o Pendiente (según catálogo)
    estado_actual = (caja.status.status_name or "").strip().lower() if getattr(caja, "status", None) else ""
    if estado_actual not in {"cerrada", "cerrado", "pendiente", "en revisión", "en revision"}:
        return jsonify({"message": f"Estado actual '{estado_actual}'. Solo se pueden confirmar cajas cerradas o pendientes."}), 400

    if "Admin" not in roles: return jsonify({"message": "No autorizado para confirmar cierre."}), 403
    if getattr(caja, "fecha_confirmacion", None): return jsonify({"message": "Esta caja ya fue confirmada."}), 400

    data = request.get_json() or {}
    observacion = (data.get("observacion_cierre") or "").strip()

    if abs(caja.difference or 0) >= 30000 and not observacion:
        return jsonify({"message": "Diferencias ≥ Gs. 30.000 requieren observación"}), 400

    caja.confirmado_por_usuario_id = int(user_id)
    caja.fecha_confirmacion = datetime.utcnow()
    caja.observacion_cierre = observacion

    # Dejar estado final 'CERRADO' (o 'AUDITADO' si existe en tu catálogo)
    st_cerrado_id = _status_id_ci("CERRADO") or _status_id_ci("Cerrada")
    if st_cerrado_id:
        caja.status_id = st_cerrado_id

    db.session.commit()
    return jsonify({"message": "Cierre confirmado correctamente", "cash_register_id": caja.id}), 200


# ---------------------- ENDPOINT REQUERIDO POR EL FRONTEND DE DEVOLUCIONES ----------------------

@bp.get("/open-cash")
@jwt_required()
def check_open_cash():
    """
    Verifica si el usuario actual tiene una caja abierta (status 'ABIERTO').
    - Si la encuentra, devuelve 200 con el ID de la caja y sucursal.
    - Si no la encuentra, devuelve 404.
    """
    user_id = get_jwt_identity()

        # --- DEBUG SEARCH ---
    print(f"--- Busqueda de caja abierta---")
    print(f"Usuario_logueado: {user_id!r}")
    print(f"--------------------")
    
    # Reutilizamos el helper que ya definió en su código
    st_abierta_id = _status_id_ci("ABIERTO")
    if not st_abierta_id:
        # Error de configuración si el estado 'ABIERTO' no está en la DB
        return jsonify({"message": "Error de configuración: Estado 'ABIERTO' no encontrado."}), 500

    # Buscamos la caja abierta para este usuario
    open_cash_register = db.session.execute(
        db.select(CashRegister)
        .filter(
            # Utilizamos el campo correcto de su modelo: 'id_usuario'
            CashRegister.id_usuario == int(user_id),
            CashRegister.status_id == st_abierta_id
        )
        .order_by(CashRegister.opened_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if open_cash_register:
        # Caja abierta encontrada (200 OK)
        return jsonify({
            "message": "Caja abierta encontrada",
            "cash_register_id": open_cash_register.id,
            "branch_id": open_cash_register.branch_id
        }), 200
    else:
        # No hay caja abierta para este usuario (404 Not Found)
        return jsonify({"error": "No se encontró una caja abierta para este usuario."}), 404