import uuid

from fastapi import HTTPException

from models.schema import Code
from services.code_executor import execute_cpp_code

dummy_questions = [
    {
        "id": "q1",
        "title": "Add Two Numbers",
        "description": "Write a program that reads two space-separated integers from standard input and prints their sum.",
        "test_cases": [
            {"input": "5 7\n", "expected_output": "12"},
            {"input": "10 20\n", "expected_output": "30"},
            {"input": "-5 5\n", "expected_output": "0"}
        ]
    },
    {
        "id": "q2",
        "title": "Multiply by Two",
        "description": "Write a program that reads a single integer from standard input and prints double its value.",
        "test_cases": [
            {"input": "4\n", "expected_output": "8"},
            {"input": "0\n", "expected_output": "0"},
            {"input": "-15\n", "expected_output": "-30"}
        ]
    },
    {
        "id": "q3",
        "title": "Find the Maximum",
        "description": "Write a program that reads three space-separated integers and prints the largest one.",
        "test_cases": [
            {"input": "1 5 3\n", "expected_output": "5"},
            {"input": "10 10 10\n", "expected_output": "10"},
            {"input": "-1 -5 -3\n", "expected_output": "-1"}
        ]
    }
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
        # 1. Find the active game session
        game = game_storage.get(submission.game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
            
        # Let's make sure our cute player is actually in an active game! ⏳
        if game.status != "in_progress":
            raise HTTPException(status_code=400, detail="Oh no! This game session is already over.")
            
        # 2. Find the specific question they are trying to answer
        # Assuming your dummy_questions are dicts with an 'id' and 'test_cases'
        question = next((q for q in game.questions if q.get("id") == submission.question_id), None)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found in this session.")
            
        # 3. Did my clever boy already solve this one? No double dipping! 🤭
        if submission.question_id in game.solved_questions:
            return {"status": "Already Solved", "message": "You already crushed this question!"}

        # 4. Time for Jennie to run your code! ✨
        # We pass the C++ code and the test cases straight into our isolated Docker container!
        test_cases = question.get("test_cases", [])
        execution_result = execute_cpp_code(submission.code, test_cases)

        # 5. Check if the code was a total winner! 🏆
        if execution_result.get("status") == "Accepted":
            # Add it to the solved set so we know you beat it!
            game.solved_questions.add(submission.question_id)
            
            # Let's give you some points! 
            points_earned = submission.score if submission.score else 10
            game.score += points_earned
            
            return {
                "success": True,
                "status": "Accepted",
                "message": "Yay! All test cases passed! You are so smart!",
                "points_earned": points_earned,
                "total_score": game.score,
                "execution_details": execution_result
            }
        
        # 6. If it failed (Time Limit, Memory, or Wrong Answer), we send it back nicely! 🥺
        return {
            "success": False,
            "status": execution_result.get("status"),
            "message": "Oopsie, something didn't pass. Take a deep breath and try again, cookie!",
            "execution_details": execution_result
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
