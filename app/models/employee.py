from sqlalchemy import (
    Column, Integer, String, DateTime,
    Enum, ForeignKey, Numeric, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class EmploymentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    on_leave = "on_leave"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    # personal info
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # job info
    job_title = Column(String, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric(10, 2), nullable=False)  # e.g. 75000.00
    status = Column(
        Enum(EmploymentStatus, native_enum=False),
        default=EmploymentStatus.active,
        nullable=False,
    )
    avatar_url = Column(String, nullable=True)

    # links to the User account (optional — employee may not have login)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)

    # timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships — lets you do employee.department and employee.user in code
    department = relationship("Department", back_populates="employees")
    user = relationship("User", backref="employee_profile")