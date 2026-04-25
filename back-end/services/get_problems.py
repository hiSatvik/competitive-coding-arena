import logging
import os
from typing import List

from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv


logger = logging.getLogger(__name__)
load_dotenv()


class TestCase(BaseModel):
    input: str
    expected_output: str


class Problem(BaseModel):
    id: str
    title: str
    difficulty: str
    constraints: List[str]
    description: str
    starter_code: str
    test_cases: List[TestCase]


FALLBACK_PROBLEMS = [
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
    {
        "id": "q4",
        "title": "Count Even Numbers",
        "difficulty": "Easy",
        "constraints": [
            "First input is N followed by N integers",
            "1 <= N <= 1000",
            "Time Complexity: O(N)",
        ],
        "description": "Read an integer N, then read N space-separated integers. Print how many of them are even.",
        "starter_code": """#include <iostream>
using namespace std;

int solve(int n) {
    int count = 0;
    for (int i = 0; i < n; i++) {
        int value;
        cin >> value;
        // Write your logic here
    }
    return count;
}

int main() {
    int n;
    if (cin >> n) {
        cout << solve(n);
    }
    return 0;
}""",
        "test_cases": [
            {"input": "5\n1 2 3 4 6\n", "expected_output": "3"},
            {"input": "4\n1 3 5 7\n", "expected_output": "0"},
            {"input": "6\n2 4 6 8 10 12\n", "expected_output": "6"},
        ],
    },
    {
        "id": "q5",
        "title": "Reverse a String",
        "difficulty": "Medium",
        "constraints": [
            "Input is a single word without spaces",
            "1 <= length <= 1000",
            "Time Complexity: O(N)",
        ],
        "description": "Read a single string and print it in reverse order.",
        "starter_code": """#include <iostream>
#include <string>
using namespace std;

string solve(string s) {
    // Write your logic here
    
}

int main() {
    string s;
    if (cin >> s) {
        cout << solve(s);
    }
    return 0;
}""",
        "test_cases": [
            {"input": "arena\n", "expected_output": "anera"},
            {"input": "code\n", "expected_output": "edoc"},
            {"input": "level\n", "expected_output": "level"},
        ],
    },
]


def _normalize_problem(problem: dict | Problem, index: int) -> dict:
    problem_data = (
        problem.model_dump() if isinstance(problem, Problem) else dict(problem)
    )
    problem_data["id"] = problem_data.get("id") or f"q{index}"
    problem_data["constraints"] = problem_data.get("constraints") or []
    problem_data["test_cases"] = problem_data.get("test_cases") or []
    return problem_data


def generate_dynamic_problems(count: int = 5) -> list[dict]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY or GOOGLE_API_KEY.")

    client = genai.Client(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    prompt = f"""
Generate exactly {count} competitive programming problems for a C++ coding arena.
Return JSON only.

Rules:
1. Mix Easy and Medium difficulty.
2. Each problem must have exactly 3 test cases.
3. Each problem must include starter_code using this shape:
   #include <iostream>
   using namespace std;
   [solve function]
   int main() {{ [logic to read input and call solve] }}
4. Each problem must include:
   id, title, difficulty, constraints, description, starter_code, test_cases.
5. test_cases must contain input and expected_output.
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[Problem],
        },
    )

    parsed = response.parsed or []
    normalized = [
        _normalize_problem(problem, index + 1) for index, problem in enumerate(parsed)
    ]

    if len(normalized) < count:
        raise ValueError("Gemini did not return enough valid problems.")

    return normalized[:count]


def load_competitive_problems(count: int = 5) -> list[dict]:
    try:
        return generate_dynamic_problems(count=count)
    except Exception as exc:
        logger.exception("Falling back to local problems because Gemini failed: %s", exc)
        return [
            _normalize_problem(problem, index + 1)
            for index, problem in enumerate(FALLBACK_PROBLEMS[:count])
        ]
