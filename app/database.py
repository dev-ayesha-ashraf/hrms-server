from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get the database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# The "engine" is the actual connection to PostgreSQL
engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})

# Every database operation happens inside a "session"
# Think of it like opening and closing a conversation with the DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All models will inherit from this Base class
Base = declarative_base()


# This is a "dependency" — FastAPI will call this for every request
# It opens a DB session, gives it to the route, then closes it
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()