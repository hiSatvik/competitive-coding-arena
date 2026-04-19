from fastapi import APIRouter, Request
from controllers.auth_controller import login_user, register_user
from models.schema import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(payload: UserCreate, request: Request):
    return register_user(payload, request)

@router.post("/login")
def login(payload: UserLogin, request: Request):
    return login_user(payload, request)