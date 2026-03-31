from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import List, Optional
from app.models.employee import EmploymentStatus


# ── DEPARTMENT (simple, needed for nested response) ──────
class DepartmentBasic(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# ── EMPLOYEE SCHEMAS ──────────────────────────────────────

# what comes IN when creating an employee
class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    job_title: str
    department_id: Optional[int] = None
    hire_date: date
    salary: float
    status: EmploymentStatus = EmploymentStatus.active
    user_id: Optional[int] = None


# what comes IN when updating (all fields optional — update only what you send)
class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[int] = None
    salary: Optional[float] = None
    status: Optional[EmploymentStatus] = None


class EmployeeResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    date_of_birth: Optional[date]
    job_title: str
    department: Optional[DepartmentBasic]
    hire_date: date
    salary: float
    status: EmploymentStatus
    avatar_url: Optional[str] = None    # ← add this
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedEmployeeResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    data: List[EmployeeResponse]