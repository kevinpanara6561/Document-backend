from datetime import datetime, timedelta
import logging
from typing import List, Optional

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
from app.routers.admin import schemas
from app.routers.admin.crud import (
    admin_users,
    invoices,
    whatsapp
)
from fastapi.responses import HTMLResponse

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
    admin_users.verify_token(db, token=token)
    
    # Fetch invoices with pagination
    paginated_invoices = invoices.get_invoices(db, start=start, limit=limit)
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
    logging.info("called")
    await whatsapp.receive_data(request=request, db=db)
    return {"data":"success"}