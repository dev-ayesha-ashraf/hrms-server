from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.leave_request import LeaveRequest, LeaveStatus
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.leave_request import (
    LeaveRequestCreate,
    LeaveStatusUpdate,
    LeaveRequestResponse
)
from app.utils.oauth2 import get_current_user
from app.utils.permissions import require_roles
from app.utils.notifications import notify_all_hr_and_admins, notify_user

router = APIRouter(prefix="/leave-requests", tags=["Leave Requests"])


def calculate_days(from_date, to_date) -> int:
    # +1 because both start and end dates are inclusive
    # e.g. Monday to Wednesday = 3 days not 2
    return (to_date - from_date).days + 1


def build_response(leave: LeaveRequest) -> dict:
    # manually build response to include computed total_days
    return {
        **{c.name: getattr(leave, c.name) for c in leave.__table__.columns},
        "employee": leave.employee,
        "reviewed_by": leave.reviewed_by,
        "total_days": calculate_days(leave.from_date, leave.to_date),
    }


# ── GET ALL — HR/Admin sees all, Employee sees only theirs ──
@router.get("/", response_model=List[LeaveRequestResponse])
def get_leave_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role in [UserRole.admin, UserRole.hr]:
        # HR and admin see everything
        leaves = (
            db.query(LeaveRequest)
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )
    else:
        # employees only see their own requests
        # find the employee record linked to this user
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()

        if not employee:
            return []  # user has no employee profile yet

        leaves = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.employee_id == employee.id)
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )

    return [build_response(l) for l in leaves]


# ── GET ONE ───────────────────────────────────────────────
@router.get("/{leave_id}", response_model=LeaveRequestResponse)
def get_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # employees can only view their own requests
    if current_user.role == UserRole.employee:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()
        if not employee or leave.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return build_response(leave)


# ── CREATE — employees submit their own requests ──────────
@router.post("/", response_model=LeaveRequestResponse, status_code=201)
def create_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # find the employee profile for this user
    employee = db.query(Employee).filter(
        Employee.user_id == current_user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=400,
            detail="You don't have an employee profile. Contact HR."
        )

    # check for overlapping approved/pending requests
    overlap = db.query(LeaveRequest).filter(
        and_(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_([LeaveStatus.pending, LeaveStatus.approved]),
            LeaveRequest.from_date <= data.to_date,
            LeaveRequest.to_date >= data.from_date,
        )
    ).first()

    if overlap:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a {overlap.status} request overlapping these dates"
        )

    leave = LeaveRequest(
        employee_id=employee.id,
        leave_type=data.leave_type,
        from_date=data.from_date,
        to_date=data.to_date,
        reason=data.reason,
    )
    db.add(leave)
    db.flush()
    # tell HR someone submitted leave
    notify_all_hr_and_admins(
        db=db,
        title="New Leave Request",
        message=(
            f"{employee.first_name} {employee.last_name} requested "
            f"{data.leave_type} leave from {data.from_date} to {data.to_date}."
        ),
        type="info",
        link="/leave-requests",
    )
    db.commit()
    db.refresh(leave)
    return build_response(leave)


# ── UPDATE STATUS — HR approves/rejects, employee cancels ─
@router.patch("/{leave_id}/status", response_model=LeaveRequestResponse)
def update_leave_status(
    leave_id: int,
    data: LeaveStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # ── CANCELLATION — employee cancels their own pending request ──
    if data.status == LeaveStatus.cancelled:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()

        # HR/admin can also cancel any request
        if current_user.role == UserRole.employee:
            if not employee or leave.employee_id != employee.id:
                raise HTTPException(status_code=403, detail="You can only cancel your own requests")

        if leave.status != LeaveStatus.pending:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel a {leave.status} request"
            )

    # ── APPROVE/REJECT — HR and admin only ────────────────────
    else:
        if current_user.role == UserRole.employee:
            raise HTTPException(
                status_code=403,
                detail="Only HR or Admin can approve or reject requests"
            )

        if leave.status != LeaveStatus.pending:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change status of a {leave.status} request"
            )
        # notify the employee if their request was decided
        if data.status in [LeaveStatus.approved, LeaveStatus.rejected]:
            # find the user linked to this employee
            employee_user = db.query(User).filter(
                User.id == leave.employee.user_id
            ).first() if leave.employee.user_id else None

            if employee_user:
                is_approved = data.status == LeaveStatus.approved
                notify_user(
                    db=db,
                    user_id=employee_user.id,
                    title=f"Leave Request {data.status.capitalize()}",
                    message=(
                        f"Your {leave.leave_type} leave request "
                        f"({leave.from_date} to {leave.to_date}) "
                        f"has been {data.status}."
                        + (f" Note: {data.review_note}" if data.review_note else "")
                    ),
                    type="success" if is_approved else "warning",
                    link="/leave-requests",
                )

        # record who reviewed it and when
        leave.reviewed_by_id = current_user.id
        leave.reviewed_at = datetime.utcnow()
        leave.review_note = data.review_note
        
    leave.status = data.status
    
    db.commit()
    db.refresh(leave)
    return build_response(leave)


# ── DELETE — admin only, only pending requests ────────────
@router.delete("/{leave_id}", status_code=204)
def delete_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if leave.status != LeaveStatus.pending:
        raise HTTPException(
            status_code=400,
            detail="Can only delete pending requests"
        )

    db.delete(leave)
    db.commit()
    return None