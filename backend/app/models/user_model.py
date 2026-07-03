from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.mysql import Base

class User(Base):
    __tablename__ = "users"

    # Định nghĩa các cột trong MySQL
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True) 
    email = Column(String(150), unique=True, index=True, nullable=False)  
    password = Column(String(255), nullable=False)                         
    role = Column(String(50), default="user", nullable=False)   
    
    full_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    documents = relationship("Document", back_populates="user")