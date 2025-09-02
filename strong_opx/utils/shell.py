import contextlib
import os
import shlex
import subprocess
import sys

from colorama import Fore as ConsoleForeground
from colorama import Style

from strong_opx.exceptions import ProcessError


def shell(command, **kwargs) -> subprocess.CompletedProcess:
    ignore_exit_code = kwargs.pop("ignore_exit_code", False)

    if isinstance(command, str):
        print(Style.DIM, f"$ {command}", Style.RESET_ALL, sep="")
    else:
        str_command = " ".join(shlex.quote(c) if " " in c else c for c in command)
        print(Style.DIM, f"$ {str_command}", Style.RESET_ALL, sep="")

    try:
        results = subprocess.run(command, **kwargs)
        if not ignore_exit_code and results.returncode:
            message = f"Exit Code: {results.returncode}\n"

            if kwargs.get("capture_output", False):
                if results.stdout:
                    message += "\n<< Captured Output >>\n"
                    message += results.stdout.decode("utf8").strip()
                    message += "\n"

                if results.stderr:
                    message += f"\n<< Captured Error >>\n{ConsoleForeground.RED}"
                    message += results.stderr.decode("utf8").strip()
                    message += f"{Style.RESET_ALL}"

            raise ProcessError(message.strip())

        return results
    except KeyboardInterrupt:
        print("--KeyboardInterrupt--", file=sys.stderr)
        exit(1)


def static_eval_bash_vars(vars_str: str) -> dict[str, str]:
    bash_vars = {}
    for statement in vars_str.split(";"):
        statement = statement.strip()
        parts = statement.split("=")
        if len(parts) != 2:
            continue

        name, value = parts
        if name.startswith("export "):
            name = name[7:]

        if " " not in name and name.isupper() and value[0] != " ":
            bash_vars[name] = value

    return bash_vars


@contextlib.contextmanager
def ssh_agent(ssh_key: str = None):
    stdout = shell("ssh-agent", capture_output=True).stdout.decode("utf8")
    ssh_agent_info = static_eval_bash_vars(stdout)
    pid = ssh_agent_info.get("SSH_AGENT_PID")
    if not pid or not pid.isdigit():
        raise ProcessError(f"Failed to start ssh-agent; Output: {stdout}")

    try:
        for k, v in ssh_agent_info.items():
            os.environ[k] = v

        if ssh_key:
            shell(["ssh-add", ssh_key])
        else:
            shell(["ssh-add", "-K"])

        yield
    finally:
        for k in ssh_agent_info:
            os.environ.pop(k, None)

        os.kill(int(pid), 9)
