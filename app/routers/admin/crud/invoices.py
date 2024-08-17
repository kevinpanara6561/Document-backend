from app.libs.s3_service import upload_file_to_s3
from app.libs.utils import generate_id
from app.models import InvoiceModel
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

load_dotenv()

bucket_name = os.getenv("AWS_BUCKET")

def create_invoice(db: Session, file_path: str, file_type: str, admin_user_id: str):
    invoice = InvoiceModel(
        id=generate_id(),
        file_path=file_path,
        file_type=file_type,
        admin_user_id=admin_user_id,
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    return invoice

def upload_invoice(db: Session, file, admin_user_id: str):
    # Define S3 path
    s3_path = f"invoices/{file.filename}"
    
    # Upload file directly to S3
    s3_url = upload_file_to_s3(file, bucket_name, object_name=s3_path)
    
    # Store file info in DB
    invoice = create_invoice(db, file_path=s3_url, file_type=file.content_type, admin_user_id=admin_user_id)
    
    return invoice