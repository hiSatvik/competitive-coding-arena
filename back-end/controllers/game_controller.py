import uuid

from fastapi import HTTPException

from models.schema import Code
from services.code_executor import execute_cpp_code


dummy_questions = [
    {
        "question_id": "q_001",
        "title": "The Sweet Sum",
        "description": "Given two integers A and B, write a C++ program to find their sum.",
        "difficulty": "Easy",
        "sample_input": "3 5",
        "sample_output": "8",
        "time_limit": "1s",
        "memory_limit": "256MB",
    },
    {
        "question_id": "q_002",
        "title": "Reverse the Magic",
        "description": "Given a string S, print the string in reverse order.",
        "difficulty": "Easy",
        "sample_input": "hello",
        "sample_output": "olleh",
        "time_limit": "1s",
        "memory_limit": "256MB",
    },
    {
        "question_id": "q_003",
        "title": "Find the Biggest Diamond",
        "description": "Given an array of N integers, find the maximum element in the array.",
        "difficulty": "Medium",
        "sample_input": "5\n1 4 9 2 5",
        "sample_output": "9",
        "time_limit": "2s",
        "memory_limit": "256MB",
    },
]

game_storage = {}


class GameLogic:
    def __init__(self, username: str):
        self.game_id = str(uuid.uuid4())
        self.username = username
        self.score = 0
        self.status = "in_progress"
        self.questions = dummy_questions
        self.solved_questions = set()

        game_storage[self.game_id] = self

    def start_game_controller(self):
        return {
            "game_id": self.game_id,
            "questions": self.questions,
            "username": self.username,
            "message": "Good luck!",
        }

    @staticmethod
    def submit_code_controller(submission: Code, username: str):
        if submission.game_id not in game_storage:
            raise HTTPException(status_code=404, detail="Game not found.")

        game = game_storage[submission.game_id]
        if game.username != username:
            raise HTTPException(status_code=403, detail="You cannot submit for this game.")

        if submission.language.lower() != "cpp":
            raise HTTPException(
                status_code=400,
                detail="Only C++ submissions are supported right now.",
            )

        requested_question_id = submission.question_id or game.questions[0]["question_id"]
        question = next(
            (item for item in game.questions if item["question_id"] == requested_question_id),
            None,
        )
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found.")

        execution_result = execute_cpp_code(
            submission.code,
            [
                {
                    "input": question["sample_input"],
                    "expected_output": question["sample_output"],
                }
            ],
        )
        is_correct = execution_result["status"] == "Accepted"

        if is_correct and question["question_id"] not in game.solved_questions:
            game.score += 10
            game.solved_questions.add(question["question_id"])

        return {
            "status": "solved" if is_correct else "failed",
            "message": "Code accepted." if is_correct else "Code execution failed.",
            "question_id": question["question_id"],
            "execution": execution_result,
            "current_score": game.score,
        }

    @staticmethod
    def get_result_controller(game_id: str, username: str):
        if game_id not in game_storage:
            raise HTTPException(status_code=404, detail="Game not found!")

        game = game_storage[game_id]
        if game.username != username:
            raise HTTPException(status_code=403, detail="You cannot access this game result.")

        game.status = "completed"

        return {
            "user": game.username,
            "final_score": game.score,
            "status": game.status,
            "solved_questions": list(game.solved_questions),
            "message": "Game over!",
        }
