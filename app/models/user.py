from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
import enum
from app.database import Base


# This defines the allowed roles as a proper Python enum
class UserRole(str, enum.Enum):
    admin = "admin"
    hr = "hr"
    employee = "employee"


# This class = one table in your database
# Every attribute with Column() = one column in that table
class User(Base):
    __tablename__ = "users"  # the actual table name in PostgreSQL

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole, native_enum=False), default=UserRole.employee, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())