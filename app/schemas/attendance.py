from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal


class AttendanceClockIn(BaseModel):
    note: Optional[str] = None


class AttendanceClockOut(BaseModel):
    note: Optional[str] = None


class EmployeeBasic(BaseModel):
    id: int
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    id: int
    employee: EmployeeBasic
    date: date
    clock_in: datetime
    clock_out: Optional[datetime]
    hours_worked: Optional[Decimal]
    note: Optional[str]

    class Config:
        from_attributes = True


class AttendanceStatus(BaseModel):
    is_clocked_in: bool
    record: Optional[AttendanceResponse]