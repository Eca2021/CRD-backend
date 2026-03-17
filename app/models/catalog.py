from app.extensions import db
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean,
    ForeignKey, Date, DateTime, TIMESTAMP, func, 
)
from sqlalchemy.orm import relationship, backref

class Estado(db.Model):
    __tablename__ = 't_status'
    id = Column(Integer, primary_key=True)
    value = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'description': self.description}

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='ACTIVO')
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())
    updated_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    roles = db.relationship('UsuarioRol', backref='usuario', lazy=True, cascade="all, delete-orphan")
    historial_accesos = db.relationship('HistorialAcceso', backref='usuario', lazy=True)

    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'nombre_usuario': self.nombre_usuario,
            'nombre': self.nombre,
            'email': self.email,
            'estado': self.estado,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': [ur.rol.to_dict_simple() for ur in self.roles]
        }

class HistorialAcceso(db.Model):
    __tablename__ = 'historial_accesos'
    id_acceso = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario', ondelete='SET NULL'), nullable=True)
    username_intentado = Column(String(50))
    fecha_hora = Column(DateTime, server_default=func.current_timestamp(), index=True)
    evento = Column(String(20))
    ip_cliente = Column(String(45))
    user_agent = Column(Text)
    motivo_fallo = Column(Text)

    def to_dict(self):
        return {
            'id_acceso': self.id_acceso,
            'id_usuario': self.id_usuario,
            'username_intentado': self.username_intentado,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None,
            'evento': self.evento,
            'ip_cliente': self.ip_cliente,
            'user_agent': self.user_agent,
            'motivo_fallo': self.motivo_fallo
        }

class Rol(db.Model):
    __tablename__ = 'rol'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)

    permisos_asociados = db.relationship('RolPermiso', backref='rol', lazy=True, cascade="all, delete-orphan")

    @property
    def permisos(self):
        return [rp.permiso for rp in self.permisos_asociados]

    def to_dict(self):
        return {
            'id_rol': self.id_rol,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'permisos': [perm.to_dict_simple() for perm in self.permisos]
        }

    def to_dict_simple(self):
        return {
            'id_rol': self.id_rol,
            'nombre': self.nombre
        }

class Permiso(db.Model):
    __tablename__ = 'permiso'
    id_permiso = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)

    def to_dict(self):
        return {
            'id_permiso': self.id_permiso,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }

    def to_dict_simple(self):
        return {'id_permiso': self.id_permiso, 'nombre': self.nombre}

class UsuarioRol(db.Model):
    __tablename__ = 'usuario_rol'
    id_usuario_rol = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())

    rol = db.relationship('Rol', backref='usuario_roles_backref', lazy=True)

class RolPermiso(db.Model):
    __tablename__ = 'rol_permiso'
    id_permiso = db.Column(db.Integer, db.ForeignKey('permiso.id_permiso', ondelete='CASCADE'), primary_key=True)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol', ondelete='CASCADE'), primary_key=True)

    permiso = db.relationship('Permiso', backref='rol_permisos', lazy=True)

class CompanySetting(db.Model):
    __tablename__ = 't_company_settings'
    id         = Column(Integer, primary_key=True)
    name       = Column(String(255), nullable=False)
    ruc        = Column(String(50), unique=True, nullable=False)
    address    = Column(Text)
    phone      = Column(String(50))
    email      = Column(String(100))
    logo_url   = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ruc': self.ruc,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id_cliente = db.Column(db.Integer, primary_key=True)
    documento = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(50))
    direccion = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id_cliente': self.id_cliente,
            'documento': self.documento,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'telefono': self.telefono,
            'direccion': self.direccion,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class TasaInteres(db.Model):
    __tablename__ = 'tasas_interes'
    id_tasa = db.Column(db.Integer, primary_key=True)
    nombre_tasa = db.Column(db.String(50))
    porcentaje = db.Column(db.Numeric, nullable=False)
    descripcion = db.Column(db.Text)

    def to_dict(self):
        return {
            'id_tasa': self.id_tasa,
            'nombre_tasa': self.nombre_tasa,
            'porcentaje': float(self.porcentaje),
            'descripcion': self.descripcion
        }

class ReglaCredito(db.Model):
    __tablename__ = 'reglas_credito'
    id_regla = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    porcentaje = db.Column(db.Numeric, nullable=False)
    dias_intervalo = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id_regla': self.id_regla,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'porcentaje': float(self.porcentaje),
            'dias_intervalo': self.dias_intervalo,
            'activo': self.activo
        }

class Credito(db.Model):
    __tablename__ = 'creditos'
    id_credito = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    id_regla = db.Column(db.Integer, db.ForeignKey('reglas_credito.id_regla'), nullable=False)
    monto_solicitado = db.Column(db.Numeric, nullable=False)
    monto_total_a_pagar = db.Column(db.Numeric, nullable=False)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    fecha_desembolso = db.Column(db.Date, default=db.func.current_date())
    estado = db.Column(db.String(20), default='PENDIENTE')

    cliente = db.relationship('Cliente', backref='creditos')
    usuario = db.relationship('Usuario', backref='creditos_otorgados')
    regla = db.relationship('ReglaCredito', backref='creditos')
    detalles = db.relationship('DetalleCredito', backref='credito', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id_credito': self.id_credito,
            'id_cliente': self.id_cliente,
            'cliente_nombre': f"{self.cliente.nombre} {self.cliente.apellido}" if self.cliente else None,
            'id_usuario': self.id_usuario,
            'usuario_nombre': self.usuario.nombre_usuario if self.usuario else None,
            'id_regla': self.id_regla,
            'regla_nombre': self.regla.nombre if self.regla else None,
            'regla_porcentaje': float(self.regla.porcentaje) if self.regla else 0,
            'monto_solicitado': float(self.monto_solicitado),
            'monto_total_a_pagar': float(self.monto_total_a_pagar),
            'cantidad_cuotas': self.cantidad_cuotas,
            'fecha_desembolso': self.fecha_desembolso.isoformat() if self.fecha_desembolso else None,
            'estado': self.estado,
            'detalles': [d.to_dict() for d in self.detalles]
        }

class DetalleCredito(db.Model):
    __tablename__ = 'detalles_credito'
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_credito = db.Column(db.Integer, db.ForeignKey('creditos.id_credito'), nullable=False)
    numero_cuota = db.Column(db.Integer, nullable=False)
    monto_cuota = db.Column(db.Numeric, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    monto_pagado = db.Column(db.Numeric, default=0)
    estado_cuota = db.Column(db.String(20), default='PENDIENTE')
    capital_cuota = db.Column(db.Numeric, default=0)
    interes_cuota = db.Column(db.Numeric, default=0)
    cuota_total = db.Column(db.Numeric, default=0)

    def to_dict(self):
        return {
            'id_detalle': self.id_detalle,
            'id_credito': self.id_credito,
            'numero_cuota': self.numero_cuota,
            'monto_cuota': float(self.monto_cuota),
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'monto_pagado': float(self.monto_pagado) if self.monto_pagado else 0,
            'estado_cuota': self.estado_cuota,
            'capital_cuota': float(self.capital_cuota) if self.capital_cuota else 0,
            'interes_cuota': float(self.interes_cuota) if self.interes_cuota else 0,
            'cuota_total': float(self.cuota_total) if self.cuota_total else 0,
            'pagos': [p.to_dict() for p in self.pagos if p.estado == 'ACTIVO']
        }

class FormaPago(db.Model):
    __tablename__ = 'formas_pago'
    id_forma_pago = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id_forma_pago': self.id_forma_pago,
            'nombre': self.nombre
        }

class Pago(db.Model):
    __tablename__ = 'pagos'
    id_pago = db.Column(db.Integer, primary_key=True)
    id_detalle_credito = db.Column(db.Integer, db.ForeignKey('detalles_credito.id_detalle'), nullable=False)
    id_forma_pago = db.Column(db.Integer, db.ForeignKey('formas_pago.id_forma_pago'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    monto_pagado = db.Column(db.Numeric, nullable=False)
    fecha_pago = db.Column(db.DateTime, default=db.func.current_timestamp())
    comprobante_nro = db.Column(db.String(50))
    estado = db.Column(db.String(20), default='ACTIVO')

    detalle = db.relationship('DetalleCredito', backref='pagos')
    forma_pago = db.relationship('FormaPago', backref='pagos')
    usuario = db.relationship('Usuario', backref='pagos')

    def to_dict(self):
        return {
            'id_pago': self.id_pago,
            'id_detalle_credito': self.id_detalle_credito,
            'id_forma_pago': self.id_forma_pago,
            'forma_pago': self.forma_pago.nombre if self.forma_pago else None,
            'id_usuario': self.id_usuario,
            'usuario_nombre': self.usuario.nombre_usuario if self.usuario else None,
            'monto_pagado': float(self.monto_pagado),
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'comprobante_nro': self.comprobante_nro,
            'estado': self.estado
        }

class PagoAudit(db.Model):
    __tablename__ = 'historial_pagos_audit'
    id_audit = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(db.Integer)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    accion = db.Column(db.String(20))
    fecha_accion = db.Column(db.DateTime, default=db.func.current_timestamp())
    monto_registrado = db.Column(db.Numeric(15, 2))
    id_detalle_credito = db.Column(db.Integer)
    estado_pago_momento = db.Column(db.String(10))
    direccion_ip = db.Column(db.String(45))
    observacion = db.Column(db.Text)

    usuario = db.relationship('Usuario', backref='auditoria_pagos')

    def to_dict(self):
        return {
            'id_audit': self.id_audit,
            'id_pago': self.id_pago,
            'id_usuario': self.id_usuario,
            'usuario_nombre': self.usuario.nombre_usuario if self.usuario else None,
            'accion': self.accion,
            'fecha_accion': self.fecha_accion.isoformat() if self.fecha_accion else None,
            'monto_registrado': float(self.monto_registrado) if self.monto_registrado else None,
            'id_detalle_credito': self.id_detalle_credito,
            'estado_pago_momento': self.estado_pago_momento,
            'direccion_ip': self.direccion_ip,
            'observacion': self.observacion
        }

class AsientoContable(db.Model):
    __tablename__ = 'asientos_contables'
    id_asiento = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=db.func.current_timestamp())
    glosa = db.Column(db.Text)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))

    movimientos = db.relationship('MovimientoContable', backref='asiento', cascade="all, delete-orphan")
    usuario = db.relationship('Usuario', backref='asientos')

    def to_dict(self):
        return {
            'id_asiento': self.id_asiento,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'glosa': self.glosa,
            'id_usuario': self.id_usuario,
            'movimientos': [m.to_dict() for m in self.movimientos]
        }

class MovimientoContable(db.Model):
    __tablename__ = 'movimientos_contables'
    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_asiento = db.Column(db.Integer, db.ForeignKey('asientos_contables.id_asiento'), nullable=False)
    cuenta = db.Column(db.String(100), nullable=False)
    debe = db.Column(db.Numeric, default=0)
    haber = db.Column(db.Numeric, default=0)

    def to_dict(self):
        return {
            'id_movimiento': self.id_movimiento,
            'cuenta': self.cuenta,
            'debe': float(self.debe),
            'haber': float(self.haber)
        }

class MovimientoAdmin(db.Model):
    __tablename__ = 'movimientos_admin'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    monto = db.Column(db.Numeric(15, 2), nullable=False)
    descripcion = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=db.func.current_timestamp())
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))

    usuario = db.relationship('Usuario', backref='movimientos_admin')

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'monto': float(self.monto),
            'descripcion': self.descripcion,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'id_usuario': self.id_usuario,
            'usuario_nombre': self.usuario.nombre_usuario if self.usuario else None
        }
