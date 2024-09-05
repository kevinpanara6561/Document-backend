from datetime import date, datetime
import json
from typing import List, Optional

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, Json, validator


class AdminUserChangePassword(BaseModel):
    old_password: str = Field(min_length=6, max_length=50)
    new_password: str = Field(min_length=6, max_length=50)


class AdminUserResetPassword(BaseModel):
    new_password: str = Field(min_length=6, max_length=50)

class AdminUser(BaseModel):
    id: str
    name: str
    email: str
    
    class Config:
        orm_mode = True


class AdminUserAll(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        orm_mode = True


class AdminUserList(BaseModel):
    count: int
    list: List[AdminUserAll]

    class Config:
        orm_mode = True


class AdminUserSmall(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True

class Register(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=6, max_length=50)
    
    @validator("email")
    def valid_email(cls, email):
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )

class RegisterResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    
    class Config:
        orm_mode = True
    
    
class Login(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=50)

    @validator("email")
    def valid_email(cls, email):
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )


class LoginResponse(AdminUserAll):
    token: str

    class Config:
        orm_mode = True


class ForgotPassword(BaseModel):
    email: str = Field(min_length=3, max_length=100)

    @validator("email")
    def valid_email(cls, email):
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )


class ConfirmForgotPassword(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    otp: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=6, max_length=50)

    @validator("email")
    def valid_email(cls, email):
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )


class ChangePassword(BaseModel):
    password: str = Field(min_length=6, max_length=50)
    new_password: str = Field(min_length=6, max_length=50)
    
class InvoiceResponse(BaseModel):
    id: str
    name: str
    file_path: str
    file_type: str
    admin_user_id: str

    class Config:
        orm_mode = True
        
class InvoiceResponseList(BaseModel):
    count: int
    data: List[InvoiceResponse]
    
class SubCategoryResponse(BaseModel):
    id: str
    name: str
    documents: List[InvoiceResponse]
    
    class Config:
        orm_mode = True
    
class CategoryResponse(BaseModel):
    id: str
    name: str
    sub_categories: List[SubCategoryResponse]
    
    class Config:
        orm_mode = True
        
class EmailCreateRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str
    
class DocumentResponse(BaseModel):
    id: str
    name: str
    file_type: str
    url: str
    admin_user_id: str
    
    class Config:
        orm_mode = True
    
class ExtreactData(BaseModel):
    id: str
    data: Json
    
    class Config:
        orm_mode = True