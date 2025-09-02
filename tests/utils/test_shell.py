from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock, call, patch

import pytest

from strong_opx.exceptions import ProcessError
from strong_opx.utils.shell import ssh_agent, static_eval_bash_vars


@pytest.mark.parametrize(
    "stdout, bash_vars",
    [
        [
            "HELLO=world; export HELLO",
            {
                "HELLO": "world",
            },
        ],
        [
            "HELLO = world; export HELLO",
            {},
        ],
        [
            "SSH_AGENT_PID=1234; export SSH_AGENT_PID",
            {
                "SSH_AGENT_PID": "1234",
            },
        ],
        [
            "export SSH_AGENT_PID=1234",
            {
                "SSH_AGENT_PID": "1234",
            },
        ],
        [
            "hello=1234",
            {},
        ],
    ],
)
def test_static_eval_bash_vars(stdout: str, bash_vars: dict[str, str]):
    assert static_eval_bash_vars(stdout) == bash_vars


class TestSshAgent:
    @dataclass
    class Fixture:
        expected_shell_calls: list
        mock_shell: Mock
        mock_os: Mock
        mock_bash_vars: Mock

    @dataclass
    class Params:
        expected_shell_calls: list
        shell_std_out: str
        bash_vars: dict
        ssh_key: Optional[str] = None

    @pytest.fixture(
        ids=[
            "ssh key provided",
            "no ssh key provided",
        ],
        params=[
            Params(
                ssh_key="/tmp/ssh-key",
                bash_vars={"SSH_AGENT_PID": "1234"},
                shell_std_out="some shell response",
                expected_shell_calls=[
                    call("ssh-agent", capture_output=True),
                    call(["ssh-add", "/tmp/ssh-key"]),
                ],
            ),
            Params(
                bash_vars={"SSH_AGENT_PID": "1234"},
                shell_std_out="some shell response",
                expected_shell_calls=[
                    call("ssh-agent", capture_output=True),
                    call(["ssh-add", "-K"]),
                ],
            ),
        ],
    )
    @patch("strong_opx.utils.shell.os", autospec=True)
    @patch("strong_opx.utils.shell.static_eval_bash_vars", autospec=True)
    @patch("strong_opx.utils.shell.shell", autospec=True)
    def setup(self, mock_shell, mock_bash_vars, mock_os, request):
        mock_bash_vars.return_value = request.param.bash_vars
        mock_shell.return_value.stdout = request.param.shell_std_out.encode("utf8")
        with ssh_agent(ssh_key=request.param.ssh_key):
            pass

        return TestSshAgent.Fixture(
            mock_os=mock_os,
            mock_shell=mock_shell,
            mock_bash_vars=mock_bash_vars,
            expected_shell_calls=request.param.expected_shell_calls,
        )

    def test_eval_bash_vars(self, setup: Fixture):
        setup.mock_bash_vars.assert_called_once_with("some shell response")

    def test_shell_called(self, setup: Fixture):
        assert setup.mock_shell.mock_calls == setup.expected_shell_calls

    def test_os_environ_pop(self, setup: Fixture):
        setup.mock_os.environ.pop.assert_called_once_with("SSH_AGENT_PID", None)

    def test_os_kill(self, setup: Fixture):
        setup.mock_os.kill.assert_called_once_with(1234, 9)


@pytest.mark.parametrize(
    "bash_vars",
    [
        {"SSH_AGENT_PID": "bonk"},
        {},
    ],
)
@patch("strong_opx.utils.shell.static_eval_bash_vars", autospec=True)
@patch("strong_opx.utils.shell.shell", autospec=True)
def test_ssh_agent_exception(mock_shell, mock_bash_vars, bash_vars):
    mock_bash_vars.return_value = bash_vars
    mock_shell.return_value.stdout = b"some stdout"
    with pytest.raises(ProcessError, match="Failed to start ssh-agent; Output: some stdout"):
        with ssh_agent():
            pass
