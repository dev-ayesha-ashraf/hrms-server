from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.token import decode_access_token

# this tells FastAPI: "to get a token, go to /auth/login"
# it also knows how to extract the Bearer token from request headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:

    # define the error we'll raise if anything goes wrong
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # decode the token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    # get the email we stored inside the token
    email: str = payload.get("sub")
    if email is None:
        raise credentials_error

    # find the user in DB
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_error

    return user