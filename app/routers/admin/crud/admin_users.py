import json
import traceback
from typing import Optional
import os

import bcrypt
from fastapi import HTTPException, status
from jwcrypto import jwk, jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.libs.emails import send_email
from app.libs.utils import date_time_diff_min, generate_id, generate_otp, generate_verification_token, now
from app.models import AdminUserModel, AdminUserOtpModel
from app.routers.admin.crud.email_templates import forgot_password, send_verify_email
from app.routers.admin.schemas import (
    AdminUserChangePassword,
    AdminUserResetPassword,
    ConfirmForgotPassword,
    ForgotPassword,
    Login,
    LoginResponse,
    Register,
)

load_dotenv()

# Load JWT_KEY and convert it from a JSON string to a dictionary
JWT_KEY = json.loads(os.environ.get("JWT_KEY"))

def get_token(admin_user_id, email):
    claims = {"id": admin_user_id, "email": email, "time": str(now())}

    # Create a signed token with the generated key
    key = jwk.JWK(**JWT_KEY)
    Token = jwt.JWT(header={"alg": "HS256"}, claims=claims)
    Token.make_signed_token(key)

    # Further encrypt the token with the same key
    encrypted_token = jwt.JWT(
        header={"alg": "A256KW", "enc": "A256CBC-HS512"}, claims=Token.serialize()
    )
    encrypted_token.make_encrypted_token(key)
    token = encrypted_token.serialize()
    return token


def verify_token(db: Session, token: str):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )
    else:
        try:
            key = jwk.JWK(**JWT_KEY)
            ET = jwt.JWT(key=key, jwt=token, expected_type="JWE")
            ST = jwt.JWT(key=key, jwt=ET.claims)
            claims = ST.claims
            claims = json.loads(claims)
            db_admin_user = get_admin_user_by_id(db, id=claims["id"])
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if db_admin_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        elif db_admin_user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        return db_admin_user


def create_password(password: str) -> str:
    # password = bytes(password, "utf-8")
    password = password.encode("utf-8")
    password = bcrypt.hashpw(password, bcrypt.gensalt())
    password = password.decode("utf-8")
    return password


def get_admin_user_by_id(db: Session, id: str):
    return db.query(AdminUserModel).filter(AdminUserModel.id == id).first()


def get_admin_user_by_email(db: Session, email: str):
    return (
        db.query(AdminUserModel)
        .filter(AdminUserModel.email == email, AdminUserModel.is_deleted == False)
        .first()
    )

def register(db: Session, request: Register):
    db_admin_user = get_admin_user_by_email(db, email=request.email)
    if db_admin_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    
    # Create the admin user
    admin_user = AdminUserModel(
        id=generate_id(),
        name=request.name,
        email=request.email,
        phone=request.phone,
        password=create_password(request.password),
    )
    
    # Add user to the database
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Generate a verification token and link
    verification_token = generate_verification_token()
    verification_link = f"http://127.0.0.1:8008/verify-email?token={verification_token}"
    
    # Store the verification token in the database (you may need to add a field for it)
    admin_user.verification_token = verification_token
    db.commit()
    
    # Send verification email
    email_content = send_verify_email(admin_user.name, verification_link)
    send_email([admin_user.email], "Verify your email address", email_content)
    
    return {"message": "User registered successfully. Please check your email to verify your account."}


def verify_email(db: Session, token: str):
    print(token)
    user = db.query(AdminUserModel).filter(AdminUserModel.verification_token == token).first()
    print(user)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired token")
    
    if user.is_registered:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered")
    
    user.is_registered = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}

def sign_in(db: Session, admin_user: Login) -> LoginResponse:
    db_admin_user = get_admin_user_by_email(db, email=admin_user.email)
    if db_admin_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    elif db_admin_user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    elif db_admin_user.is_registered is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    hashed = db_admin_user.password.encode("utf-8")
    # hashed = bytes(hashed.encode, "utf-8")
    password = admin_user.password.encode("utf-8")
    if not bcrypt.checkpw(password, hashed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    db_admin_user.token = get_token(db_admin_user.id, db_admin_user.email)
    return db_admin_user


def change_password(db: Session, admin_user: AdminUserChangePassword, token: str):
    db_admin_user = verify_token(db, token=token)
    try:
        hashed = bytes(db_admin_user.password, "utf-8")
        password = bytes(admin_user.old_password, "utf-8")
        result = bcrypt.checkpw(password, hashed)
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect old password"
        )
    else:
        password = create_password(admin_user.new_password)
        db_admin_user.password = password
        db_admin_user.updated_at = now()
        db.commit()


def reset_password(db: Session, admin_user: AdminUserResetPassword, admin_user_id: str):
    db_admin_user = get_admin_user_by_id(db, id=admin_user_id)
    if db_admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    else:
        hashed = create_password(admin_user.new_password)
        db_admin_user.password = hashed
        db_admin_user.updated_at = now()
        db.commit()
    return

def get_profile(db: Session, token: str):
    db_admin_user = verify_token(db, token=token)
    return db_admin_user

def send_forgot_password_email(db: Session, admin_user: ForgotPassword):
    db_admin_user = get_admin_user_by_email(db=db, email=admin_user.email)
    if not db_admin_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not registered",
        )
    otp = generate_otp()
    db_otp = AdminUserOtpModel(
        id=generate_id(),
        otp=otp,
        admin_user_id=db_admin_user.id,
    )
    db.add(db_otp)
    email_body = forgot_password(name=db_admin_user.name, otp=otp)
    if not send_email(
        recipients=[db_admin_user.email], subject="Forgot Password", body=email_body
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email not sent",
        )
    db.commit()


def confirm_forgot_password(db: Session, admin_user: ConfirmForgotPassword):
    db_admin_user = get_admin_user_by_email(db=db, email=admin_user.email)
    if not db_admin_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not registered",
        )

    date_time = now()
    db_otp = (
        db.query(AdminUserOtpModel)
        .filter(AdminUserOtpModel.admin_user_id == db_admin_user.id)
        .order_by(AdminUserOtpModel.created_at.desc())
        .first()
    )
    if db_otp.is_redeemed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid OTP."
        )
    elif date_time_diff_min(start=db_otp.created_at, end=date_time) >= 10:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="OTP expired."
        )
    elif db_otp.otp != admin_user.otp:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid OTP."
        )

    db_admin_user.password = create_password(admin_user.password)
    db_admin_user.updated_at = now()
    db_otp.is_redeemed = True
    db_otp.updated_at = now()
    db.commit()


def get_admin_user_for_list(db: Session, id: str):
    db_admin_user = db.query(AdminUserModel).filter(AdminUserModel.id == id).first()
    if db_admin_user is None:
        return {}
    name = db_admin_user.first_name + " " + db_admin_user.last_name
    data = {"id": db_admin_user.id, "name": name}
    return data

def get_admin_users(
    db: Session,
    start: int,
    limit: int,
    sort_by: Optional[str] = None,
    order: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(AdminUserModel).filter(AdminUserModel.is_deleted == False)

    if search:
        text = f"""%{search}%"""
        query = query.filter(
            or_(
                AdminUserModel.name.like(text),
                AdminUserModel.email.like(text),
            )
        )

    if sort_by == "name":
        if order == "desc":
            query = query.order_by(AdminUserModel.name.desc())
        else:
            query = query.order_by(AdminUserModel.name)
    elif sort_by == "email":
        if order == "desc":
            query = query.order_by(AdminUserModel.email.desc())
        else:
            query = query.order_by(AdminUserModel.email)
    else:
        query = query.order_by(AdminUserModel.created_at.desc())

    results = query.offset(start).limit(limit).all()
    count = query.count()
    data = {"count": count, "list": results}
    return data


def delete_admin_user(db: Session, admin_user_id: str):
    db_admin_user = get_admin_user_by_id(db, id=admin_user_id)
    if db_admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    db_admin_user.is_deleted = True
    db_admin_user.updated_at = now()
    db.commit()
    return

def get_admin_user(db: Session, admin_user_id: str):
    db_admin_user = get_admin_user_by_id(db, id=admin_user_id)
    if db_admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    db_admin_user.role = db_admin_user.admin_user_role[0].role
    return db_admin_user

def get_all_admin_users(db: Session):
    db_admin_users = (
        db.query(AdminUserModel)
        .filter(AdminUserModel.is_deleted == False)
        .order_by(AdminUserModel.name)
        .all()
    )
    return db_admin_users
