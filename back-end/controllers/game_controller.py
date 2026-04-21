import json
import os
import uuid
from typing import cast
import random
import string
import time

from celery import Celery
from fastapi import HTTPException
from redis import Redis

from models.schema import Code
from services.code_executor import execute_cpp_code

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

celery_app = Celery(
    "code_execution_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)


def _publish_execution_update(game_id: str, payload: dict) -> None:
    redis_client.publish(f"game_updates:{game_id}", json.dumps(payload))


@celery_app.task(name="execute_code_task")
def execute_code_task(game_id: str, question_id: str, code: str, score: int, test_cases: list):
    execution_result = execute_cpp_code(code, test_cases)

    redis_key = f"Game:{game_id}"
    game_data_str = redis_client.get(redis_key)

    if not game_data_str:
        result = {
            "success": False,
            "status": "error",
            "message": "Game expired before execution finished!",
            "question_id": question_id,
        }
        _publish_execution_update(game_id, result)
        return result

    game = json.loads(game_data_str)

    if execution_result.get("status") == "Accepted" and question_id not in game["solved_questions"]:
        game["solved_questions"].append(question_id)
        game["score"] += score

    game["last_execution"] = {
        "question_id": question_id,
        "result": execution_result,
    }

    time_left = cast(int, redis_client.ttl(redis_key))
    if time_left > 0:
        redis_client.setex(redis_key, time_left, json.dumps(game))

    result_payload = {
        "success": execution_result.get("status") == "Accepted",
        "status": execution_result.get("status"),
        "question_id": question_id,
        "total_score": game["score"],
        "solved_questions": game["solved_questions"],
        "execution_details": execution_result,
    }

    _publish_execution_update(game_id, result_payload)
    return result_payload


dummy_questions = [
    {
        "id": "q1",
        "title": "Add Two Numbers",
        "description": "Write a program that reads two space-separated integers from standard input and prints their sum.",
        "test_cases": [
            {"input": "5 7\n", "expected_output": "12"},
            {"input": "10 20\n", "expected_output": "30"},
            {"input": "-5 5\n", "expected_output": "0"},
        ],
    },
    {
        "id": "q2",
        "title": "Multiply by Two",
        "description": "Write a program that reads a single integer from standard input and prints double its value.",
        "test_cases": [
            {"input": "4\n", "expected_output": "8"},
            {"input": "0\n", "expected_output": "0"},
            {"input": "-15\n", "expected_output": "-30"},
        ],
    },
    {
        "id": "q3",
        "title": "Find the Maximum",
        "description": "Write a program that reads three space-separated integers and prints the largest one.",
        "test_cases": [
            {"input": "1 5 3\n", "expected_output": "5"},
            {"input": "10 10 10\n", "expected_output": "10"},
            {"input": "-1 -5 -3\n", "expected_output": "-1"},
        ],
    },
]


class GameLogic:
    def __init__(self, username: str):
        self.game_id = str(uuid.uuid4())
        self.username = username
        self.questions = dummy_questions

        game_data = {
            "game_id": self.game_id,
            "username": self.username,
            "score": 0,
            "status": "in_progress",
            "questions": self.questions,
            "solved_questions": [],
        }

        redis_client.setex(f"Game:{self.game_id}", 1800, json.dumps(game_data))

    def start_game_controller(self):
        return {
            "game_id": self.game_id,
            "questions": self.questions,
            "username": self.username,
            "message": "Good luck!",
        }

    @staticmethod
    def submit_code_controller(submission: Code, username: str):
        redis_key = f"Game:{submission.game_id}"
        game_data_str = cast(str | None, redis_client.get(redis_key))

        if not game_data_str:
            raise HTTPException(status_code=404, detail="Game not found.")

        game = json.loads(game_data_str)

        if game["username"] != username:
            raise HTTPException(status_code=403, detail="You cannot submit for this game.")

        if game["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="This game session is already over.")

        question = next(
            (q for q in game["questions"] if q.get("id") == submission.question_id),
            None,
        )
        if not question:
            raise HTTPException(status_code=404, detail="Question not found in this session.")

        if submission.question_id in game["solved_questions"]:
            return {"status": "Already Solved", "message": "You already solved this question."}

        test_cases = question.get("test_cases", [])
        points_earned = submission.score or 10

        execute_code_task.delay(
            submission.game_id,
            submission.question_id,
            submission.code,
            points_earned,
            test_cases,
        )

        # the final result is delivered later through Redis pubsub -> WebSocket.
        return {
            "success": True,
            "status": "Processing",
            "message": "Code sent to the background worker.",
        }

    @staticmethod
    def get_result_controller(game_id: str, username: str):
        redis_key = f"Game:{game_id}"
        game_data_str = cast(str | None, redis_client.get(redis_key))

        if not game_data_str:
            raise HTTPException(status_code=404, detail="Game not found!")

        game = json.loads(game_data_str)
        if game["username"] != username:
            raise HTTPException(status_code=403, detail="You cannot access this game result.")

        game["status"] = "completed"

        time_left = cast(int, redis_client.ttl(redis_key))
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(game))

        return {
            "user": game["username"],
            "final_score": game["score"],
            "status": game["status"],
            "solved_questions": game["solved_questions"],
            "message": "Game over!",
        }
    
    @staticmethod
    def create_room_controller(username: str):
        room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

        question = dummy_questions

        room_data = {
            "room_code": room_code,
            "status": "waiting",
            "players": [username],
            "questions": question,
            "start_time": None
        }

        redis_client.setex(f"Room:{room_code}", 1800, json.dumps(room_data))

        return {
            "room_code": room_code,
            "username": username,
            "questions": question,
            "message": f"Room created successfully! Share {room_code} to invite users. 🎀"
        }
    
    @staticmethod
    def join_room_controller(room_code: str, username: str):
        redis_key = f"Room:{room_code}" 

        room_data_str = redis_client.get(redis_key)

        # If it's completely missing from Redis
        if not room_data_str:
            raise HTTPException(status_code=404, detail="Oops! Room not found. 🥺")
        
        room = json.loads(room_data_str)

        # Check if the game has already started before letting them in!
        if room["status"] != "waiting":
            raise HTTPException(status_code=400, detail="Oh no! The game has already started! 🏃‍♂️")

        if username not in room["players"]:
            room["players"].append(username)

            time_left = cast(int, redis_client.ttl(redis_key))

            if time_left > 0:
                redis_client.setex(redis_key, time_left, json.dumps(room))

        return {
            "room_code": room_code,
            "username": username,
            "players": room["players"],
            "questions": room["questions"],
            "message": "Welcome to the party!"
        }
    
    @staticmethod
    def start_room_controller(room_code: str):
        redis_key = f"Room:{room_code}"
        room_data_str = redis_client.get(redis_key)
        
        if not room_data_str:
            raise HTTPException(status_code=404, detail="Oopsie! Room not found. 🥺")
            
        room = json.loads(room_data_str)
        
        if room["status"] != "waiting":
            raise HTTPException(status_code=400, detail="The timer is already ticking! 🏃‍♂️")
            
        # Start the clock!
        room["status"] = "in_progress"
        room["start_time"] = int(time.time()) # Record the exact second it started
        
        # Save the updated status back to Redis
        time_left = cast(int, redis_client.ttl(redis_key))
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(room))
            
        # Jennie's special trick: Broadcast to the WebSocket that the game has started!
        redis_client.publish(f"room_updates:{room_code}", json.dumps({
            "type": "GAME_STARTED",
            "start_time": room["start_time"],
            "message": "Buckle up, developers! The match has begun! 🚀"
        }))
        
        return {"message": "Game started successfully!"}