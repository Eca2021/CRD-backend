# catalog.py (arriba del todo)
from app.extensions import db
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean,
    ForeignKey, Date, DateTime, TIMESTAMP, func, 
)
from sqlalchemy.orm import relationship, backref

# ==========================================================
# Definición de Modelos (TODOS MOVIDOS AQUÍ
# Esto asegura que se definan una sola vez al cargar el módulo.
# ==========================================================



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


    # Relación uno a muchos con UsuarioRol (un usuario puede tener muchos roles)
    roles = db.relationship('UsuarioRol', backref='usuario', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'nombre_usuario': self.nombre_usuario,
            'nombre': self.nombre,
            'email': self.email,
            'estado': self.estado,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': [ur.rol.to_dict_simple() for ur in self.roles] # Lista de roles asociados (nombre y id)
        }

class Rol(db.Model):
    __tablename__ = 'rol'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)

    # Relación muchos a muchos con Permiso a través de RolPermiso
    permisos_asociados = db.relationship('RolPermiso', backref='rol', lazy=True, cascade="all, delete-orphan")

    @property
    def permisos(self):
        """Permite acceder directamente a la lista de permisos como rol.permisos"""
        return [rp.permiso for rp in self.permisos_asociados]

    def to_dict(self):
        # Incluye la lista de permisos asociados al rol
        return {
            'id_rol': self.id_rol,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'permisos': [perm.to_dict_simple() for perm in self.permisos]  # Usamos la nueva propiedad aquí
        }

    def to_dict_simple(self):
        # Versión simplificada para cuando se lista dentro de otro objeto (ej. Usuario)
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
        # Versión simplificada para listar permisos dentro de un rol
        return {'id_permiso': self.id_permiso, 'nombre': self.nombre}

class UsuarioRol(db.Model):
    __tablename__ = 'usuario_rol'
    id_usuario_rol = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())

    # RELACIÓN CLAVE: Permite acceder al objeto Rol desde una instancia de UsuarioRol
    rol = db.relationship('Rol', backref='usuario_roles_backref', lazy=True) # backref 'usuario_roles_backref' para evitar conflictos con 'usuario_roles' si ya existe.

class RolPermiso(db.Model):
    __tablename__ = 'rol_permiso'
    id_permiso = db.Column(db.Integer, db.ForeignKey('permiso.id_permiso', ondelete='CASCADE'), primary_key=True)
    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id_rol', ondelete='CASCADE'), primary_key=True)
    # created_at no existe en la definición SQL dada por el usuario para rol_permiso, pero lo dejo si no molesta, o lo quito.
    # El usuario dijo "Relación entre Roles y Permisos... PRIMARY KEY (id_permiso, id_rol)". 
    # No mencionó created_at. Lo quitaré para ser fiel al esquema.

    # Relación de vuelta para acceder al Permiso desde RolPermiso
    permiso = db.relationship('Permiso', backref='rol_permisos', lazy=True)

# ----------------------------------------------------
#   C R U D   para  T I P O S   D E   D O C U M E N T O S
# ----------------------------------------------------



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
    documento = db.Column(db.String(20), nullable=False) # No unique constraint in schema provided? User said "Nulable: NO". Usually document is unique, but I'll stick to 'nullable=False' and maybe keep 'unique=True' for logic if reasonable, or better follow schema strictly? Schema output doesn't show unique constraint explicitly in that text format, but usually it is. I will keep unique=False in model definition if not specified, but usually it should be. The user said "guide yourself by that structure". The structure shows columns. I will keep unique=True for document because it makes sense for business logic, but strict schema might not have it. I'll add `unique=True` as a safety net unless it fails.
    # Actually, the user did not show constraints like UNIQUE in the text table.
    # I will modify to match columns.
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

class Credito(db.Model):
    __tablename__ = 'creditos'
    id_credito = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    id_tasa = db.Column(db.Integer, db.ForeignKey('tasas_interes.id_tasa'), nullable=False)
    monto_solicitado = db.Column(db.Numeric, nullable=False)
    monto_total_a_pagar = db.Column(db.Numeric, nullable=False)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    fecha_desembolso = db.Column(db.Date, default=db.func.current_date())
    estado = db.Column(db.String(20), default='PENDIENTE')

    cliente = db.relationship('Cliente', backref='creditos')
    usuario = db.relationship('Usuario', backref='creditos_otorgados')
    tasa = db.relationship('TasaInteres', backref='creditos')
    detalles = db.relationship('DetalleCredito', backref='credito', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id_credito': self.id_credito,
            'id_cliente': self.id_cliente,
            'cliente_nombre': f"{self.cliente.nombre} {self.cliente.apellido}" if self.cliente else None,
            'id_usuario': self.id_usuario,
            'usuario_nombre': self.usuario.nombre_usuario if self.usuario else None,
            'id_tasa': self.id_tasa,
            'tasa_nombre': self.tasa.nombre_tasa if self.tasa else None,
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
            'cuota_total': float(self.cuota_total) if self.cuota_total else 0
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
    monto_pagado = db.Column(db.Numeric, nullable=False)
    fecha_pago = db.Column(db.DateTime, default=db.func.current_timestamp())
    comprobante_nro = db.Column(db.String(50))

    detalle = db.relationship('DetalleCredito', backref='pagos')
    forma_pago = db.relationship('FormaPago', backref='pagos')

    def to_dict(self):
        return {
            'id_pago': self.id_pago,
            'id_detalle_credito': self.id_detalle_credito,
            'id_forma_pago': self.id_forma_pago,
            'forma_pago': self.forma_pago.nombre if self.forma_pago else None,
            'monto_pagado': float(self.monto_pagado),
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'comprobante_nro': self.comprobante_nro
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
