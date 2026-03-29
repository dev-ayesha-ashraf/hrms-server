from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, employees   # ← add employees

app = FastAPI(title="HRMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)   # ← add this

@app.get("/")
def root():
    return {"message": "HRMS API is running"}