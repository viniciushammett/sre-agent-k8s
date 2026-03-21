import paramiko
from typing import Tuple


def run_ssh_command(host: str, user: str, password: str, command: str) -> Tuple[bool, str]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )

        stdin, stdout, stderr = client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()

        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if exit_status == 0:
            return True, output or "Command executed successfully."
        return False, error or output or f"Command failed with exit code {exit_status}"

    except Exception as exc:
        return False, str(exc)
    finally:
        client.close()