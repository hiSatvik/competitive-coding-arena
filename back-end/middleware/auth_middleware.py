from fastapi import HTTPException, status
from models.connect import connect

def ensure_user_does_not_exist(email: str, username: str) -> None:
    existing_user = connect.db.users.find_one(
        {"$or": [{"email": email}, {"username": username}]}
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or username already exists",
        )


def ensure_login_credentials_are_valid(email: str, password: str, pwd_context):
    user = connect.db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not pwd_context.verify(password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return user
