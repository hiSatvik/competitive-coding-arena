from datetime import datetime, timezone
from fastapi import Request
from passlib.context import CryptContext
from middleware.auth_middleware import (
    ensure_login_credentials_are_valid,
    ensure_user_does_not_exist,
)
from models.connect import connect
from models.schema import UserCreate, UserLogin

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def register_user(payload: UserCreate, request: Request) -> dict:
    ensure_user_does_not_exist(payload.email, payload.username)

    hashed_password = pwd_context.hash(payload.password)
    now = datetime.now(timezone.utc)
    result = connect.db.users.insert_one(
        {
            "username": payload.username,
            "email": payload.email,
            "hashed_password": hashed_password,
            "created_at": now,
            "updated_at": now,
        }
    )

    request.session["user_id"] = str(result.inserted_id)
    request.session["username"] = payload.username

    return {
        "message": "Registration successful",
        "user": {
            "id": str(result.inserted_id),
            "username": payload.username,
            "email": payload.email,
        },
    }

def login_user(payload: UserLogin, request: Request) -> dict:
    user = ensure_login_credentials_are_valid(payload.email, payload.password, pwd_context)

    request.session["user_id"] = str(user["_id"])
    request.session["username"] = user["username"]

    return {
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
        },
    }