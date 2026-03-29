from passlib.context import CryptContext

# Use bcrypt_sha256 to avoid bcrypt's 72-byte input limit.
# Keep plain bcrypt for backward compatibility with any existing hashes.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    # turns "mypassword123" into "$2b$12$abc123..." (unreadable hash)
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # checks if a plain password matches a stored hash
    # returns True or False
    return pwd_context.verify(plain_password, hashed_password)