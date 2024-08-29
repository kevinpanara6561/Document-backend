import io
from typing import List, Optional

from PyPDF2 import PdfWriter
from fastapi import UploadFile
from app.libs.s3_service import upload_file_to_s3
from app.libs.utils import generate_id, generate_presigned_url
from app.models import DocumentModel
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.routers.admin import schemas
from app.routers.admin.schemas import InvoiceResponse
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

bucket_name = os.getenv("AWS_BUCKET")

def create_invoice(db: Session, file_path: str, file_name: str, file_type: str, admin_user_id: str, password: str):
    invoice = DocumentModel(
        id=generate_id(),
        name=file_name,
        file_path=file_path,
        file_type=file_type,
        admin_user_id=admin_user_id,
        password=password
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    return invoice

def upload_invoices(db: Session, files: List[UploadFile], admin_user_id: str, password: Optional[str] = None):
    invoices = []
    for file in files:
        file_name = file.filename
        s3_path = f"invoices/{file_name}"
        
        # Read file content
        file_content = file.file.read()  # Read file synchronously
        
        if password and file.content_type == 'application/pdf':
            # Apply password protection to the PDF
            pdf_data = password_protect_pdf(file_content, password)
            s3_url = upload_file_to_s3(pdf_data, bucket_name, object_name=s3_path)
        else:
            # Directly upload the file content if no password
            s3_url = upload_file_to_s3(file_content, bucket_name, object_name=s3_path)
        
        password_hash = generate_password_hash(password) if password else None
        
        # Create and store the invoice in the database
        invoice = create_invoice(
            db, 
            file_path=s3_url, 
            file_name=file_name, 
            file_type=file.content_type, 
            admin_user_id=admin_user_id, 
            password=password_hash
        )
        invoices.append(invoice)
    
    return invoices


def password_protect_pdf(file_content: bytes, password: str) -> bytes:
    pdf_writer = PdfWriter()
    
    # Use the bytes content directly
    pdf_reader = io.BytesIO(file_content)
    
    pdf_writer.append(pdf_reader)
    pdf_writer.encrypt(user_pwd=password, owner_pwd=password, use_128bit=True)
    
    output = io.BytesIO()
    pdf_writer.write(output)    
    return output.getvalue()

def get_invoices(
    db: Session,
    start: int,
    limit: int,
    invoice_id: Optional[str] = None
) -> schemas.InvoiceResponseList:
    query = db.query(DocumentModel).filter(DocumentModel.is_deleted == False)

    if invoice_id:
        query = query.filter(DocumentModel.id == invoice_id)

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