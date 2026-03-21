import subprocess
from typing import Tuple, List


def get_pods() -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-A"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def get_unhealthy_pods() -> Tuple[bool, List[str]]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-A", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

        unhealthy = []

        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue

            if "Running" in line or "Completed" in line:
                continue

            unhealthy.append(line)

        return True, unhealthy

    except subprocess.CalledProcessError as exc:
        return False, [exc.stderr.strip() or str(exc)]
    except Exception as exc:
        return False, [str(exc)]