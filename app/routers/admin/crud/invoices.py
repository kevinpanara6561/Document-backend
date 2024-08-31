import io
import logging
from typing import List, Optional

from PyPDF2 import PdfWriter
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from app.libs.s3_service import upload_file_to_s3
from app.libs.utils import generate_id, generate_presigned_url
from app.models import CategoryModel, DocumentModel
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.routers.admin import schemas
from app.routers.admin.schemas import CategoryResponse, InvoiceResponse, SubCategoryResponse
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
        original_file_name = file.filename
        unique_file_name = generate_unique_filename(db, original_file_name)        
        s3_path = f"invoices/{unique_file_name}"
        
        file_content = file.file.read()
        
        if password and file.content_type == 'application/pdf':
            pdf_data = password_protect_pdf(file_content, password)
            s3_url = upload_file_to_s3(pdf_data, bucket_name, object_name=s3_path)
        else:
            s3_url = upload_file_to_s3(file_content, bucket_name, object_name=s3_path)
        
        password_hash = generate_password_hash(password) if password else None
        
        invoice = create_invoice(
            db, 
            file_path=s3_url, 
            file_name=unique_file_name, 
            file_type=file.content_type, 
            admin_user_id=admin_user_id, 
            password=password_hash
        )
        invoices.append(invoice)
    
    return invoices

def check_file_exists(db: Session, file_name: str) -> bool:
    return db.query(DocumentModel).filter(DocumentModel.name == file_name, DocumentModel.is_deleted == False).first() is not None

def generate_unique_filename(db: Session, original_file_name: str) -> str:
    """
    Check if the file name exists in the database, and if so, append a unique suffix.
    """
    file_name, file_extension = os.path.splitext(original_file_name)
    logging.info(f"file_name: {file_name}")
    logging.info(f"file_extension: {file_extension}")
    counter = 1
    
    while check_file_exists(db, original_file_name):
        original_file_name = f"{file_name}({counter}){file_extension}"
        logging.info(f"original_file_name: {original_file_name}")
        counter += 1
    
    return original_file_name

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

def get_documents(db: Session, admin_user_id: int) -> List[CategoryResponse]:
    categories = db.query(CategoryModel).filter(
        CategoryModel.parent_id == None,
        CategoryModel.is_deleted == False
    ).all()
    
    category_responses = []
    
    for category in categories:
        sub_categories = db.query(CategoryModel).filter(
            CategoryModel.parent_id == category.id,
            CategoryModel.is_deleted == False
        ).all()
        
        sub_category_responses = []
        for sub_category in sub_categories:
            # Only fetch invoices that belong to the current admin_user
            invoices = db.query(DocumentModel).filter(
                DocumentModel.category_id == sub_category.id,
                DocumentModel.is_deleted == False,
                DocumentModel.admin_user_id == admin_user_id  # Filter by the logged-in user
            ).all()
            
            invoice_responses = [InvoiceResponse(
                id=invoice.id,
                name=invoice.name,
                file_path=invoice.file_path,
                file_type=invoice.file_type,
                admin_user_id=invoice.admin_user_id
            ) for invoice in invoices]
            
            sub_category_responses.append(SubCategoryResponse(
                id=sub_category.id,
                name=sub_category.name,
                documents=invoice_responses
            ))
        
        category_responses.append(CategoryResponse(
            id=category.id,
            name=category.name,
            sub_categories=sub_category_responses
        ))

    return category_responses

