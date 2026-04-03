from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import csv
from io import StringIO
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.database import get_db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceClockIn,
    AttendanceClockOut,
    AttendanceResponse,
    AttendanceStatus
)
from app.utils.oauth2 import get_current_user
from app.utils.permissions import require_roles

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def get_employee_or_error(user: User, db: Session) -> Employee:
    employee = db.query(Employee).filter(
        Employee.user_id == user.id
    ).first()
    if not employee:
        raise HTTPException(
            status_code=400,
            detail="No employee profile found for your account"
        )
    return employee


# ── CLOCK IN ─────────────────────────────────────────────
@router.post("/clock-in", response_model=AttendanceResponse)
def clock_in(
    data: AttendanceClockIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = get_employee_or_error(current_user, db)
    today = date.today()

    # check if already clocked in today
    existing = db.query(Attendance).filter(
        and_(
            Attendance.employee_id == employee.id,
            Attendance.date == today
        )
    ).first()

    if existing:
        if existing.clock_out is None:
            raise HTTPException(
                status_code=400,
                detail="You are already clocked in today"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="You have already completed your attendance for today"
            )

    record = Attendance(
        employee_id=employee.id,
        date=today,
        clock_in=datetime.utcnow(),
        note=data.note
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── CLOCK OUT ─────────────────────────────────────────────
@router.post("/clock-out", response_model=AttendanceResponse)
def clock_out(
    data: AttendanceClockOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = get_employee_or_error(current_user, db)
    today = date.today()

    # find today's open record
    record = db.query(Attendance).filter(
        and_(
            Attendance.employee_id == employee.id,
            Attendance.date == today,
            Attendance.clock_out == None
        )
    ).first()

    if not record:
        raise HTTPException(
            status_code=400,
            detail="You haven't clocked in today"
        )

    now = datetime.utcnow()
    record.clock_out = now

    # calculate hours worked
    delta = now - record.clock_in.replace(tzinfo=None)
    total_seconds = delta.total_seconds()
    hours = Decimal(str(round(total_seconds / 3600, 2)))
    record.hours_worked = hours

    if data.note:
        record.note = data.note

    db.commit()
    db.refresh(record)
    return record


# ── TODAY'S STATUS — am I clocked in right now? ───────────
@router.get("/status", response_model=AttendanceStatus)
def get_today_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = get_employee_or_error(current_user, db)
    today = date.today()

    record = db.query(Attendance).filter(
        and_(
            Attendance.employee_id == employee.id,
            Attendance.date == today
        )
    ).first()

    if not record:
        return AttendanceStatus(is_clocked_in=False, record=None)

    is_clocked_in = record.clock_out is None
    return AttendanceStatus(is_clocked_in=is_clocked_in, record=record)


# ── MY ATTENDANCE HISTORY ─────────────────────────────────
@router.get("/my-history", response_model=List[AttendanceResponse])
def get_my_history(
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = get_employee_or_error(current_user, db)

    query = db.query(Attendance).filter(
        Attendance.employee_id == employee.id
    )

    # filter by month/year if provided
    if month and year:
        query = query.filter(
            and_(
                extract("month", Attendance.date) == month,
                extract("year", Attendance.date) == year
            )
        )

    records = query.order_by(Attendance.date.desc()).all()
    return records


# ── ALL ATTENDANCE — HR/Admin only ────────────────────────
@router.get("/all", response_model=List[AttendanceResponse])
def get_all_attendance(
    month: int = None,
    year: int = None,
    employee_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.hr)
    )
):
    query = db.query(Attendance)

    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)

    if month and year:
        query = query.filter(
            and_(
                extract("month", Attendance.date) == month,
                extract("year", Attendance.date) == year
            )
        )

    records = query.order_by(Attendance.date.desc()).all()
    return records


# ── EXPORT ATTENDANCE AS CSV — HR/Admin only ──────────────
@router.get("/export/csv")
def export_attendance_csv(
    month: Optional[int] = Query(default=None),
    year: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr)),
):
    query = db.query(Attendance)

    if month and year:
        query = query.filter(
            and_(
                extract("month", Attendance.date) == month,
                extract("year", Attendance.date) == year,
            )
        )

    records = query.order_by(Attendance.date.asc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Employee", "Date", "Clock In", "Clock Out",
        "Hours Worked", "Note",
    ])
    for rec in records:
        writer.writerow([
            rec.id,
            f"{rec.employee.first_name} {rec.employee.last_name}",
            rec.date,
            rec.clock_in.strftime("%H:%M:%S") if rec.clock_in else "",
            rec.clock_out.strftime("%H:%M:%S") if rec.clock_out else "",
            rec.hours_worked if rec.hours_worked is not None else "",
            rec.note or "",
        ])

    period = f"_{year}_{str(month).zfill(2)}" if month and year else ""
    csv_bytes = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance{period}.csv"},
    )


# ── TODAY'S PRESENT EMPLOYEES — HR/Admin only ─────────────
@router.get("/today", response_model=List[AttendanceResponse])
def get_today_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.hr)
    )
):
    today = date.today()
    records = db.query(Attendance).filter(
        Attendance.date == today
    ).all()
    return records