from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.routers import (
    auth,
    employees,
    departments,
    attendance,
    payroll,
    leave_reaquests as leave_requests,
    dashboard,
)

app = FastAPI(title="HRMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

@app.get("/")
def root():
    return {"message": "HRMS API is running"}