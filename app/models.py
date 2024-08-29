from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    JSON,
    Enum
)
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentStatusEnum(enum.Enum):
    """
    PENDING
    INPROCESS
    CLASSIFIED
    EXTRACTED
    COMPLETED
    """

    PENDING = "PENDING"
    INPROCESS = "INPROCESS"
    CLASSIFIED = "CLASSIFIED"
    EXTRACTED = "EXTRACTED"
    COMPLETED = "COMPLETED"

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
    
class CategoryModel(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100),nullable=False) 
    parent_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    parent = relationship("CategoryModel", remote_side=[id], backref="subcategories")
    
class DocumentModel(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    admin_user_id = Column(String(36), ForeignKey("admin_users.id"), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    is_priroty = Column(Boolean, nullable=False, default=False)
    password = Column(String(255), nullable=True)
    status = Column(Enum(DocumentStatusEnum), nullable=False, default=DocumentStatusEnum.PENDING)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    admin_user = relationship("AdminUserModel", backref="documents")
    category = relationship("CategoryModel", backref="documents")
    
class ExtractedDataModel(Base):
    __tablename__ = "extracted_datas"
    
    id = Column(String(36), primary_key=True)
    data = Column(JSON, nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    classification_result = Column(String(255), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    document = relationship("DocumentModel", backref="extracted_datas")
    