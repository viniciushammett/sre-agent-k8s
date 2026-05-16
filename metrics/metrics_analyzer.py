"""
Analisa métricas brutas do PrometheusClient e produz diagnóstico estruturado.
"""
import logging

logger = logging.getLogger(__name__)

_CPU_PRESSURE_THRESHOLD = 900.0   # millicores
_MEM_PRESSURE_THRESHOLD = 450.0   # MiB


class MetricsAnalyzer:
    def __init__(self, prometheus_client):
        self._client = prometheus_client

    def analyze(self, pod: str, namespace: str) -> dict:
        """Retorna dict estruturado com diagnóstico de métricas para o pod."""
        _unavailable = {
            "available": False,
            "cpu_millicores": None,
            "memory_mib": None,
            "cpu_pressure": False,
            "memory_pressure": False,
            "summary": "Prometheus unavailable — metrics skipped",
        }

        if self._client is None:
            return _unavailable

        try:
            if not self._client.is_available():
                return _unavailable

            cpu = self._client.get_pod_cpu_usage(pod, namespace)
            mem = self._client.get_pod_memory_usage(pod, namespace)

            cpu_r = round(cpu, 1) if cpu is not None else None
            mem_r = round(mem, 1) if mem is not None else None

            cpu_pressure = cpu_r is not None and cpu_r > _CPU_PRESSURE_THRESHOLD
            mem_pressure = mem_r is not None and mem_r > _MEM_PRESSURE_THRESHOLD

            summary = _build_summary(cpu_r, mem_r, cpu_pressure, mem_pressure)

            return {
                "available": True,
                "cpu_millicores": cpu_r,
                "memory_mib": mem_r,
                "cpu_pressure": cpu_pressure,
                "memory_pressure": mem_pressure,
                "summary": summary,
            }
        except Exception as exc:
            logger.warning("MetricsAnalyzer error: %s", exc)
            return _unavailable


def _build_summary(cpu, mem, cpu_pressure, mem_pressure) -> str:
    if cpu is None and mem is None:
        return "Metrics available but no data for pod"
    if cpu_pressure and mem_pressure:
        return f"High CPU ({cpu}m) and memory ({mem}MiB) usage detected"
    if cpu_pressure:
        return f"High CPU usage detected ({cpu}m)"
    if mem_pressure:
        return f"High memory usage detected ({mem}MiB)"
    parts = []
    if cpu is not None:
        parts.append(f"CPU: {cpu}m")
    if mem is not None:
        parts.append(f"Memory: {mem}MiB")
    return ", ".join(parts) + " — within normal range"
