from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract
from typing import List
from datetime import datetime
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.utils.pdf_generator import generate_payslip_pdf

from app.database import get_db
from app.models.payroll import Payroll
from app.models.employee import Employee, EmploymentStatus
from app.models.attendance import Attendance
from app.models.user import User, UserRole
from app.schemas.payroll import (
    PayrollGenerate,
    PayrollBulkGenerate,
    PayrollMarkPaid,
    PayrollResponse
)
from app.utils.oauth2 import get_current_user
from app.utils.permissions import require_roles
from app.utils.payroll_calculator import (
    calculate_payroll,
    get_working_days
)

router = APIRouter(prefix="/payroll", tags=["Payroll"])


def get_days_present(employee_id: int, month: int, year: int, db: Session) -> int:
    """Count days the employee was present (clocked out) in a month."""
    count = db.query(Attendance).filter(
        and_(
            Attendance.employee_id == employee_id,
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
            Attendance.clock_out != None   # only completed days
        )
    ).count()
    return count


def get_overtime_hours(employee_id: int, month: int, year: int, db: Session) -> float:
    """
    Count hours worked beyond 8 hours per day as overtime.
    Standard day = 8 hours. Anything above = overtime.
    """
    records = db.query(Attendance).filter(
        and_(
            Attendance.employee_id == employee_id,
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
            Attendance.clock_out != None,
            Attendance.hours_worked != None
        )
    ).all()

    overtime = 0.0
    for rec in records:
        hours = float(rec.hours_worked)
        if hours > 8:
            overtime += hours - 8  # only the extra hours

    return round(overtime, 2)


# ── GENERATE FOR ONE EMPLOYEE ─────────────────────────────
@router.post("/generate/{employee_id}", response_model=PayrollResponse)
def generate_payroll_for_employee(
    employee_id: int,
    data: PayrollGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # check if payroll already generated for this month
    existing = db.query(Payroll).filter(
        and_(
            Payroll.employee_id == employee_id,
            Payroll.month == data.month,
            Payroll.year == data.year
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Payroll already generated for this employee for {data.month}/{data.year}"
        )

    # gather attendance data
    working_days = get_working_days(data.year, data.month)
    days_present = get_days_present(employee_id, data.month, data.year, db)
    days_absent = working_days - days_present
    overtime_hours = get_overtime_hours(employee_id, data.month, data.year, db)

    # use provided overtime/bonus overrides if given
    final_overtime = data.overtime_hours if data.overtime_hours else overtime_hours
    final_bonus = data.performance_bonus if data.performance_bonus else 0

    # run the calculation engine
    result = calculate_payroll(
        annual_salary=float(employee.salary),
        days_present=days_present,
        working_days_in_month=working_days,
        overtime_hours=final_overtime,
        performance_bonus=final_bonus,
    )

    payroll = Payroll(
        employee_id=employee_id,
        month=data.month,
        year=data.year,
        base_salary=result.base_salary,
        overtime_bonus=result.overtime_bonus,
        performance_bonus=result.performance_bonus,
        gross_salary=result.gross_salary,
        income_tax=result.income_tax,
        social_security=result.social_security,
        total_deductions=result.total_deductions,
        net_pay=result.net_pay,
        days_present=days_present,
        days_absent=days_absent,
        overtime_hours=final_overtime,
        generated_by_id=current_user.id,
    )

    db.add(payroll)
    db.commit()
    db.refresh(payroll)
    return payroll


# ── GENERATE FOR ALL ACTIVE EMPLOYEES ────────────────────
@router.post("/generate-bulk", response_model=List[PayrollResponse])
def generate_payroll_bulk(
    data: PayrollBulkGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    # get all active employees
    employees = db.query(Employee).filter(
        Employee.status == EmploymentStatus.active
    ).all()

    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found")

    results = []
    skipped = []

    for employee in employees:
        # skip if already generated
        existing = db.query(Payroll).filter(
            and_(
                Payroll.employee_id == employee.id,
                Payroll.month == data.month,
                Payroll.year == data.year
            )
        ).first()

        if existing:
            skipped.append(employee.id)
            continue

        working_days = get_working_days(data.year, data.month)
        days_present = get_days_present(employee.id, data.month, data.year, db)
        days_absent = working_days - days_present
        overtime_hours = get_overtime_hours(employee.id, data.month, data.year, db)

        result = calculate_payroll(
            annual_salary=float(employee.salary),
            days_present=days_present,
            working_days_in_month=working_days,
            overtime_hours=overtime_hours,
        )

        payroll = Payroll(
            employee_id=employee.id,
            month=data.month,
            year=data.year,
            base_salary=result.base_salary,
            overtime_bonus=result.overtime_bonus,
            performance_bonus=result.performance_bonus,
            gross_salary=result.gross_salary,
            income_tax=result.income_tax,
            social_security=result.social_security,
            total_deductions=result.total_deductions,
            net_pay=result.net_pay,
            days_present=days_present,
            days_absent=days_absent,
            overtime_hours=overtime_hours,
            generated_by_id=current_user.id,
        )

        db.add(payroll)
        results.append(payroll)

    db.commit()
    for r in results:
        db.refresh(r)

    return results


# ── GET ALL PAYROLL FOR A MONTH ───────────────────────────
@router.get("/", response_model=List[PayrollResponse])
def get_payroll_list(
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    query = db.query(Payroll)
    if month:
        query = query.filter(Payroll.month == month)
    if year:
        query = query.filter(Payroll.year == year)
    return query.order_by(Payroll.year.desc(), Payroll.month.desc()).all()


# ── GET MY PAYROLL — employee sees their own ──────────────
@router.get("/my-payslips", response_model=List[PayrollResponse])
def get_my_payslips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(
        Employee.user_id == current_user.id
    ).first()

    if not employee:
        return []

    return (
        db.query(Payroll)
        .filter(Payroll.employee_id == employee.id)
        .order_by(Payroll.year.desc(), Payroll.month.desc())
        .all()
    )


# ── GET ONE PAYSLIP ───────────────────────────────────────
@router.get("/{payroll_id}", response_model=PayrollResponse)
def get_payslip(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payslip not found")

    # employees can only see their own
    if current_user.role == UserRole.employee:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()
        if not employee or payroll.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return payroll


# ── MARK AS PAID ──────────────────────────────────────────
@router.patch("/{payroll_id}/mark-paid", response_model=PayrollResponse)
def mark_as_paid(
    payroll_id: int,
    data: PayrollMarkPaid,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payslip not found")

    if payroll.is_paid:
        raise HTTPException(status_code=400, detail="Already marked as paid")

    payroll.is_paid = True
    payroll.paid_at = datetime.utcnow()
    if data.notes:
        payroll.notes = data.notes

    db.commit()
    db.refresh(payroll)
    return payroll

# ── DOWNLOAD PAYSLIP AS PDF ───────────────────────────────
@router.get("/{payroll_id}/pdf")
def download_payslip_pdf(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payslip not found")

    # employees can only download their own
    if current_user.role == UserRole.employee:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()
        if not employee or payroll.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # convert SQLAlchemy model to dict for the PDF generator
    payslip_dict = {
        "id": payroll.id,
        "month": payroll.month,
        "year": payroll.year,
        "employee": {
            "first_name": payroll.employee.first_name,
            "last_name": payroll.employee.last_name,
            "job_title": payroll.employee.job_title,
        },
        "base_salary": payroll.base_salary,
        "overtime_bonus": payroll.overtime_bonus,
        "performance_bonus": payroll.performance_bonus,
        "gross_salary": payroll.gross_salary,
        "income_tax": payroll.income_tax,
        "social_security": payroll.social_security,
        "total_deductions": payroll.total_deductions,
        "net_pay": payroll.net_pay,
        "days_present": payroll.days_present,
        "days_absent": payroll.days_absent,
        "overtime_hours": payroll.overtime_hours,
        "is_paid": payroll.is_paid,
        "paid_at": payroll.paid_at,
        "notes": payroll.notes,
    }

    pdf_bytes = generate_payslip_pdf(payslip_dict)

    filename = (
        f"payslip_{payroll.employee.first_name.lower()}_"
        f"{payroll.employee.last_name.lower()}_"
        f"{payroll.year}_{str(payroll.month).zfill(2)}.pdf"
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            # tells browser to download this as a file with this name
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )