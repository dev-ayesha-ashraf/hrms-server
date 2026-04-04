from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
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

app = FastAPI(
    title="HRMS API",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": False,
        "additionalQueryStringParams": {},
    },
    swagger_ui_parameters={"persistAuthorization": True},
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "https://hrms-client-liard.vercel.app", 
    "http://localhost:3000" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          
    allow_credentials=True,
    allow_methods=["*"],            # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],            # allow all headers
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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    # Remove client_id / client_secret from the password flow security scheme
    for scheme in schema.get("components", {}).get("securitySchemes", {}).values():
        if scheme.get("type") == "oauth2":
            for flow in scheme.get("flows", {}).values():
                flow.pop("clientId", None)
                flow.pop("clientSecret", None)
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi

@app.get("/")
def root():
    return {"message": "HRMS API is running"}