import requests
from typing import Tuple


def check_http(url: str, timeout: int = 5) -> Tuple[bool, str]:
    try:
        response = requests.get(url, timeout=timeout)
        return True, f"HTTP {response.status_code}"
    except requests.RequestException as exc:
        return False, str(exc)