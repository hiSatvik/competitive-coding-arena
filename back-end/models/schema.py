from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    username: str
    email: str
    password: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class UserInDB(User):
    id: ObjectId
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class UserInDB(User):
    id: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()