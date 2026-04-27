from fastapi import APIRouter
from app.api.v1 import auth, time_entries, companies, timesheets

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(time_entries.router)
api_router.include_router(companies.router)
api_router.include_router(timesheets.router)
