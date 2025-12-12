"""Default CodeQuest challenge bank.

This module defines built-in challenges used when no on-disk challenge DB exists.
Challenges are intentionally small and safe to evaluate with subprocess-based tests.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_default_challenges() -> List[Dict[str, Any]]:
    """Return a list of challenge dicts.

    Schema (superset; the API will omit tests when sending to the client):
    - id: str
    - track: str (e.g., "Python", "JavaScript")
    - language: str ("python" | "javascript")
    - title: str
    - prompt: str
    - starter_code: str
    - evaluator: str ("python_unittest" | "node_assert")
    - test_code: str (language-specific tests)
    """

    return [
        {
            "id": "py_add_two_numbers",
            "track": "Python",
            "language": "python",
            "title": "Add Two Numbers",
            "prompt": "Write a function `add(a, b)` that returns the sum of `a` and `b`.\n\nRequirements:\n- Must return an int/float numeric sum\n- Do not print; just return",
            "starter_code": "def add(a, b):\n    # TODO: implement\n    pass\n",
            "evaluator": "python_unittest",
            "test_code": """import unittest\n\nimport student\n\n\nclass TestAdd(unittest.TestCase):\n    def test_basic(self):\n        self.assertEqual(student.add(1, 2), 3)\n        self.assertEqual(student.add(-1, 1), 0)\n\n    def test_floats(self):\n        self.assertAlmostEqual(student.add(0.1, 0.2), 0.3, places=7)\n\n\nif __name__ == '__main__':\n    unittest.main()\n""",
        },
        {
            "id": "py_reverse_string",
            "track": "Python",
            "language": "python",
            "title": "Reverse a String",
            "prompt": "Write a function `reverse_string(s)` that returns the reverse of the input string `s`.\n\nExamples:\n- reverse_string('abc') -> 'cba'\n- reverse_string('') -> ''",
            "starter_code": "def reverse_string(s: str) -> str:\n    # TODO: implement\n    pass\n",
            "evaluator": "python_unittest",
            "test_code": """import unittest\n\nimport student\n\n\nclass TestReverseString(unittest.TestCase):\n    def test_examples(self):\n        self.assertEqual(student.reverse_string('abc'), 'cba')\n        self.assertEqual(student.reverse_string(''), '')\n\n    def test_spaces(self):\n        self.assertEqual(student.reverse_string('a b'), 'b a')\n\n\nif __name__ == '__main__':\n    unittest.main()\n""",
        },
        {
            "id": "js_fizzbuzz",
            "track": "JavaScript",
            "language": "javascript",
            "title": "FizzBuzz",
            "prompt": "Write a function `fizzBuzz(n)` that returns an array of length `n` with values from 1..n using the classic FizzBuzz rules:\n- 'Fizz' for multiples of 3\n- 'Buzz' for multiples of 5\n- 'FizzBuzz' for multiples of both\n- otherwise the number itself\n\nExample: fizzBuzz(5) -> [1,2,'Fizz',4,'Buzz']",
            "starter_code": "function fizzBuzz(n) {\n  // TODO: implement\n}\n\nmodule.exports = { fizzBuzz };\n",
            "evaluator": "node_assert",
            "test_code": """const assert = require('assert');\nconst student = require('./student');\n\nfunction normalize(a) { return JSON.parse(JSON.stringify(a)); }\n\nassert.deepStrictEqual(normalize(student.fizzBuzz(5)), [1,2,'Fizz',4,'Buzz']);\nassert.deepStrictEqual(normalize(student.fizzBuzz(15))[14], 'FizzBuzz');\nassert.deepStrictEqual(normalize(student.fizzBuzz(1)), [1]);\n\nconsole.log('OK');\n""",
        },
        {
            "id": "js_is_palindrome",
            "track": "JavaScript",
            "language": "javascript",
            "title": "Palindrome Check",
            "prompt": "Write a function `isPalindrome(s)` that returns true if `s` reads the same backwards. Treat the string exactly as-is (case-sensitive, spaces count).\n\nExamples:\n- isPalindrome('racecar') -> true\n- isPalindrome('Racecar') -> false\n- isPalindrome('a b a') -> true",
            "starter_code": "function isPalindrome(s) {\n  // TODO: implement\n}\n\nmodule.exports = { isPalindrome };\n",
            "evaluator": "node_assert",
            "test_code": """const assert = require('assert');\nconst student = require('./student');\n\nassert.strictEqual(student.isPalindrome('racecar'), true);\nassert.strictEqual(student.isPalindrome('Racecar'), false);\nassert.strictEqual(student.isPalindrome('a b a'), true);\nassert.strictEqual(student.isPalindrome('ab'), false);\n\nconsole.log('OK');\n""",
        },
        {
            "id": "react_classnames",
            "track": "React",
            "language": "javascript",
            "title": "Class Name Builder (classnames)",
            "prompt": "In React apps, it's common to build CSS class strings conditionally.\n\nWrite a function `classNames(...args)` that returns a single space-separated string.\n\nRules:\n- String args are included as-is\n- Falsy values (false, null, undefined, 0, '') are ignored\n- Object args include keys whose values are truthy\n\nExamples:\n- classNames('btn', 'primary') -> 'btn primary'\n- classNames('btn', false && 'x', { active: true, disabled: false }) -> 'btn active'",
            "starter_code": "function classNames(...args) {\n  // TODO: implement\n}\n\nmodule.exports = { classNames };\n",
            "evaluator": "node_assert",
            "test_code": """const assert = require('assert');\nconst student = require('./student');\n\nassert.strictEqual(student.classNames('btn', 'primary'), 'btn primary');\nassert.strictEqual(student.classNames('btn', false, null, undefined, ''), 'btn');\nassert.strictEqual(student.classNames('btn', { active: true, disabled: false }), 'btn active');\nassert.strictEqual(student.classNames('a', { b: 1, c: 0 }, 'd'), 'a b d');\n\nconsole.log('OK');\n""",
        },
    ]
