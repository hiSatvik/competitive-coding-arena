from fastapi import FastAPI
from models.connect import connect
from router.auth_router import router as auth_router
from starlette.middleware.sessions import SessionMiddleware
from router.game_router import router as game_router

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="Not_so_secret_key", 
session_cookie="session_id", max_age=604800, same_site="lax", https_only=False)

app.include_router(auth_router)
app.include_router(game_router)

@app.get("/")
def root():
    return {"message": "Hello World"}