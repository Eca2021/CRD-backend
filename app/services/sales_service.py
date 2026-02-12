# ❌ si estaba relativo:
# from ..repositories.customer_repo import CustomerRepo

# ✅ mejor absoluto:
from app.repositories.customer_repo import CustomerRepo

class CustomerService:
    @staticmethod
    def list_customers():
        return CustomerRepo.get_all()

    @staticmethod
    def get_customer(cid: int):
        return CustomerRepo.get_by_id(cid)

    @staticmethod
    def create_customer(**data):
        return CustomerRepo.create(**data)

    @staticmethod
    def update_customer(cid: int, **data):
        return CustomerRepo.update(cid, **data)

    @staticmethod
    def delete_customer(cid: int):
        return CustomerRepo.delete(cid)
