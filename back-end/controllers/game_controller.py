import json
import os
import uuid

from fastapi import HTTPException
from redis import Redis

from models.schema import Code
from services.code_executor import execute_cpp_code


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

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
        game_data_str = redis_client.get(redis_key)

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
        execution_result = execute_cpp_code(submission.code, test_cases)

        if execution_result.get("status") == "Accepted":
            game["solved_questions"].append(submission.question_id)
            points_earned = submission.score or 10
            game["score"] += points_earned

            time_left = redis_client.ttl(redis_key)
            if time_left > 0:
                redis_client.setex(redis_key, time_left, json.dumps(game))

            return {
                "success": True,
                "status": "Accepted",
                "message": "All test cases passed!",
                "points_earned": points_earned,
                "total_score": game["score"],
                "execution_details": execution_result,
            }

        return {
            "success": False,
            "status": execution_result.get("status"),
            "message": "Code execution failed. Try again.",
            "execution_details": execution_result,
        }

    @staticmethod
    def get_result_controller(game_id: str, username: str):
        redis_key = f"Game:{game_id}"
        game_data_str = redis_client.get(redis_key)

        if not game_data_str:
            raise HTTPException(status_code=404, detail="Game not found!")

        game = json.loads(game_data_str)
        if game["username"] != username:
            raise HTTPException(status_code=403, detail="You cannot access this game result.")

        game["status"] = "completed"

        time_left = redis_client.ttl(redis_key)
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(game))

        return {
            "user": game["username"],
            "final_score": game["score"],
            "status": game["status"],
            "solved_questions": game["solved_questions"],
            "message": "Game over!",
        }
