import json
from datetime import datetime
from pathlib import Path
from typing import Dict

INCIDENT_LOG_FILE = Path("incident_history.log")


def write_incident_summary(summary: Dict) -> None:
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **summary,
    }

    with INCIDENT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")