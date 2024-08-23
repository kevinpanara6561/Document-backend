from typing import List, Optional

from fastapi import UploadFile
from app.libs.s3_service import upload_file_to_s3
from app.libs.utils import generate_id, generate_presigned_url
from app.models import InvoiceModel
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.routers.admin import schemas
from app.routers.admin.schemas import InvoiceResponse

load_dotenv()

bucket_name = os.getenv("AWS_BUCKET")

def create_invoice(db: Session, file_path: str, file_name: str, file_type: str, admin_user_id: str):
    invoice = InvoiceModel(
        id=generate_id(),
        name=file_name,
        file_path=file_path,
        file_type=file_type,
        admin_user_id=admin_user_id,
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    return invoice

def upload_invoices(db: Session, files: List[UploadFile], admin_user_id: str):
    invoices = []
    for file in files:
        # Extract file name
        file_name = file.filename
        
        # Define S3 path for each file
        s3_path = f"invoices/{file_name}"
        
        # Upload file directly to S3
        s3_url = upload_file_to_s3(file, bucket_name, object_name=s3_path)
        
        # Store file info in DB with name
        invoice = create_invoice(db, file_path=s3_url, file_name=file_name, file_type=file.content_type, admin_user_id=admin_user_id)
        invoices.append(invoice)
    
    return invoices

def get_invoices(
    db: Session,
    start: int,
    limit: int,
    invoice_id: Optional[str] = None
) -> schemas.InvoiceResponseList:
    query = db.query(InvoiceModel).filter(InvoiceModel.is_deleted == False)

    if invoice_id:
        query = query.filter(InvoiceModel.id == invoice_id)

    count = query.count()

    results = query.offset(start).limit(limit).all()

    invoice_responses = []
    for invoice in results:
        invoice.file_path = generate_presigned_url(invoice.file_path)
        invoice_response = schemas.InvoiceResponse(
            id=invoice.id,
            name=invoice.name,
            file_path=invoice.file_path,
            file_type=invoice.file_type,
            admin_user_id=invoice.admin_user_id
        )
        invoice_responses.append(invoice_response)

    return schemas.InvoiceResponseList(count=count, data=invoice_responses)