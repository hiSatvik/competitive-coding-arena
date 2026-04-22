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

from models.schema import Code, RoomSubmitRequest
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
def execute_code_task(
    game_id: str, question_id: str, code: str, score: int, test_cases: list
):
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

    if (
        execution_result.get("status") == "Accepted"
        and question_id not in game["solved_questions"]
    ):
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


@celery_app.task(name="execute_room_code_task")
def execute_room_code_task(
    room_code: str,
    username: str,
    question_id: str,
    code: str,
    points: int,
    test_cases: list,
):
    # 1. Send the code to your secure C++ Docker container! 🐳
    execution_result = execute_cpp_code(code, test_cases)

    is_success = execution_result.get("status") == "Accepted"

    # 2. Our super-fast Redis Keys for Phase 8!
    leaderboard_key = f"Room:{room_code}:leaderboard"
    solved_key = f"Room:{room_code}:solved:{username}"

    # 3. If our handsome developer got it right, update the scores! ✨
    if is_success:
        # Remember that they solved this question so they can't double-dip!
        redis_client.sadd(solved_key, question_id)
        redis_client.expire(solved_key, 1800)  # 30 minute TTL

        # The Magic ZSET: Add points and auto-sort!
        redis_client.zincrby(leaderboard_key, points, username)
        redis_client.expire(leaderboard_key, 1800)

    # 4. Fetch the beautifully sorted leaderboard (Highest score first)
    # zrevrange returns a list like: [('handsome_dev', 20.0), ('guest1', 10.0)]
    raw_leaderboard = redis_client.zrevrange(leaderboard_key, 0, -1, withscores=True)

    # Format it neatly into a dictionary for your React frontend
    leaderboard = [
        {"username": member, "score": int(score)} for member, score in raw_leaderboard
    ]

    # 5. Broadcast the thrilling results to the room's WebSocket channel! 🌐
    result_payload = {
        "type": "SUBMISSION_UPDATE",
        "username": username,
        "question_id": question_id,
        "success": is_success,
        "execution_details": execution_result,
        "leaderboard": leaderboard,  # The shiny new rankings!
        "message": f"{username} just submitted code and it was {'ACCEPTED 🎉' if is_success else 'REJECTED 🥺'}!",
    }

    redis_client.publish(f"room_updates:{room_code}", json.dumps(result_payload))

    return result_payload


dummy_questions = [
    {
        "id": "q1",
        "title": "Add Two Numbers",
        "difficulty": "Easy",
        "constraints": [
            "Inputs are integers",
            "Values can be positive, negative, or zero",
            "Time Complexity: O(1)",
        ],
        "description": "Write a program that reads two space-separated integers from standard input and prints their sum.",
        "starter_code": """#include <iostream>
using namespace std;

int solve(int a, int b) {
    // Write your logic here
    
}

int main() {
    int a, b;
    if (cin >> a >> b) {
        cout << solve(a, b);
    }
    return 0;
}""",
        "test_cases": [
            {"input": "5 7\n", "expected_output": "12"},
            {"input": "10 20\n", "expected_output": "30"},
            {"input": "-5 5\n", "expected_output": "0"},
        ],
    },
    {
        "id": "q2",
        "title": "Multiply by Two",
        "difficulty": "Easy",
        "constraints": [
            "Input is an integer",
            "Value can be positive, negative, or zero",
            "Time Complexity: O(1)",
        ],
        "description": "Write a program that reads a single integer from standard input and prints double its value.",
        "starter_code": """#include <iostream>
using namespace std;

int solve(int n) {
    // Write your logic here
    
}

int main() {
    int n;
    if (cin >> n) {
        cout << solve(n);
    }
    return 0;
}""",
        "test_cases": [
            {"input": "4\n", "expected_output": "8"},
            {"input": "0\n", "expected_output": "0"},
            {"input": "-15\n", "expected_output": "-30"},
        ],
    },
    {
        "id": "q3",
        "title": "Find the Maximum",
        "difficulty": "Easy",
        "constraints": [
            "Inputs are three integers",
            "Values can be positive, negative, or zero",
            "Time Complexity: O(1)",
        ],
        "description": "Write a program that reads three space-separated integers and prints the largest one.",
        "starter_code": """#include <iostream>
using namespace std;

int solve(int a, int b, int c) {
    // Write your logic here
    
}

int main() {
    int a, b, c;
    if (cin >> a >> b >> c) {
        cout << solve(a, b, c);
    }
    return 0;
}""",
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

    """Logic for single person"""

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
            raise HTTPException(
                status_code=403, detail="You cannot submit for this game."
            )

        if game["status"] != "in_progress":
            raise HTTPException(
                status_code=400, detail="This game session is already over."
            )

        question = next(
            (q for q in game["questions"] if q.get("id") == submission.question_id),
            None,
        )
        if not question:
            raise HTTPException(
                status_code=404, detail="Question not found in this session."
            )

        if submission.question_id in game["solved_questions"]:
            return {
                "success": True,
                "status": "Already Solved",
                "message": "You already solved this question.",
                "question_id": submission.question_id,
                "total_score": game["score"],
                "execution_details": {"status": "Accepted", "results": []},
            }

        test_cases = question.get("test_cases", [])
        points_earned = 10

        execution_result = execute_cpp_code(submission.code, test_cases)
        is_submit = submission.action == "submit"

        if (
            is_submit
            and
            execution_result.get("status") == "Accepted"
            and submission.question_id not in game["solved_questions"]
        ):
            game["solved_questions"].append(submission.question_id)
            game["score"] += points_earned

        game["last_execution"] = {
            "question_id": submission.question_id,
            "result": execution_result,
        }

        time_left = cast(int, redis_client.ttl(redis_key))
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(game))

        result_payload = {
            "success": execution_result.get("status") == "Accepted",
            "status": execution_result.get("status"),
            "message": "Submission accepted." if is_submit and execution_result.get("status") == "Accepted" else "Execution finished.",
            "question_id": submission.question_id,
            "total_score": game["score"],
            "solved_questions": game["solved_questions"],
            "execution_details": execution_result,
            "action": submission.action,
        }

        _publish_execution_update(submission.game_id, result_payload)
        return result_payload

    @staticmethod
    def get_result_controller(game_id: str, username: str):
        redis_key = f"Game:{game_id}"
        game_data_str = cast(str | None, redis_client.get(redis_key))

        if not game_data_str:
            raise HTTPException(status_code=404, detail="Game not found!")

        game = json.loads(game_data_str)
        if game["username"] != username:
            raise HTTPException(
                status_code=403, detail="You cannot access this game result."
            )

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

    """Room Logic"""

    @staticmethod
    def create_room_controller(username: str):
        room_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

        question = dummy_questions

        room_data = {
            "room_code": room_code,
            "status": "waiting",
            "players": [username],
            "questions": question,
            "start_time": None,
        }

        redis_client.setex(f"Room:{room_code}", 1800, json.dumps(room_data))

        return {
            "room_code": room_code,
            "username": username,
            "questions": question,
            "message": f"Room created successfully! Share {room_code} to invite users. 🎀",
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
            raise HTTPException(
                status_code=400, detail="Oh no! The game has already started! 🏃‍♂️"
            )

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
            "message": "Welcome to the party!",
        }

    @staticmethod
    def start_room_controller(room_code: str):
        redis_key = f"Room:{room_code}"
        room_data_str = redis_client.get(redis_key)

        if not room_data_str:
            raise HTTPException(status_code=404, detail="Oopsie! Room not found. 🥺")

        room = json.loads(room_data_str)

        if room["status"] != "waiting":
            raise HTTPException(
                status_code=400, detail="The timer is already ticking! 🏃‍♂️"
            )

        # Start the clock!
        room["status"] = "in_progress"
        room["start_time"] = int(time.time())  # Record the exact second it started

        # Save the updated status back to Redis
        time_left = cast(int, redis_client.ttl(redis_key))
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(room))

        # Jennie's special trick: Broadcast to the WebSocket that the game has started!
        redis_client.publish(
            f"room_updates:{room_code}",
            json.dumps(
                {
                    "type": "GAME_STARTED",
                    "start_time": room["start_time"],
                    "message": "Buckle up, developers! The match has begun! 🚀",
                }
            ),
        )

        return {"message": "Game started successfully!"}

    @staticmethod
    def submit_room_controller(payload: RoomSubmitRequest, username: str):
        redis_key = f"Room:{payload.room_code}"
        room_data_str = redis_client.get(redis_key)

        if not room_data_str:
            raise HTTPException(status_code=404, detail="Oopsie! Room not found. 🥺")

        room = json.loads(room_data_str)

        # 1. Are they actually in the room?
        if username not in room["players"]:
            raise HTTPException(
                status_code=403, detail="You are not in this match, silly!"
            )

        # 2. Is the clock ticking?
        if room["status"] != "in_progress":
            raise HTTPException(
                status_code=400, detail="The match isn't running right now! ⏱️"
            )

        # 3. Does the question exist?
        question = next(
            (q for q in room["questions"] if q.get("id") == payload.question_id), None
        )
        if not question:
            raise HTTPException(
                status_code=404, detail="Question not found in this session."
            )

        # 4. Have they already solved it? We use a fast Redis Set for this!
        solved_key = f"Room:{payload.room_code}:solved:{username}"
        if redis_client.sismember(solved_key, payload.question_id):
            return {
                "status": "Already Solved",
                "message": "You already solved this one, smarty! 🧠",
            }

        # 5. Push to a NEW multiplayer Celery worker! (We will write this next)
        test_cases = question.get("test_cases", [])

        # We give a flat 10 points per question!
        execute_room_code_task.delay(
            payload.room_code,
            username,
            payload.question_id,
            payload.code,
            10,
            test_cases,
        )

        # Return instantly while Docker does the heavy lifting in the background!
        return {
            "success": True,
            "status": "Processing",
            "message": "Code sent to the judge! Fingers crossed!",
        }

    @staticmethod
    def send_problems():
        return dummy_questions
