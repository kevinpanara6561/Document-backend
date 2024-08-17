from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    JSON
)
from sqlalchemy.orm import relationship

from app.database import Base

class AdminUserModel(Base):
    __tablename__ = "admin_users"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    password = Column(String(255), nullable=False)
    is_registered = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String(50), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)

class AdminUserOtpModel(Base):
    __tablename__ = "admin_user_otps"

    id = Column(String(36), primary_key=True)
    otp = Column(String(6), nullable=False)
    is_redeemed = Column(Boolean, nullable=False, default=False)
    admin_user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)

    admin_user = relationship("AdminUserModel", backref="otps")
    
class InvoiceModel(Base):
    __tablename__ = "invoices"
    
    id = Column(String(36), primary_key=True)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    admin_user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    admin_user = relationship("AdminUserModel", backref="invoices")
    
class ExtractedDataModel(Base):
    __tablename__ = "extracted_datas"
    
    id = Column(String(36), primary_key=True)
    data = Column(JSON, nullable=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    invoice = relationship("InvoiceModel", backref="extracted_datas")
    