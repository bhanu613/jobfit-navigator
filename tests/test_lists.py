import re
import unittest

from jobfit import jobfit_navigation_engine as engine

NAMES = {"aws": 1, "python": 2, "docker": 3, "excel": 4, "sql": 5, "git": 6}
PATTERN = re.compile(r"\b(" + "|".join(NAMES) + r")\b", re.I)


def statuses(text):
    mentions = [
        dict(skill_id=NAMES[m.group(0).lower()], start=m.start(), end=m.end(), matched_text=m.group(0))
        for m in PATTERN.finditer(text)
    ]
    found = {}
    for m in mentions:
        found.setdefault(m["matched_text"], []).append(engine.interpret(text, m, mentions)[0])
    return {name: engine.aggregate(values) for name, values in found.items()}


class ListRuleTests(unittest.TestCase):
    def check(self, text, expected):
        result = statuses(text)
        self.assertTrue(result, text)
        for name, status in result.items():
            self.assertEqual(status, expected, f"{text!r}: {name} was {status}")

    def test_comma_only_lists_are_required(self):
        for text in (
            "AWS, Python, Docker, Excel are required.",
            "AWS, Python, Docker, Excel, are required.",
            "Python, SQL are needed.",
            "Python, SQL, Git are mandatory.",
            "Python, SQL, Git are a must.",
            "Python, SQL, Git skills are required.",
            "- Python, SQL are required",
            "Python, SQL, Git sind erforderlich.",
        ):
            with self.subTest(text=text):
                self.check(text, "required")

    def test_must_have_lists_are_required(self):
        for text in (
            "You must have Python and SQL.",
            "You must have Python, SQL, Git.",
            "You must know Python, SQL and Git.",
            "You must have experience with Python, SQL.",
            "We need to know Python.",
        ):
            with self.subTest(text=text):
                self.check(text, "required")

    def test_comma_only_lists_are_desirable(self):
        for text in (
            "Python, Docker are nice to have.",
            "Python, SQL, Git sind wünschenswert.",
        ):
            with self.subTest(text=text):
                self.check(text, "desirable")

    def test_unclear_wording_stays_uncertain(self):
        for text in (
            "Python or SQL are required.",
            "Python, SQL are required but Git is not.",
            "Python, SQL are required unless you know Git.",
            "You must have Python or SQL.",
            "You must have Python and be willing to learn SQL.",
            "You must not have Python, SQL.",
            "Python, SQL are not required and Git is required.",
            "AWS, Python, Docker, Excel, are are needed and required.",
            "Python, SQL, Git.",
        ):
            with self.subTest(text=text):
                self.check(text, "uncertain")

    def test_existing_results_do_not_change(self):
        self.check("Python is required.", "required")
        self.check("Python and SQL are required.", "required")
        self.check("Python, SQL and Git are required.", "required")
        self.check("Python is a plus.", "desirable")
        self.check("Python, SQL, Git are a plus.", "desirable")
        self.check("Python is not required.", "not_required")
        self.check("We need Python and SQL.", "required")
        self.assertEqual(statuses("Python is required but SQL is not."), {"Python": "uncertain", "SQL": "uncertain"})
        self.assertEqual(statuses("Python is required, Docker is a plus."), {"Python": "required", "Docker": "desirable"})


if __name__ == "__main__":
    unittest.main()