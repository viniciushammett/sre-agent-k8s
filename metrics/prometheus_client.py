"""
Cliente HTTP determinístico para consulta ao Prometheus via PromQL.
Usa apenas urllib — zero dependências externas.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_AVAILABILITY_TIMEOUT = 3


class PrometheusClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def is_available(self) -> bool:
        """GET /-/healthy — retorna True/False, nunca lança exceção."""
        url = f"{self._base_url}/-/healthy"
        try:
            with urllib.request.urlopen(url, timeout=_AVAILABILITY_TIMEOUT) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.debug("Prometheus unavailable: %s", type(exc).__name__)
            return False

    def query(self, promql: str) -> dict:
        """GET /api/v1/query?query=<promql>. Retorna dict com status e resultado."""
        params = urllib.parse.urlencode({"query": promql})
        url = f"{self._base_url}/api/v1/query?{params}"
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw)
                result = payload.get("data", {}).get("result", [])
                return {"status": "success", "result": result}
        except urllib.error.HTTPError as exc:
            logger.warning("Prometheus HTTP error %s for query", exc.code)
        except urllib.error.URLError as exc:
            logger.warning("Prometheus connection error: %s", exc.reason)
        except Exception as exc:
            logger.warning("Prometheus query failed: %s", type(exc).__name__)
        return {"status": "error", "result": []}

    def get_pod_cpu_usage(self, pod: str, namespace: str) -> float | None:
        """Uso de CPU em millicores ou None se indisponível."""
        promql = (
            f'rate(container_cpu_usage_seconds_total{{'
            f'pod="{pod}",namespace="{namespace}",container!="POD"}}[2m]) * 1000'
        )
        return self._extract_scalar(self.query(promql))

    def get_pod_memory_usage(self, pod: str, namespace: str) -> float | None:
        """Uso de memória em MiB ou None se indisponível."""
        promql = (
            f'container_memory_working_set_bytes{{'
            f'pod="{pod}",namespace="{namespace}",container!="POD"}} / 1024 / 1024'
        )
        return self._extract_scalar(self.query(promql))

    def _extract_scalar(self, response: dict) -> float | None:
        """Extrai o primeiro valor escalar de uma resposta PromQL."""
        try:
            result = response.get("result", [])
            if not result:
                return None
            return float(result[0]["value"][1])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.debug("Failed to parse Prometheus result: %s", exc)
            return None
