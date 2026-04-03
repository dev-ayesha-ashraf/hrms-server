from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, distinct, and_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest, LeaveStatus
from app.models.payroll import Payroll
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardStatsResponse
from app.utils.cache import cache
from app.utils.permissions import require_roles

_CACHE_KEY = "dashboard_stats"

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr)),
):
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    today = date.today()

    total_employees = db.query(func.count(Employee.id)).scalar() or 0

    present_today = (
        db.query(func.count(distinct(Attendance.employee_id)))
        .filter(Attendance.date == today)
        .scalar()
        or 0
    )

    on_leave = (
        db.query(func.count(distinct(LeaveRequest.employee_id)))
        .filter(
            and_(
                LeaveRequest.status == LeaveStatus.approved,
                LeaveRequest.from_date <= today,
                LeaveRequest.to_date >= today,
            )
        )
        .scalar()
        or 0
    )

    # Group leave requests by status first, then read pending from the grouped result.
    leave_status_counts = (
        db.query(LeaveRequest.status, func.count(LeaveRequest.id).label("count"))
        .group_by(LeaveRequest.status)
        .all()
    )
    pending_requests = 0
    for status, count in leave_status_counts:
        if status == LeaveStatus.pending:
            pending_requests = count
            break

    total_payroll_this_month = (
        db.query(func.coalesce(func.sum(Payroll.net_pay), 0))
        .filter(
            and_(
                Payroll.month == today.month,
                Payroll.year == today.year,
            )
        )
        .scalar()
    )

    result = DashboardStatsResponse(
        total_employees=total_employees,
        present_today=present_today,
        on_leave=on_leave,
        pending_requests=pending_requests,
        total_payroll_this_month=float(total_payroll_this_month or 0),
    )
    cache.set(_CACHE_KEY, result, ttl=settings.DASHBOARD_CACHE_TTL)
    return result