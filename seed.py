import sys
import os

# make sure Python can find your app folder
sys.path.append(os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.utils.hashing import hash_password


def seed_users():
    db = SessionLocal()

    # list of users to create
    users_to_seed = [
        {
            "name": "Admin User",
            "email": "admin@hrms.com",
            "password": "admin123",
            "role": UserRole.admin,
        },
        {
            "name": "HR Manager",
            "email": "hr@hrms.com",
            "password": "hr123456",
            "role": UserRole.hr,
        },
        {
            "name": "John Employee",
            "email": "employee@hrms.com",
            "password": "emp12345",
            "role": UserRole.employee,
        },
    ]

    for user_data in users_to_seed:
        # check if user already exists — don't create duplicates
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"  skipping {user_data['email']} — already exists")
            continue

        user = User(
            name=user_data["name"],
            email=user_data["email"],
            hashed_password=hash_password(user_data["password"]),
            role=user_data["role"],
        )
        db.add(user)
        print(f"  created {user_data['role'].value}: {user_data['email']}")

    db.commit()
    db.close()
    print("\nSeeding complete.")


if __name__ == "__main__":
    seed_users()

    from app.models.employee import Employee, EmploymentStatus
from app.models.department import Department
from datetime import date


def seed_departments(db):
    departments = [
        {"name": "Engineering", "description": "Software and infrastructure"},
        {"name": "Human Resources", "description": "People operations"},
        {"name": "Finance", "description": "Accounting and payroll"},
    ]
    created = []
    for dept_data in departments:
        existing = db.query(Department).filter(
            Department.name == dept_data["name"]
        ).first()
        if existing:
            print(f"  skipping department {dept_data['name']} — already exists")
            created.append(existing)
            continue
        dept = Department(**dept_data)
        db.add(dept)
        db.flush()  # flush to get the id without committing
        created.append(dept)
        print(f"  created department: {dept_data['name']}")
    db.commit()
    return created

def seed_employees(db, departments):
    # fetch users to link them
    admin_user = db.query(User).filter(User.email == "admin@hrms.com").first()
    hr_user = db.query(User).filter(User.email == "hr@hrms.com").first()
    emp_user = db.query(User).filter(User.email == "employee@hrms.com").first()

    employees = [
        {
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah@hrms.com",
            "job_title": "Senior Engineer",
            "department_id": departments[0].id,
            "hire_date": date(2022, 3, 15),
            "salary": 95000.00,
            "status": EmploymentStatus.active,
            "user_id": admin_user.id if admin_user else None,
        },
        {
            "first_name": "Mike",
            "last_name": "Ross",
            "email": "mike@hrms.com",
            "job_title": "HR Specialist",
            "department_id": departments[1].id,
            "hire_date": date(2021, 7, 1),
            "salary": 65000.00,
            "status": EmploymentStatus.active,
            "user_id": hr_user.id if hr_user else None,
        },
        {
            "first_name": "John",
            "last_name": "Employee",
            "email": "john@hrms.com",
            "job_title": "Junior Developer",
            "department_id": departments[0].id,
            "hire_date": date(2023, 1, 10),
            "salary": 55000.00,
            "status": EmploymentStatus.active,
            "user_id": emp_user.id if emp_user else None,
        },
    ]

    for emp_data in employees:
        existing = db.query(Employee).filter(
            Employee.email == emp_data["email"]
        ).first()
        if existing:
            # update user_id if not already set
            if not existing.user_id and emp_data.get("user_id"):
                existing.user_id = emp_data["user_id"]
                db.commit()
            print(f"  skipping {emp_data['email']} — already exists")
            continue
        emp = Employee(**emp_data)
        db.add(emp)
        print(f"  created employee: {emp_data['first_name']} {emp_data['last_name']}")
    db.commit()
# update your main block at the bottom:
if __name__ == "__main__":
    db = SessionLocal()
    print("\nSeeding users...")
    seed_users()
    print("\nSeeding departments...")
    depts = seed_departments(db)
    print("\nSeeding employees...")
    seed_employees(db, depts)
    db.close()
    print("\nAll done.")