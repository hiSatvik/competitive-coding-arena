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


@router.websocket("/ws/room/{room_code}")
async def room_websocket_endpoint(websocket: WebSocket, room_code: str):
    await manager.connect(websocket, room_code)
    await websocket.send_json(
        {
            "type": "connection",
            "status": "connected",
            "room_code": room_code,
            "message": "Room WebSocket connected successfully.",
        }
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)


async def listen_to_redis_pubsub():
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()

    await pubsub.psubscribe("game_updates:*")
    await pubsub.psubscribe("room_updates:*")

    async for message in pubsub.listen():
        if message["type"] != "pmessage":
            continue

        channel = message["channel"]
        data = json.loads(message["data"])

        if channel.startswith("game_updates:"):
            game_id = channel.split(":", 1)[1]
            await manager.broadcast_to_game(data, game_id)
        elif channel.startswith("room_updates:"):
            room_code = channel.split(":", 1)[1]
            await manager.broadcast_to_game(data, room_code)
