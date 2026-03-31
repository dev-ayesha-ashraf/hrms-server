from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal


class PayrollGenerate(BaseModel):
    month: int          # 1-12
    year: int
    # optional overrides per employee
    performance_bonus: Optional[float] = 0
    overtime_hours: Optional[float] = 0


class PayrollBulkGenerate(BaseModel):
    month: int
    year: int


class PayrollMarkPaid(BaseModel):
    notes: Optional[str] = None


class EmployeeBasic(BaseModel):
    id: int
    first_name: str
    last_name: str
    job_title: str

    class Config:
        from_attributes = True


class PayrollResponse(BaseModel):
    id: int
    employee: EmployeeBasic
    month: int
    year: int
    base_salary: Decimal
    overtime_bonus: Decimal
    performance_bonus: Decimal
    gross_salary: Decimal
    income_tax: Decimal
    social_security: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    days_present: int
    days_absent: int
    overtime_hours: Decimal
    is_paid: bool
    paid_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True