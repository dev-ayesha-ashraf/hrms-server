from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.leave_request import LeaveStatus, LeaveType


class EmployeeBasic(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


class ReviewerBasic(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    from_date: date
    to_date: date
    reason: Optional[str] = None


class LeaveStatusUpdate(BaseModel):
    status: LeaveStatus
    review_note: Optional[str] = None


class LeaveRequestResponse(BaseModel):
    id: int
    employee_id: int
    leave_type: LeaveType
    from_date: date
    to_date: date
    reason: Optional[str]
    status: LeaveStatus
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    employee: Optional[EmployeeBasic] = None
    reviewed_by: Optional[ReviewerBasic] = None
    total_days: int

    class Config:
        from_attributes = True