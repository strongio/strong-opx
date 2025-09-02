import unittest
from unittest.mock import MagicMock, patch

from colorama import Fore

from strong_opx.codegen.questions import ChoiceQuestion, SimpleQuestion


class SimpleQuestionTests(unittest.TestCase):
    @patch("builtins.input", MagicMock(return_value="test answer"))
    def test_from_stdin_no_validation_re(self):
        sq = SimpleQuestion("What is your name?")
        answer = sq.from_stdin()
        self.assertEqual(answer, "test answer")

    @patch("builtins.print")
    @patch("builtins.input", MagicMock(side_effect=["invalid answer", "red"]))
    def test_from_stdin_with_validation_re(self, mock_print):
        sq = SimpleQuestion("What is your favorite color?", validation_re=r"^(red|green|blue)$")
        answer = sq.from_stdin()
        self.assertEqual(answer, "red")
        mock_print.assert_called_with(f"{Fore.RED}Error: Must be of ^(red|green|blue)$ pattern.{Fore.RESET}")


class ChoiceQuestionTests(unittest.TestCase):
    @patch("strong_opx.codegen.questions.select_prompt", MagicMock(return_value="green"))
    def test_from_stdin(self):
        cq = ChoiceQuestion("What is your favorite color?", ["red", "green", "blue"])
        answer = cq.from_stdin()
        self.assertEqual(answer, "green")
