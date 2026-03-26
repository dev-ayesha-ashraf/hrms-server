from passlib.context import CryptContext

# tells passlib to use bcrypt as the hashing algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    # turns "mypassword123" into "$2b$12$abc123..." (unreadable hash)
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # checks if a plain password matches a stored hash
    # returns True or False
    return pwd_context.verify(plain_password, hashed_password)