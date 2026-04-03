from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import os

from app.config import settings
from app.routers import (
    auth,
    employees,
    departments,
    attendance,
    payroll,
    notifications,
    leave_reaquests as leave_requests,
    dashboard,
)

# Rate limiter — applied per-route with @limiter.limit(settings.RATE_LIMIT)
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

app = FastAPI(title="HRMS API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve everything in app/uploads as static files
# visiting /uploads/avatars/filename.jpg returns the file
os.makedirs("app/uploads/avatars", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(departments.router)
app.include_router(leave_requests.router)
app.include_router(attendance.router)
app.include_router(payroll.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)

@app.get("/")
def root():
    return {"message": "HRMS API is running"}