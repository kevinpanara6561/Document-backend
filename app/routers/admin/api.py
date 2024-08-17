from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
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
    invoices
)

router = APIRouter()


# Authentication

@router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RegisterResponse,
    tags=["Authentication"],
)
def register(request: schemas.Register, db: Session = Depends(get_db)):
    """
    url: `/register`
    """
    data = admin_users.register(db, request)
    return data

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
    response_model=schemas.InvoiceResponse,
    tags=["Invoices"],
)
def upload_invoice(token: str = Header(None), file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    url: `/upload-invoice`
    """
    db_admin_user = admin_users.verify_token(db, token=token)
    data = invoices.upload_invoice(db, file, db_admin_user.id)
    return data