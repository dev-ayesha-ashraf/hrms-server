from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse
from app.utils.hashing import hash_password, verify_password
from app.utils.token import create_access_token
from app.utils.oauth2 import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(user_data.password)
    new_user = User(name=user_data.name, email=user_data.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ── NEW: LOGIN ──────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):

    # 1. find the user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    # 2. if no user OR wrong password → same error (don't reveal which one)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 3. create the token — store email and role inside it
    token = create_access_token(data={
        "sub": user.email,
        "role": user.role
    })

    return {"access_token": token, "token_type": "bearer"}


# ── NEW: GET CURRENT USER ───────────────────────────────
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    # get_current_user already did all the work
    # if we reach here, the user is authenticated
    return current_user