"""
CodeQuest-related prompts for TAI Tutor AI.

This module contains prompt templates for CodeQuest challenge generation and evaluation.
"""

import json
from typing import Any, Dict, List, Optional


def build_challenge_set_prompt(
    title: str,
    language: str,
    difficulty: str,
    track: str,
    concepts: Optional[List[str]] = None,
    num_challenges: int = 5,
    description: str = "",
    plan_text: str = ""
) -> Dict[str, Any]:
    """
    Build prompt for generating a CodeQuest challenge set.
    
    Args:
        title: Challenge set title/theme
        language: Programming language
        difficulty: Difficulty level
        track: Learning track (e.g., "Python", "JavaScript")
        concepts: List of concepts to cover
        num_challenges: Number of challenges to generate
        description: Optional description
        plan_text: Optional learning plan text
    
    Returns:
        Dictionary with system and user prompts
    """
    system = (
        "You generate programming challenges for an educational product called CodeQuest. "
        "Return ONLY valid JSON. Do not include markdown fences."
    )
    
    user = {
        "task": "Generate a CodeQuest challenge set",
        "constraints": {
            "num_challenges": int(num_challenges),
            "difficulty": str(difficulty),
            "language": language,
            "track": track,
            "ids": "ids must be unique, lowercase, and URL-safe",
            "starter_code": "include minimal starter_code with TODOs but syntactically valid",
            "solution": "include a correct reference solution as code (no markdown fences)",
        },
        "inputs": {
            "title": str(title),
            "description": str(description or ""),
            "concepts": [str(c) for c in (concepts or [])],
            "plan_text": str(plan_text or ""),
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "track", "language", "title", "prompt", "starter_code"],
                "optional": ["solution"],
            },
        },
    }
    
    return {"system": system, "user": json.dumps(user, ensure_ascii=False)}


def build_solution_prompt(language: str, prompt: str, starter_code: str = "") -> Dict[str, str]:
    """
    Build prompt for generating a reference solution.
    
    Args:
        language: Programming language
        prompt: Challenge prompt
        starter_code: Starter code template
    
    Returns:
        Dictionary with system and user prompts
    """
    system = (
        "You write correct reference solutions for programming challenges. "
        "Return ONLY the solution code. Do not include markdown fences, explanations, or extra text."
    )
    
    user = (
        f"Language: {language}\n\n"
        f"Challenge prompt:\n{prompt}\n\n"
        f"Starter code (if any):\n{starter_code}\n\n"
        "Write a clean, correct solution that satisfies the prompt."
    )
    
    return {"system": system, "user": user}


def build_evaluation_prompt(
    language: str,
    prompt: str,
    code: str,
    solution: str = ""
) -> Dict[str, str]:
    """
    Build prompt for evaluating a code submission.
    
    Args:
        language: Programming language
        prompt: Challenge prompt
        code: User's submitted code
        solution: Reference solution for comparison
    
    Returns:
        Dictionary with system and user prompts
    """
    system = (
        "You are an automated grader. Return only JSON with keys: "
        "passed (bool), reason (string, short), feedback (string, optional)."
    )
    
    user = (
        f"Language: {language}\n\n"
        f"Challenge prompt:\n{prompt}\n\n"
        f"Reference solution (for comparison):\n{solution}\n\n"
        f"Student submission:\n{code}\n\n"
        "Evaluate whether the submission correctly satisfies the prompt requirements. "
        "If it fails, provide a concise reason (one sentence) and an optional short feedback. "
        "Return only a JSON object."
    )
    
    return {"system": system, "user": user}


# =============================================================================
# Default Challenge Templates
# =============================================================================

DEFAULT_CHALLENGES = [
    {
        "id": "py_add_two_numbers",
        "track": "Python",
        "language": "python",
        "title": "Add Two Numbers",
        "prompt": (
            "Write a function `add(a, b)` that returns the sum of `a` and `b`.\n\n"
            "Requirements:\n"
            "- Must return an int/float numeric sum\n"
            "- Do not print; just return"
        ),
        "starter_code": "def add(a, b):\n    # TODO: implement\n    pass\n",
        "solution": "def add(a, b):\n    return a + b\n",
    },
    {
        "id": "py_reverse_string",
        "track": "Python",
        "language": "python",
        "title": "Reverse a String",
        "prompt": (
            "Write a function `reverse_string(s)` that returns the reverse of the input string `s`.\n\n"
            "Examples:\n"
            "- reverse_string('abc') -> 'cba'\n"
            "- reverse_string('') -> ''"
        ),
        "starter_code": "def reverse_string(s: str) -> str:\n    # TODO: implement\n    pass\n",
        "solution": "def reverse_string(s: str) -> str:\n    return s[::-1]\n",
    },
    {
        "id": "js_fizzbuzz",
        "track": "JavaScript",
        "language": "javascript",
        "title": "FizzBuzz",
        "prompt": (
            "Write a function `fizzBuzz(n)` that returns an array of length `n` with values from 1..n "
            "using the classic FizzBuzz rules:\n"
            "- 'Fizz' for multiples of 3\n"
            "- 'Buzz' for multiples of 5\n"
            "- 'FizzBuzz' for multiples of both\n"
            "- otherwise the number itself\n\n"
            "Example: fizzBuzz(5) -> [1,2,'Fizz',4,'Buzz']"
        ),
        "starter_code": "function fizzBuzz(n) {\n  // TODO: implement\n}\n\nmodule.exports = { fizzBuzz };\n",
        "solution": (
            "function fizzBuzz(n) {\n"
            "  const out = [];\n"
            "  for (let i = 1; i <= n; i++) {\n"
            "    const fizz = i % 3 === 0;\n"
            "    const buzz = i % 5 === 0;\n"
            "    if (fizz && buzz) out.push('FizzBuzz');\n"
            "    else if (fizz) out.push('Fizz');\n"
            "    else if (buzz) out.push('Buzz');\n"
            "    else out.push(i);\n"
            "  }\n"
            "  return out;\n"
            "}\n\n"
            "module.exports = { fizzBuzz };\n"
        ),
    },
    {
        "id": "js_is_palindrome",
        "track": "JavaScript",
        "language": "javascript",
        "title": "Palindrome Check",
        "prompt": (
            "Write a function `isPalindrome(s)` that returns true if `s` reads the same backwards. "
            "Treat the string exactly as-is (case-sensitive, spaces count).\n\n"
            "Examples:\n"
            "- isPalindrome('racecar') -> true\n"
            "- isPalindrome('Racecar') -> false\n"
            "- isPalindrome('a b a') -> true"
        ),
        "starter_code": "function isPalindrome(s) {\n  // TODO: implement\n}\n\nmodule.exports = { isPalindrome };\n",
        "solution": (
            "function isPalindrome(s) {\n"
            "  const rev = s.split('').reverse().join('');\n"
            "  return s === rev;\n"
            "}\n\n"
            "module.exports = { isPalindrome };\n"
        ),
    },
]


def get_default_challenges() -> List[Dict[str, Any]]:
    """Get the default challenge bank."""
    return DEFAULT_CHALLENGES.copy()
