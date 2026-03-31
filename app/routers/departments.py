from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.utils.oauth2 import get_current_user
from app.utils.permissions import require_roles
from app.models.user import User, UserRole

router = APIRouter(prefix="/departments", tags=["Departments"])


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    employee_count: int = 0     # ← computed field, not in DB

    class Config:
        from_attributes = True


# ── GET ALL ───────────────────────────────────────────────
@router.get("/", response_model=List[DepartmentResponse])
def get_all_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # join departments with employees and count — one query, not N queries
    results = (
        db.query(
            Department,
            func.count(Employee.id).label("employee_count")
        )
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.id)
        .all()
    )

    # build response manually because we have a computed field
    response = []
    for dept, count in results:
        response.append(DepartmentResponse(
            id=dept.id,
            name=dept.name,
            description=dept.description,
            employee_count=count
        ))
    return response


# ── CREATE ────────────────────────────────────────────────
@router.post("/", response_model=DepartmentResponse, status_code=201)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    existing = db.query(Department).filter(
        Department.name == data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department already exists")

    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # return with employee_count = 0 (brand new department)
    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        description=dept.description,
        employee_count=0
    )


# ── UPDATE ────────────────────────────────────────────────
@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.hr))
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dept, field, value)

    db.commit()
    db.refresh(dept)

    # recount employees for this department
    count = db.query(func.count(Employee.id)).filter(
        Employee.department_id == dept_id
    ).scalar()

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        description=dept.description,
        employee_count=count or 0
    )


# ── DELETE ────────────────────────────────────────────────
@router.delete("/{dept_id}", status_code=204)
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    # check if department has employees — don't delete if it does
    employee_count = db.query(func.count(Employee.id)).filter(
        Employee.department_id == dept_id
    ).scalar()

    if employee_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {employee_count} employee(s) still in this department"
        )

    db.delete(dept)
    db.commit()
    return None