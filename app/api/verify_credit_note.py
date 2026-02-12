import sys
import os
from datetime import date

# Asegurar que el path del proyecto está en sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.catalog import (
    InvoiceType, InvoiceNumber, Branch, Cash, CashRegister, 
    Sale, SaleDetail, Producto, Customer, Usuario, Invoice, SalesStatus, PaymentMethod
)

app = create_app()

def verify():
    with app.app_context():
        print("Iniciando verificación...")
        
        # 1. Asegurar InvoiceType "Nota de Crédito"
        nc_type = InvoiceType.query.filter(InvoiceType.name.ilike('%Nota de Cr%dito%')).first()
        if not nc_type:
            print("Creando Tipo de Factura 'Nota de Crédito'...")
            nc_type = InvoiceType(name="Nota de Crédito", description="Para devoluciones")
            db.session.add(nc_type)
            db.session.commit()
        print(f"InvoiceType: {nc_type.name} (ID: {nc_type.id})")

        # 2. Obtener datos base (Sucursal, Caja, Usuario)
        branch = Branch.query.first()
        cash = Cash.query.first()
        user = Usuario.query.first()
        
        if not branch or not cash or not user:
            print("Error: Faltan datos base (Branch, Cash o User).")
            return

        # 3. Asegurar InvoiceNumber para Nota de Crédito
        inv_num = InvoiceNumber.query.filter_by(
            branch_id=branch.id,
            cash_id=cash.id,
            invoice_type_id=nc_type.id,
            status='ACTIVE'
        ).first()

        if not inv_num:
            print("Creando Numeración para Nota de Crédito...")
            inv_num = InvoiceNumber(
                branch_id=branch.id,
                cash_id=cash.id,
                invoice_type_id=nc_type.id,
                timbrado="12345678",
                establishment=1,
                point_of_issue=1,
                start_number=1,
                end_number=1000,
                current_number=0,
                valid_from=date.today(),
                valid_until=date(2030, 12, 31),
                status='ACTIVE'
            )
            db.session.add(inv_num)
            db.session.commit()
        print(f"InvoiceNumber ID: {inv_num.id} - Actual: {inv_num.current_number}")

        # 4. Crear una Venta y Factura de prueba
        print("Creando Venta y Factura de prueba...")
        customer = Customer.query.first()
        product = Producto.query.first()
        status = SalesStatus.query.first()
        pm = PaymentMethod.query.first()
        
        if not product:
            print("Error: No hay productos.")
            return

        sale = Sale(
            customer_id=customer.id if customer else None,
            id_usuario=user.id_usuario,
            cash_id=cash.id,
            branch_id=branch.id,
            total=100,
            status_id=status.id if status else None
        )
        db.session.add(sale)
        db.session.flush()

        detail = SaleDetail(
            sale_id=sale.id,
            product_id=product.id,
            quantity=1,
            price=100,
            subtotal=100,
            unit_type="UNIDAD"
        )
        db.session.add(detail)
        
        # Factura dummy
        invoice = Invoice(
            sale_id=sale.id,
            formatted_number=f"001-001-{sale.id}", # Dummy number
            invoice_type_id=1, # Asumiendo 1 es Factura
            payment_method_id=pm.id if pm else 1,
            customer_id=customer.id if customer else 1,
            id_usuario=user.id_usuario,
            timbrado="11111111",
            total=100,
            status_id=status.id if status else None
        )
        db.session.add(invoice)
        db.session.commit()
        print(f"Venta creada ID: {sale.id}")

        # 5. Simular Petición de Devolución (Llamando a la función del controlador o simulando request)
        # Para simplificar, usaremos test_client
        client = app.test_client()
        
        # Necesitamos token JWT simulado o saltar auth. 
        # Como es complicado simular JWT aquí sin login, vamos a intentar invocar la lógica directamente o usar un hack.
        # Mejor: vamos a usar `app.test_request_context` y mockear `get_jwt_identity`.
        
        from flask_jwt_extended import create_access_token
        
        with app.test_request_context():
            token = create_access_token(identity=str(user.id_usuario))
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Necesitamos un CashRegister abierto
            cr = CashRegister.query.filter_by(id_usuario=user.id_usuario, closed_at=None).first()
            if not cr:
                print("Abriendo caja temporal...")
                cr = CashRegister(
                    cash_id=cash.id,
                    branch_id=branch.id,
                    id_usuario=user.id_usuario,
                    initial_amount=0,
                    status_id=1 # Asumiendo 1 es Abierto
                )
                db.session.add(cr)
                db.session.commit()
            
            payload = {
                "items": [
                    {
                        "sale_detail_id": detail.id,
                        "product_id": product.id,
                        "quantity_to_return": 1,
                        "unit_price": 100
                    }
                ],
                "return_type": "DEVOLUCION",
                "total_refund": 100,
                "refund_payment_method": "NOTA_CREDITO",
                "cash_register_id": cr.id,
                "branch_id": branch.id,
                "notes": "Prueba script verificación"
            }
            
            print("Enviando petición POST...")
            response = client.post(f"/api/sales_returns/{sale.id}", json=payload, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json}")
            
            if response.status_code == 201:
                print("✅ ÉXITO: Nota de Crédito creada.")
            else:
                print("❌ FALLO: No se creó la Nota de Crédito.")

if __name__ == "__main__":
    verify()
