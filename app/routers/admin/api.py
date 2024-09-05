from datetime import datetime, timedelta
import logging
import os
from typing import List, Optional
from botocore.exceptions import ClientError
import boto3

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.libs.utils import generate_presigned_url
from app.models import CategoryModel, DocumentModel, ExtractedDataModel
from app.routers.admin import schemas
from app.routers.admin.crud import (
    admin_users,
    emails,
    invoices,
    whatsapp
)
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


# Authentication

@router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
)
def register(request: schemas.Register, db: Session = Depends(get_db)):
    """
    url: `/register`
    """
    data = admin_users.register(db, request)
    return data

@router.get(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    response_class=HTMLResponse
)
def verify_email(
    db: Session = Depends(get_db),
    token: str = Query(..., description="The token for email verification")
):
    """
    URL: `/verify-email`
    Query parameter: `token`
    """
    # Call the function to handle the verification
    result = admin_users.verify_email(db, token)
    
    # Render HTML content based on the result
    if "Email verified successfully" in result["message"]:
        html_content = """
        <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 0; }
                    .container { background-color: #ffffff; margin: 50px auto; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); max-width: 500px; }
                    .header { background-color: #4CAF50; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; color: white; }
                    .content { margin: 20px 0; text-align: center; }
                    .footer { text-align: center; font-size: 12px; color: #777; margin-top: 20px; }
                    .button { display: inline-block; padding: 10px 20px; font-size: 16px; color: #fff; background-color: #4CAF50; border-radius: 5px; text-decoration: none; }
                    .button:hover { background-color: #45a049; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Email Verification</h2>
                    </div>
                    <div class="content">
                        <p>Your email has been successfully verified!</p>
                        <a href="/login" class="button">Login</a>
                    </div>
                    <div class="footer">
                        <p>If you need further assistance, please <a href="#">contact support</a>.</p>
                    </div>
                </div>
            </body>
        </html>
        """
    else:
        html_content = """
        <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 0; }
                    .container { background-color: #ffffff; margin: 50px auto; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); max-width: 500px; }
                    .header { background-color: #f44336; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; color: white; }
                    .content { margin: 20px 0; text-align: center; }
                    .footer { text-align: center; font-size: 12px; color: #777; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Email Verification</h2>
                    </div>
                    <div class="content">
                        <p>There was an issue verifying your email. Please try again.</p>
                    </div>
                    <div class="footer">
                        <p>If you need further assistance, please <a href="#">contact support</a>.</p>
                    </div>
                </div>
            </body>
        </html>
        """

    return HTMLResponse(content=html_content)

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=schemas.LoginResponse,
    tags=["Authentication"],
)
def sign_in(admin_user: schemas.Login, db: Session = Depends(get_db)):
    """
    url: `/login`
    """
    data = admin_users.sign_in(db, admin_user)
    return data


@router.post("/forgot-password", tags=["Authentication"])
def send_forgot_password_email(
    admin_user: schemas.ForgotPassword, db: Session = Depends(get_db)
):
    """
    url: `/forgot-password`
    """
    data = admin_users.send_forgot_password_email(db=db, admin_user=admin_user)
    return data


@router.put("/forgot-password", tags=["Authentication"])
def confirm_forgot_password(
    admin_user: schemas.ConfirmForgotPassword, db: Session = Depends(get_db)
):
    """
    url: `/forgot-password`
    """
    data = admin_users.confirm_forgot_password(db=db, admin_user=admin_user)
    return data


# End Authentication


@router.post(
    "/upload-invoice",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.InvoiceResponse],
    tags=["Invoices"],
)
def upload_invoice(token: str = Header(None), 
                   files: List[UploadFile] = File(...), 
                   db: Session = Depends(get_db), 
                   password: Optional[str] = Form(None)):
    """
    url: `/upload-invoice`
    Upload multiple invoices with optional password protection.
    """
    db_admin_user = admin_users.verify_token(db, token=token)
    
    # Upload multiple files with password if provided
    data = invoices.upload_invoices(db, files, db_admin_user.id, password=password)
    
    return data

@router.get("/invoices", response_model=schemas.InvoiceResponseList)
def list_invoices(
    token: str = Header(None),
    db: Session = Depends(get_db),
    start: int = Query(0, ge=0),
    limit: int = Query(10, ge=1)
):
    admin_user = admin_users.verify_token(db, token=token)
    
    # Fetch invoices with pagination
    paginated_invoices = invoices.get_invoices(admin_user.id, db, start=start, limit=limit)
    return paginated_invoices

@router.get("/documents", response_model=List[schemas.CategoryResponse], tags=['Documents'])
def get_all_documents(
    token: str = Header(None),
    db: Session = Depends(get_db),
):
    admin_user = admin_users.verify_token(db, token=token)
    admin_user_id = admin_user.id
    
    # Fetch invoices with pagination
    data = invoices.get_documents(db=db, admin_user_id=admin_user_id)
    return data

VERIFY_TOKEN = "ileWgE0aa6otQjlXUBFy6crtfmWMwbIG"

@router.get("/receive-message-whatsapp", tags=["Whatsapp"])
async def verify_webhook(request: Request):
    verify_token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    if verify_token == VERIFY_TOKEN:
        return int(challenge)
    return {"message": "Invalid token"}

@router.post("/receive-message-whatsapp", tags=["Whatsapp"])
async def receive_whatsapp_message(request: Request, db: Session = Depends(get_db)):
    await whatsapp.receive_data(request=request, db=db)
    return {"data":"success"}

@router.post("/emails", tags=["Email"])
def add_email(
    request: schemas.EmailCreateRequest,
    token: str = Header(None),
    db: Session = Depends(get_db),
    ):
    admin_user = admin_users.verify_token(db=db, token=token)
    data = emails.add_email(request=request, db=db, admin_user_id=admin_user.id)
    return {'message':"Email added successfully"}

# @router.get("/emails", tags=["Email"])
# def get_emails(
#     request: schemas.EmailCreateRequest,
#     token: str = Header(None),
#     db: Session = Depends(get_db),
#     ):
#     admin_user = admin_users.verify_token(db=db, token=token)
#     data = emails.add_email(request=request, db=db, admin_user_id=admin_user.id)
#     return {'message':"Email added successfully"}


@router.get("/documents/{document_id}", response_model=schemas.DocumentResponse, tags=['Documents'])
def get_document_by_id(
    document_id: str,
    token: str = Header(None),
    db: Session = Depends(get_db),
):
    # Verify the admin user token
    admin_user = admin_users.verify_token(db, token=token)
    # admin_user_id = admin_user.id

    # Fetch the document from the database
    document = db.query(DocumentModel).filter(
        DocumentModel.id == document_id,
        DocumentModel.is_deleted == False,
    ).first()

    # If the document is not found, raise a 404 error
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Generate a presigned URL for the document's file in S3
    presigned_url = generate_presigned_url(document.file_path)

    # Create a response model to return
    document_response = schemas.DocumentResponse(
        id=document.id,
        name=document.name,
        file_type=document.file_type,
        url=presigned_url,
        admin_user_id=document.admin_user_id
    )

    return document_response

@router.get("/documents/{document_id}/extreact-data", response_model=schemas.ExtreactData, tags=['Documents'])
def get_extreact_data(
    document_id: str,
    token: str = Header(None),
    db: Session = Depends(get_db),
):
    # Verify the admin user token
    admin_user = admin_users.verify_token(db, token=token)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    # Fetch extracted data by document_id
    extreact_data = db.query(ExtractedDataModel).filter_by(document_id=document_id, is_deleted=False).first()

    if not extreact_data:
        raise HTTPException(status_code=404, detail="Extracted data not found")

    return extreact_data

@router.get("/dashboard")
def get_dashboard_count(
    token: str = Header(None),
    db: Session = Depends(get_db),
):
    # Verify admin user from token
    admin_user = admin_users.verify_token(db, token=token)

    # Query to count total documents for the admin user
    total_documents = db.query(DocumentModel).filter(DocumentModel.admin_user_id == admin_user.id).count()

    # Join DocumentModel with CategoryModel and classify based on the category name
    classified_count = (
        db.query(DocumentModel)
        .join(CategoryModel, DocumentModel.category_id == CategoryModel.id)
        .filter(DocumentModel.admin_user_id == admin_user.id)
        .filter(CategoryModel.name != "Other")
        .count()
    )

    unclassified_count = (
        db.query(DocumentModel)
        .join(CategoryModel, DocumentModel.category_id == CategoryModel.id)
        .filter(DocumentModel.admin_user_id == admin_user.id)
        .filter(CategoryModel.name == "Other")
        .count()
    )

    # Return the result as a JSON response
    return {
        "total_documents": total_documents,
        "classified_document": classified_count,
        "unclassified_document": unclassified_count,
    }
    

# Initialize the S3 client
s3_client = boto3.client('s3')

@router.delete("/documents/{document_id}", tags=["Documents"])
def delete_document(
    document_id: str,
    token: str = Header(None),
    db: Session = Depends(get_db),
):
    admin_user = admin_users.verify_token(db, token=token)
    
    db_document = db.query(DocumentModel).filter(
        DocumentModel.id == document_id, 
        DocumentModel.is_deleted == False
    ).first()
    
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    s3_file_key = db_document.file_path
    s3_bucket_name = os.getenv("AWS_BUCKET")
    
    try:
        s3_client.delete_object(Bucket=s3_bucket_name, Key=s3_file_key)
        
        db.delete(db_document)
        db.commit()
        
        return {"message": "Document and associated S3 file deleted successfully"}
    
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete S3 file: {e}")
    

@router.delete("/categories/{category_id}", tags=["Categories"])
def delete_category(
    category_id: str,
    token: str = Header(None),
    db: Session = Depends(get_db),
):
    admin_user = admin_users.verify_token(db, token=token)
    
    db_category = db.query(CategoryModel).filter(
        CategoryModel.id == category_id, 
        CategoryModel.is_deleted == False
    ).first()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_sub_categories = db.query(CategoryModel).filter(CategoryModel.parent_id == category_id).all()
    for db_sub_category in db_sub_categories:
        db_documents = db.query(DocumentModel).filter(DocumentModel.category_id == db_sub_category.id).all()
        for db_document in db_documents:
            db_extreacted_datas = db.query(ExtractedDataModel).filter(ExtractedDataModel.document_id == db_document.id).all()
            for db_extreacted_data in db_extreacted_datas:
                db.delete(db_extreacted_data)
                db.commit()
                
            db.delete(db_document)
            db.commit()
            
            s3_file_key = db_document.file_path
            s3_bucket_name = os.getenv("AWS_BUCKET")
            
            try:
                s3_client.delete_object(Bucket=s3_bucket_name, Key=s3_file_key)
            except ClientError as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete S3 file: {e}")
            
        db.delete(db_sub_category)
        db.commit()
    
    db.delete(db_category)
    db.commit()
    
    return {"message": "Category and associated records deleted successfully"}

