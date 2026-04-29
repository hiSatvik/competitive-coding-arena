from fastapi import FastAPI
from models.connect import connect
from router.auth_router import router as auth_router
from starlette.middleware.sessions import SessionMiddleware
from router.game_router import router as game_router
import asyncio
from contextlib import asynccontextmanager
from router.websockets_router import router as websocket_router, listen_to_redis_pubsub
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start redis lister in the background
    pubsub_task = asyncio.create_task(listen_to_redis_pubsub())
    yield

    #Clean up
    pubsub_task.cancel()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="Not_so_secret_key", 
session_cookie="session_id", max_age=604800, same_site="lax", https_only=False)

app.include_router(auth_router)
app.include_router(game_router)
app.include_router(websocket_router)

@app.get("/")
def root():
    return {"message": "Hello World"}
