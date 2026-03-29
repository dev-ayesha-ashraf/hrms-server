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