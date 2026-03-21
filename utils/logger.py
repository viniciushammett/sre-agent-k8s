from datetime import datetime


def log(level: str, message: str):
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] [{level}] {message}")