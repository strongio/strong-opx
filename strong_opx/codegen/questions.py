import re
from typing import Collection

from colorama import Fore

from strong_opx.utils.prompt import select_prompt


class Question:
    def from_stdin(self) -> str:
        raise NotImplementedError()


class SimpleQuestion(Question):
    def __init__(self, prompt: str, validation_re: str = None):
        self.prompt = prompt

        if validation_re:
            self.validation_re = re.compile(validation_re)
        else:
            self.validation_re = None

    def from_stdin(self) -> str:
        while True:
            answer = input(f"{self.prompt}: ")
            if not self.validation_re or self.validation_re.match(answer):
                break

            print(f"{Fore.RED}Error: Must be of {self.validation_re.pattern} pattern.{Fore.RESET}")

        return answer


class ChoiceQuestion(Question):
    def __init__(self, prompt: str, choices: Collection[str]):
        self.prompt = prompt
        self.choices = choices

    def from_stdin(self) -> str:
        return select_prompt(self.prompt, self.choices)
