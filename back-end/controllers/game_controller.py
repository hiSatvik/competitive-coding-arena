import json
import os
import random
import string
import threading
import time
import uuid
from typing import cast

from celery import Celery
from fastapi import HTTPException
from redis import Redis

from models.schema import Code, RoomSubmitRequest
from services.code_executor import execute_cpp_code
from services.get_problems import load_competitive_problems


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

celery_app = Celery(
    "code_execution_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

ROOM_JOIN_WINDOW_SECONDS = 120
MATCH_DURATION_SECONDS = 1800
QUESTIONS_PER_MATCH = 5


def _publish_execution_update(game_id: str, payload: dict) -> None:
    redis_client.publish(f"game_updates:{game_id}", json.dumps(payload))


def _publish_room_update(room_code: str, payload: dict) -> None:
    redis_client.publish(f"room_updates:{room_code}", json.dumps(payload))


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
    execution_result = execute_cpp_code(code, test_cases)
    is_success = execution_result.get("status") == "Accepted"

    room_key = f"Room:{room_code}"
    room_data_str = redis_client.get(room_key)
    if not room_data_str:
        return {
            "type": "SUBMISSION_UPDATE",
            "username": username,
            "question_id": question_id,
            "success": False,
            "execution_details": {
                "status": "Room Error",
                "error": "Room no longer exists.",
            },
            "leaderboard": [],
            "message": "Room no longer exists.",
        }

    room = json.loads(room_data_str)
    leaderboard_key = f"Room:{room_code}:leaderboard"
    solved_key = f"Room:{room_code}:solved:{username}"

    if is_success:
        redis_client.sadd(solved_key, question_id)
        redis_client.expire(solved_key, MATCH_DURATION_SECONDS)
        redis_client.zincrby(leaderboard_key, points, username)
        redis_client.expire(leaderboard_key, MATCH_DURATION_SECONDS)

    leaderboard = GameLogic._build_room_leaderboard(room_code, room["players"])
    result_payload = {
        "type": "SUBMISSION_UPDATE",
        "username": username,
        "question_id": question_id,
        "success": is_success,
        "execution_details": execution_result,
        "leaderboard": leaderboard,
        "message": f"{username} just submitted code and it was {'ACCEPTED' if is_success else 'REJECTED'}!",
    }

    _publish_room_update(room_code, result_payload)

    total_questions = len(room.get("questions", []))
    solved_count = cast(int, redis_client.scard(solved_key))
    if (
        is_success
        and room.get("status") == "in_progress"
        and total_questions > 0
        and solved_count >= total_questions
    ):
        GameLogic._finalize_room(
            room_code,
            room,
            winner_usernames=[username],
            winner_reason="completed_all_first",
        )

    return result_payload


class GameLogic:
    def __init__(self, username: str):
        self.game_id = str(uuid.uuid4())
        self.username = username
        self.questions = load_competitive_problems(count=QUESTIONS_PER_MATCH)

        game_data = {
            "game_id": self.game_id,
            "username": self.username,
            "score": 0,
            "status": "in_progress",
            "questions": self.questions,
            "solved_questions": [],
        }

        redis_client.setex(f"Game:{self.game_id}", MATCH_DURATION_SECONDS, json.dumps(game_data))

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
            and execution_result.get("status") == "Accepted"
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
            "message": "Submission accepted."
            if is_submit and execution_result.get("status") == "Accepted"
            else "Execution finished.",
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
        room_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        join_deadline = int(time.time()) + ROOM_JOIN_WINDOW_SECONDS
        questions = load_competitive_problems(count=QUESTIONS_PER_MATCH)

        room_data = {
            "room_code": room_code,
            "status": "waiting",
            "players": [username],
            "questions": questions,
            "start_time": None,
            "join_deadline": join_deadline,
            "winner_usernames": [],
            "winner_reason": None,
            "completed_at": None,
        }

        redis_client.setex(f"Room:{room_code}", MATCH_DURATION_SECONDS, json.dumps(room_data))
        threading.Thread(
            target=GameLogic._auto_start_room_after_deadline,
            args=(room_code,),
            daemon=True,
        ).start()

        return {
            "room_code": room_code,
            "username": username,
            "players": room_data["players"],
            "questions": room_data["questions"],
            "status": room_data["status"],
            "join_deadline": join_deadline,
            "winner_usernames": [],
            "message": f"Room created successfully! Share {room_code} to invite users.",
        }

    @staticmethod
    def join_room_controller(room_code: str, username: str):
        redis_key = f"Room:{room_code}"
        room_data_str = redis_client.get(redis_key)

        if not room_data_str:
            raise HTTPException(status_code=404, detail="Room not found.")

        room = json.loads(room_data_str)
        room = GameLogic._ensure_room_started_if_ready(room_code, room)
        room = GameLogic._ensure_room_finished_if_ready(room_code, room)

        if room["status"] != "waiting":
            return GameLogic._serialize_room_state(room, username)

        if username not in room["players"]:
            room["players"].append(username)

            time_left = cast(int, redis_client.ttl(redis_key))
            if time_left > 0:
                redis_client.setex(redis_key, time_left, json.dumps(room))

            _publish_room_update(
                room_code,
                {
                    "type": "PLAYER_JOINED",
                    "room_code": room_code,
                    "players": room["players"],
                    "status": room["status"],
                    "join_deadline": room.get("join_deadline"),
                },
            )

        return GameLogic._serialize_room_state(room, username)

    @staticmethod
    def get_room_controller(room_code: str, username: str):
        redis_key = f"Room:{room_code}"
        room_data_str = redis_client.get(redis_key)

        if not room_data_str:
            raise HTTPException(status_code=404, detail="Room not found.")

        room = json.loads(room_data_str)
        room = GameLogic._ensure_room_started_if_ready(room_code, room)
        room = GameLogic._ensure_room_finished_if_ready(room_code, room)
        return GameLogic._serialize_room_state(room, username)

    @staticmethod
    def start_room_controller(room_code: str):
        redis_key = f"Room:{room_code}"
        room_data_str = redis_client.get(redis_key)

        if not room_data_str:
            raise HTTPException(status_code=404, detail="Room not found.")

        room = json.loads(room_data_str)

        if room["status"] != "waiting":
            raise HTTPException(status_code=400, detail="The room has already started.")

        room["status"] = "in_progress"
        room["start_time"] = int(time.time())

        time_left = cast(int, redis_client.ttl(redis_key))
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(room))

        _publish_room_update(
            room_code,
            {
                "type": "GAME_STARTED",
                "room_code": room_code,
                "players": room["players"],
                "questions": room["questions"],
                "start_time": room["start_time"],
                "message": "The room match has started!",
            },
        )

        return {"message": "Game started successfully!"}

    @staticmethod
    def _auto_start_room_after_deadline(room_code: str):
        redis_key = f"Room:{room_code}"

        while True:
            room_data_str = redis_client.get(redis_key)
            if not room_data_str:
                return

            room = json.loads(room_data_str)
            if room["status"] != "waiting":
                return

            join_deadline = room.get("join_deadline")
            if join_deadline is None:
                return

            remaining = join_deadline - int(time.time())
            if remaining <= 0:
                try:
                    GameLogic.start_room_controller(room_code)
                except HTTPException:
                    return
                return

            time.sleep(min(remaining, 1))

    @staticmethod
    def _ensure_room_started_if_ready(room_code: str, room: dict):
        join_deadline = room.get("join_deadline")

        if (
            room.get("status") == "waiting"
            and join_deadline is not None
            and int(time.time()) >= join_deadline
        ):
            GameLogic.start_room_controller(room_code)
            updated_room_data = redis_client.get(f"Room:{room_code}")
            if not updated_room_data:
                raise HTTPException(status_code=404, detail="Room not found.")
            return json.loads(updated_room_data)

        return room

    @staticmethod
    def _ensure_room_finished_if_ready(room_code: str, room: dict):
        start_time = room.get("start_time")

        if room.get("status") == "completed":
            return room

        if (
            room.get("status") == "in_progress"
            and start_time is not None
            and int(time.time()) >= start_time + MATCH_DURATION_SECONDS
        ):
            return GameLogic._finalize_room(room_code, room)

        return room

    @staticmethod
    def _build_room_leaderboard(room_code: str, players: list[str]):
        leaderboard_key = f"Room:{room_code}:leaderboard"
        leaderboard = []

        for player in players:
            raw_score = redis_client.zscore(leaderboard_key, player)
            solved_count = cast(int, redis_client.scard(f"Room:{room_code}:solved:{player}"))
            leaderboard.append(
                {
                    "username": player,
                    "score": int(raw_score or 0),
                    "solved_count": solved_count,
                    "time": 0,
                }
            )

        leaderboard.sort(
            key=lambda entry: (-entry["solved_count"], -entry["score"], entry["username"])
        )
        return leaderboard

    @staticmethod
    def _finalize_room(
        room_code: str,
        room: dict,
        winner_usernames: list[str] | None = None,
        winner_reason: str = "highest_solved_at_timeout",
    ):
        if room.get("status") == "completed":
            return room

        leaderboard = GameLogic._build_room_leaderboard(room_code, room["players"])

        if winner_usernames is None:
            highest_solved = max(
                (entry["solved_count"] for entry in leaderboard),
                default=0,
            )
            winner_usernames = [
                entry["username"]
                for entry in leaderboard
                if entry["solved_count"] == highest_solved
            ]

        room["status"] = "completed"
        room["winner_usernames"] = winner_usernames
        room["winner_reason"] = winner_reason
        room["completed_at"] = int(time.time())

        redis_key = f"Room:{room_code}"
        time_left = cast(int, redis_client.ttl(redis_key))
        if time_left > 0:
            redis_client.setex(redis_key, time_left, json.dumps(room))

        winner_text = ", ".join(winner_usernames) if winner_usernames else "No winners"
        _publish_room_update(
            room_code,
            {
                "type": "MATCH_COMPLETED",
                "room_code": room_code,
                "leaderboard": leaderboard,
                "winner_usernames": winner_usernames,
                "winner_reason": winner_reason,
                "completed_at": room["completed_at"],
                "message": f"Match completed. Winner(s): {winner_text}",
            },
        )
        return room

    @staticmethod
    def _serialize_room_state(room: dict, username: str):
        return {
            "room_code": room["room_code"],
            "username": username,
            "players": room["players"],
            "questions": room["questions"],
            "status": room["status"],
            "join_deadline": room.get("join_deadline"),
            "start_time": room.get("start_time"),
            "leaderboard": GameLogic._build_room_leaderboard(
                room["room_code"], room["players"]
            ),
            "winner_usernames": room.get("winner_usernames", []),
            "winner_reason": room.get("winner_reason"),
            "completed_at": room.get("completed_at"),
            "match_duration_seconds": MATCH_DURATION_SECONDS,
        }

    @staticmethod
    def submit_room_controller(payload: RoomSubmitRequest, username: str):
        redis_key = f"Room:{payload.room_code}"
        room_data_str = redis_client.get(redis_key)

        if not room_data_str:
            raise HTTPException(status_code=404, detail="Room not found.")

        room = json.loads(room_data_str)
        room = GameLogic._ensure_room_started_if_ready(payload.room_code, room)
        room = GameLogic._ensure_room_finished_if_ready(payload.room_code, room)

        if username not in room["players"]:
            raise HTTPException(status_code=403, detail="You are not in this match.")

        if room["status"] == "completed":
            return {
                "success": False,
                "status": "Completed",
                "message": "The match is already over.",
                "winner_usernames": room.get("winner_usernames", []),
            }

        if room["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="The match isn't running right now.")

        question = next(
            (q for q in room["questions"] if q.get("id") == payload.question_id), None
        )
        if not question:
            raise HTTPException(status_code=404, detail="Question not found in this session.")

        solved_key = f"Room:{payload.room_code}:solved:{username}"
        if redis_client.sismember(solved_key, payload.question_id):
            return {
                "status": "Already Solved",
                "message": "You already solved this question.",
            }

        test_cases = question.get("test_cases", [])
        result_payload = execute_room_code_task(
            payload.room_code,
            username,
            payload.question_id,
            payload.code,
            10,
            test_cases,
        )

        return {
            "success": True,
            "status": result_payload.get("execution_details", {}).get("status", "Processed"),
            "message": "Code judged successfully.",
            "execution_details": result_payload.get("execution_details"),
        }

    @staticmethod
    def send_problems():
        return load_competitive_problems(count=QUESTIONS_PER_MATCH)
