import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from services.websockets_manager import manager


router = APIRouter(tags=["WebSockets"])
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


@router.websocket("/ws/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await manager.connect(websocket, game_id)
    # Yurie: send an immediate handshake message so the HTML test client shows that
    # the socket is alive even before any code execution result is published.
    await websocket.send_json(
        {
            "type": "connection",
            "status": "connected",
            "game_id": game_id,
            "message": "WebSocket connected successfully.",
        }
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)


async def listen_to_redis_pubsub():
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()

    # Yurie: subscribe to the exact `game_updates:{game_id}` pattern used by the
    # background task publisher, so each game's results can be routed correctly.
    await pubsub.psubscribe("game_updates:*")

    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            channel = message["channel"]
            # Yurie: split only once so the right-hand side stays as the game_id.
            game_id = channel.split(":", 1)[1]
            data = json.loads(message["data"])
            await manager.broadcast_to_game(data, game_id)

@router.websocket("/ws/room/{room_code}")
async def room_websocket_endpoint(websocket: WebSocket, room_code: str):
    await manager.connect(websocket, room_code)

    try:
        while True:
            data = await websocket.receive_text()
    except:
        manager.disconnect(websocket, room_code)