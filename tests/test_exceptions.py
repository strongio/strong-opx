import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from strong_opx.exceptions import ErrorDetail
from strong_opx.utils.tracking import Position
from tests.helper_functions import patch_colorama


def new_error_detail(start_line: int, start_column: int, end_line: int = None, end_column: int = None) -> ErrorDetail:
    start_pos = Position(start_line, start_column)

    end_pos = None
    if end_line is not None and end_column is not None:
        end_pos = Position(end_line, end_column)

    return ErrorDetail(error="", file_path="", start_pos=start_pos, end_pos=end_pos)


@patch_colorama
class ErrorDetailTests(TestCase):
    def test_read_block__single_line(self):
        with tempfile.NamedTemporaryFile() as f:
            for i in range(1, 10):
                f.write(f"line {i}\n".encode("utf8"))

            f.flush()
            e = new_error_detail(1, 3, 1, 7)
            block = list(e.read_block(f.name))

        self.assertListEqual(
            [
                "{Style.DIM}1:  {Style.RESET_ALL}li{Style.BRIGHT}ne 1{Style.RESET_ALL}",
                "{Style.DIM}2:  {Style.RESET_ALL}line 2",
                "{Style.DIM}3:  {Style.RESET_ALL}line 3",
            ],
            block,
        )

    def test_read_block__multiple_line(self):
        with tempfile.NamedTemporaryFile() as f:
            for i in range(1, 10):
                f.write(f"line {i}\n".encode("utf8"))

            f.flush()
            e = new_error_detail(1, 3, 2, 6)
            block = list(e.read_block(f.name))

        self.assertListEqual(
            [
                "{Style.DIM}1:  {Style.RESET_ALL}li{Style.BRIGHT}ne 1",
                "{Style.DIM}2:  {Style.RESET_ALL}line {Style.RESET_ALL}2",
                "{Style.DIM}3:  {Style.RESET_ALL}line 3",
                "{Style.DIM}4:  {Style.RESET_ALL}line 4",
            ],
            block,
        )

    def test_read_block__remove_context_after_blank_line(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"line 1\n")
            f.write(b"line 2\n")
            f.write(b"line 3\n")
            f.write(b"\n")
            f.write(b"line 5\n")
            f.write(b"line 6\n")
            f.flush()

            block = list(new_error_detail(2, 3, 2, 7).read_block(f.name))

        self.assertListEqual(
            [
                "{Style.DIM}1:  {Style.RESET_ALL}line 1",
                "{Style.DIM}2:  {Style.RESET_ALL}li{Style.BRIGHT}ne 2{Style.RESET_ALL}",
                "{Style.DIM}3:  {Style.RESET_ALL}line 3",
            ],
            block,
        )

    def test_read_block__remove_context_before_blank_line(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"line 1\n")
            f.write(b"\n")
            f.write(b"line 3\n")
            f.write(b"line 4\n")
            f.write(b"line 5\n")
            f.flush()

            block = list(new_error_detail(3, 3, 3, 7).read_block(f.name))

        self.assertListEqual(
            [
                "{Style.DIM}3:  {Style.RESET_ALL}li{Style.BRIGHT}ne 3{Style.RESET_ALL}",
                "{Style.DIM}4:  {Style.RESET_ALL}line 4",
                "{Style.DIM}5:  {Style.RESET_ALL}line 5",
            ],
            block,
        )

    def test_read_block__no_end_pos(self):
        """
        Prints the "start" line and `YAMLError.lines_for_context` before and after the start line.
        """
        with tempfile.NamedTemporaryFile() as f:
            for i in range(1, 10):
                f.write(f"line {i}\n".encode("utf8"))

            f.flush()

            block = list(new_error_detail(3, 3).read_block(f.name))

            self.assertListEqual(
                [
                    "{Style.DIM}1:  {Style.RESET_ALL}line 1",
                    "{Style.DIM}2:  {Style.RESET_ALL}line 2",
                    "{Style.DIM}3:  {Style.RESET_ALL}li{Style.BRIGHT}ne 3{Style.RESET_ALL}",
                    "{Style.DIM}4:  {Style.RESET_ALL}line 4",
                    "{Style.DIM}5:  {Style.RESET_ALL}line 5",
                ],
                block,
            )

    def test_read_block__no_end_pos_one_line(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write("line 1\n".encode("utf8"))

            f.flush()
            block = list(new_error_detail(0, 3).read_block(f.name))

        self.assertEqual(["{Style.DIM}1:  {Style.RESET_ALL}li{Style.BRIGHT}ne 1{Style.RESET_ALL}"], block)

    def test_str__no_file_path(self):
        e = ErrorDetail("dummy error")
        self.assertEqual("{Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}dummy error{Style.RESET_ALL}", str(e))

    @patch("strong_opx.project.Project.current", new=MagicMock())
    def test_str__with_file_path(self):
        e = ErrorDetail("dummy error", file_path="some-path.yml")
        self.assertEqual(
            "{Fore.RED}╷{Fore.RESET}\n"
            "{Fore.RED}│{Fore.RESET} {Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}dummy error{Style.RESET_ALL}\n"
            "{Fore.RED}│{Fore.RESET} \n"
            "{Fore.RED}│{Fore.RESET}   in some-path.yml\n"
            "{Fore.RED}╵{Fore.RESET}",
            str(e),
        )

    @patch("strong_opx.project.Project.current", new=MagicMock())
    @patch("strong_opx.exceptions.ErrorDetail.read_block")
    def test_str__with_file_path_and_start_pos(self, read_block_mock: MagicMock):
        read_block_mock.side_effect = lambda *_: ["line 1", "line 2"]

        e = ErrorDetail("dummy error", file_path="some-path.yml", start_pos=Position(2, 2))
        self.assertEqual(
            "{Fore.RED}╷{Fore.RESET}\n"
            "{Fore.RED}│{Fore.RESET} {Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}dummy error{Style.RESET_ALL}\n"
            "{Fore.RED}│{Fore.RESET} \n"
            "{Fore.RED}│{Fore.RESET}   in some-path.yml on line 2 column 2\n"
            "{Fore.RED}│{Fore.RESET}   line 1\n"
            "{Fore.RED}│{Fore.RESET}   line 2\n"
            "{Fore.RED}╵{Fore.RESET}",
            str(e),
        )

    def test_str__with_hint(self):
        e = ErrorDetail("dummy error", hint="some cool hint")
        self.assertEqual(
            "{Fore.RED}╷{Fore.RESET}\n"
            "{Fore.RED}│{Fore.RESET} {Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}dummy error{Style.RESET_ALL}\n"
            "{Fore.RED}│{Fore.RESET} \n"
            "{Fore.RED}│{Fore.RESET} some cool hint\n"
            "{Fore.RED}╵{Fore.RESET}",
            str(e),
        )

    def test_str__with_long_hint(self):
        e = ErrorDetail("dummy error", hint="some cool but long hint " * 5)
        self.assertEqual(
            "{Fore.RED}╷{Fore.RESET}\n"
            "{Fore.RED}│{Fore.RESET} {Fore.RED}Error:{Fore.RESET} {Style.BRIGHT}dummy error{Style.RESET_ALL}\n"
            "{Fore.RED}│{Fore.RESET} \n"
            "{Fore.RED}│{Fore.RESET} some cool but long hint some cool but long hint some cool but long hint some\n"
            "{Fore.RED}│{Fore.RESET} cool but long hint some cool but long hint\n"
            "{Fore.RED}╵{Fore.RESET}",
            str(e),
        )
