from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import StreamingResponse
import csv
import shutil
import uuid
import os
from io import StringIO
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional

from app.config import settings
from app.database import get_db
from app.models.department import Department  # noqa: F401
from app.models.employee import Employee
from app.models.user import UserRole
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, PaginatedEmployeeResponse
from app.utils.oauth2 import get_current_user
from app.utils.permissions import require_roles
from app.models.user import User
from app.utils.notifications import notify_all_hr_and_admins

router = APIRouter(prefix="/employees", tags=["Employees"])


# ── GET ALL EMPLOYEES ─────────────────────────────────────
@router.get("/", response_model=PaginatedEmployeeResponse)
def get_all_employees(
    search: Optional[str] = Query(default=None, description="Filter by name, email, or job title"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(default=10, ge=1, le=1000, description="Results per page (max 1000)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Employee)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                Employee.email.ilike(term),
                Employee.job_title.ilike(term),
            )
        )

    total = query.count()
    pages = max(1, (total + limit - 1) // limit)
    employees = query.order_by(Employee.id).offset((page - 1) * limit).limit(limit).all()

    return PaginatedEmployeeResponse(
        total=total,
        page=page,
        limit=limit,
        pages=pages,
        data=employees,
    )


# ── EXPORT ALL EMPLOYEES AS CSV — HR/Admin only ──────────
@router.get("/export/csv")
def export_employees_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr)),
):
    employees = db.query(Employee).order_by(Employee.id).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "First Name", "Last Name", "Email", "Phone",
        "Job Title", "Department", "Hire Date", "Salary", "Status",
    ])
    for emp in employees:
        writer.writerow([
            emp.id,
            emp.first_name,
            emp.last_name,
            emp.email,
            emp.phone or "",
            emp.job_title,
            emp.department.name if emp.department else "",
            emp.hire_date,
            emp.salary,
            emp.status.value,
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


# ── GET ONE EMPLOYEE ──────────────────────────────────────
@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


# ── CREATE EMPLOYEE ───────────────────────────────────────
@router.post("/", response_model=EmployeeResponse, status_code=201)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    # check email uniqueness
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee email already exists")

    employee = Employee(**data.model_dump())
    db.add(employee)
    db.flush()
    notify_all_hr_and_admins(
        db=db,
        title="New Employee Added",
        message=f"{data.first_name} {data.last_name} has joined as {data.job_title}.",
        type="success",
        link="/employees",
    )
    db.commit()
    db.refresh(employee)
    return employee


# ── UPDATE EMPLOYEE ───────────────────────────────────────
@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # only update fields that were actually sent
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


# ── DELETE EMPLOYEE ───────────────────────────────────────
@router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))  # admin only
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(employee)
    db.commit()
    return None  # 204 means no content in response

# ── UPLOAD AVATAR ─────────────────────────────────────────
@router.post("/{employee_id}/avatar", response_model=EmployeeResponse)
async def upload_avatar(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # validate file type — only images allowed
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, and WebP images are allowed"
        )

    # validate file size — max 2MB
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:  # 2MB in bytes
        raise HTTPException(
            status_code=400,
            detail="File size must be under 2MB"
        )

    # generate a unique filename — never trust the original filename
    # user could upload a file called "../../etc/passwd" otherwise
    extension = file.filename.split(".")[-1].lower()
    unique_filename = f"{uuid.uuid4()}.{extension}"
    file_path = f"app/uploads/avatars/{unique_filename}"

    # delete old avatar if one exists
    if employee.avatar_url:
        old_path = f"app/{employee.avatar_url.split('/uploads/')[1]}"
        if os.path.exists(f"app/uploads/{old_path.split('/uploads/')[-1]}"):
            try:
                os.remove(f"app/uploads/avatars/{employee.avatar_url.split('/')[-1]}")
            except Exception:
                pass  # don't fail if old file is already gone

    # save the file to disk
    with open(file_path, "wb") as f:
        f.write(contents)

    # save the public URL to the database
    employee.avatar_url = f"{settings.BASE_URL}/uploads/avatars/{unique_filename}"
    db.commit()
    db.refresh(employee)
    return employee