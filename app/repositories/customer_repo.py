# ❌ estaba así
# from ..models.customer import Customer
# from ..extensions import db

# ✅ dejalo así
from app.models.catalog import Customer
from app.extensions import db

class CustomerRepo:
    @staticmethod
    def get_all():
        return Customer.query.all()

    @staticmethod
    def get_by_id(cid: int):
        return Customer.query.get(cid)

    @staticmethod
    def create(**data):
        obj = Customer(**data)
        db.session.add(obj)
        db.session.commit()
        return obj

    @staticmethod
    def update(cid: int, **data):
        obj = Customer.query.get(cid)
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.session.commit()
        return obj

    @staticmethod
    def delete(cid: int):
        obj = Customer.query.get(cid)
        if not obj:
            return False
        db.session.delete(obj)
        db.session.commit()
        return True
