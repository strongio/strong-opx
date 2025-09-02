import sys
from typing import Collection

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.filters import IsDone
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Dimension, FormattedTextControl, Layout
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, Window
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import RadioList

default_style = Style.from_dict(
    {
        "question-mark": "#5F819D",
        "pointer-selected": "#FF9D00 bold",  # AWS orange
        "answer": "#FF9D00 bold",  # AWS orange
        "question": "bold",
    }
)


class RadioListEx(RadioList):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._total_values = len(self.values)

    def _get_text_fragments(self) -> StyleAndTextTuples:
        tokens = []

        for index, (key, value) in enumerate(self.values):
            selected = index == self._selected_index
            tokens.append(("", " "))
            if selected:
                tokens.append(("[SetCursorPosition]", ""))
                tokens.append(("class:pointer-selected", "\u276f "))
            else:
                tokens.append(("", "  "))

            tokens.append(("class:radio-selected" if selected else "", value))
            tokens.append(("", "\n"))

        tokens.pop()  # Remove last newline.
        return tokens

    @property
    def selected_value(self):
        return self.values[self._selected_index][0]


def create_application(message: str, choices: Collection[str]) -> Application:
    answered = False
    radio_list = RadioListEx(values=list(zip(choices, choices)))

    def get_prompt_tokens():
        tokens = [
            ("class:question-mark", "?"),
            ("class:question", f" {message} "),
        ]

        if answered:
            tokens.append(("class:answer", f" {radio_list.selected_value}"))
        else:
            tokens.append(("", " (Use arrow keys)"))

        return tokens

    # assemble layout
    layout = Layout(
        HSplit(
            [
                Window(
                    height=Dimension.exact(1),
                    content=FormattedTextControl(get_prompt_tokens),
                ),
                ConditionalContainer(
                    HSplit([radio_list]),
                    filter=~IsDone(),
                ),
            ]
        )
    )

    # key bindings
    key_bindings = KeyBindings()

    @key_bindings.add(Keys.ControlQ, eager=True)
    @key_bindings.add(Keys.ControlC, eager=True)
    def _(event):
        get_app().exit(result=None)

    @key_bindings.add(Keys.Enter, eager=True)
    def set_answer(event):
        nonlocal answered
        answered = True

        get_app().exit(result=radio_list.selected_value)

    return Application(layout=layout, key_bindings=key_bindings, style=default_style, cursor=CursorShape.BLOCK)


def select_prompt(message: str, choices: Collection[str]) -> str:
    application = create_application(message, choices)
    selection = application.run()
    if selection is None:
        print("--KeyboardInterrupt--", file=sys.stderr)
        exit(1)

    return selection


def input_boolean(prompt, default=True) -> bool:
    if default is None:
        hint = "[y/n]"
    elif default:
        hint = "[Y/n] "
    else:
        hint = "[y/N] "

    while True:
        choice = input(f"{prompt} {hint}: ").strip().lower()
        if default is not None and choice == "":
            return default

        if choice == "y":
            return True

        if choice == "n":
            return False

        print('Please respond with "y" or "n")')
