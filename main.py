from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="HRMS API")

# register the auth router
app.include_router(auth.router)


@app.get("/")
def root():
    return {"message": "HRMS API is running"}