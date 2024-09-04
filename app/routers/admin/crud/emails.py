from app.libs.utils import generate_id
from app.models import EmailModel
from app.routers.admin.crud.admin_users import create_password
from sqlalchemy.orm import Session

from app.routers.admin.schemas import EmailCreateRequest


def add_email(request: EmailCreateRequest, db: Session, admin_user_id: str):
    
    hashed_password = create_password(request.password)
    
    new_email = EmailModel(
        id=generate_id(),
        name=request.name,
        email=request.email,
        password=hashed_password,
        phone=request.phone,
        admin_user_id=admin_user_id,
    )
    
    db.add(new_email)
    db.commit()
    db.refresh(new_email)
    
    return new_email