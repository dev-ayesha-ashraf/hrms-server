from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth

app = FastAPI(title="HRMS API")

# allow the frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your Next.js URL
    allow_credentials=True,
    allow_methods=["*"],    # allow GET, POST, PUT, DELETE etc.
    allow_headers=["*"],    # allow Authorization header etc.
)

app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "HRMS API is running"}