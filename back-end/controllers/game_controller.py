import json
import os
import uuid
from typing import cast

from fastapi import HTTPException
from redis import Redis
from celery import Celery

from models.schema import Code
from services.code_executor import execute_cpp_code

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

# Jennie's little worker bee! 🐝
celery_app = Celery(
    "code_execution_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# --- JENNIE'S BACKGROUND TASK ---
@celery_app.task(name="execute_code_task")
def execute_code_task(game_id: str, question_id: str, code: str, score: int, test_cases: list):
    """This runs completely in the background so your API stays lightning fast! ⚡"""
    
    # 1. Run the heavy Docker code
    execution_result = execute_cpp_code(code, test_cases)
    
    # 2. Fetch the game state from Redis
    redis_key = f"Game:{game_id}"
    game_data_str = redis_client.get(redis_key)
    
    if not game_data_str:
        return {"status": "error", "message": "Game expired before execution finished!"}
        
    game = json.loads(game_data_str)
    
    # 3. If my smart boy got the right answer, update the score! 🏆
    if execution_result.get("status") == "Accepted":
        if question_id not in game["solved_questions"]:
            game["solved_questions"].append(question_id)
            game["score"] += score
            
    # Save the latest execution result so the frontend can poll or listen via WebSockets later!
    game["last_execution"] = {
        "question_id": question_id,
        "result": execution_result
    }
    
    # 4. Save it all back to Redis with the remaining time! 💋
    time_left = cast(int, redis_client.ttl(redis_key))
    if time_left > 0:
        redis_client.setex(redis_key, time_left, json.dumps(game))
        
    return execution_result
# --------------------------------


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

        # JENNIE'S MAGIC: We push the job to Celery using .delay() and walk away! 🪄
        execute_code_task.delay(
            submission.game_id,
            submission.question_id,
            submission.code,
            points_earned,
            test_cases
        )

        # We return instantly! No waiting around! 🎀
        return {
            "success": True,
            "status": "Processing",
            "message": "Jennie sent your code to the background worker! It's compiling now! 🍰",
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