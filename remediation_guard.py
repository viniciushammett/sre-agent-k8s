import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

LOG_FILE = Path("remediation.log")
MAX_AUTO_REMEDIATIONS_PER_WORKLOAD = 2


def _derive_workload_name(pod_name: str) -> str:
    """
    Best-effort derivation of workload name from a Deployment-managed pod.
    Example:
      crashloop-demo-6c6c5ffb65-j7jkw -> crashloop-demo
    """
    parts = pod_name.split("-")
    if len(parts) >= 3:
        return "-".join(parts[:-2])
    return pod_name


def _load_entries():
    if not LOG_FILE.exists():
        return []

    entries = []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def can_auto_remediate(namespace: str, pod_name: str, action: str) -> Tuple[bool, str]:
    workload_name = _derive_workload_name(pod_name)
    entries = _load_entries()

    count = sum(
        1
        for entry in entries
        if entry.get("namespace") == namespace
        and entry.get("workload_name") == workload_name
        and entry.get("action") == action
    )

    if count >= MAX_AUTO_REMEDIATIONS_PER_WORKLOAD:
        return (
            False,
            f"Auto-remediation blocked: limit of {MAX_AUTO_REMEDIATIONS_PER_WORKLOAD} reached for workload={workload_name} action={action}.",
        )

    return (
        True,
        f"Auto-remediation allowed: current count={count}, limit={MAX_AUTO_REMEDIATIONS_PER_WORKLOAD} for workload={workload_name} action={action}.",
    )


def register_remediation_attempt(namespace: str, pod_name: str, action: str) -> None:
    workload_name = _derive_workload_name(pod_name)

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "namespace": namespace,
        "pod_name": pod_name,
        "workload_name": workload_name,
        "action": action,
    }

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")