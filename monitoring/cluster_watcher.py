"""
Cluster Watcher — monitoramento contínuo de pods por namespace.

Implementa polling periódico com detecção de mudança de estado e
callback para integração com o pipeline de diagnóstico.

Uso:
    from monitoring.cluster_watcher import ClusterWatcher

    def on_change(change: dict):
        print(change)  # {pod_name, previous_status, current_status}

    watcher = ClusterWatcher(namespace="sre-demo", interval=30)
    watcher.run(on_change)
"""
import json
import subprocess
import time
from typing import Callable

from utils.logger import log as _logger

TIMEOUT_READ = 15  # consistente com kubectl_remediator.py


def _log(level: str, message: str) -> None:
    _logger(level, f"[ClusterWatcher] {message}")


class ClusterWatcher:
    """
    Monitora pods em um namespace com polling periódico.

    Detecta mudanças de estado entre snapshots consecutivos e
    invoca um callback para cada mudança detectada.
    """

    def __init__(self, namespace: str, interval: int = 30):
        """
        Args:
            namespace: namespace Kubernetes a monitorar.
            interval:  intervalo em segundos entre polls (padrão: 30).
        """
        self.namespace = namespace
        self.interval = interval

    def get_pod_states(self) -> dict:
        """
        Executa kubectl get pods -n <namespace> -o json e extrai
        pod_name → parsed_status para todos os pods do namespace.

        A lógica de parsing é idêntica à de get_pod_status em
        kubectl_remediator.py: parsed_status = container_state_reason or phase,
        onde container_state_reason vem de waiting.reason ou terminated.reason
        do primeiro containerStatus.

        Returns:
            dict {pod_name: parsed_status}. Retorna {} se kubectl falhar.
        """
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_READ,
                check=True,
            )
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as exc:
            _log("ERROR", f"kubectl get pods falhou: {exc.stderr.strip() or str(exc)}")
            return {}
        except subprocess.TimeoutExpired:
            _log("ERROR", f"Timeout ({TIMEOUT_READ}s) ao executar kubectl get pods -n {self.namespace}")
            return {}
        except Exception as exc:
            _log("ERROR", f"Erro inesperado em get_pod_states: {exc}")
            return {}

        states = {}
        for item in data.get("items", []):
            pod_name = item.get("metadata", {}).get("name", "")
            if not pod_name:
                continue

            phase = item.get("status", {}).get("phase", "Unknown")
            container_statuses = item.get("status", {}).get("containerStatuses", [])
            container_state_reason = None

            if container_statuses:
                state = container_statuses[0].get("state", {})
                waiting = state.get("waiting")
                terminated = state.get("terminated")

                if waiting and waiting.get("reason"):
                    container_state_reason = waiting["reason"]
                elif terminated and terminated.get("reason"):
                    container_state_reason = terminated["reason"]

            states[pod_name] = container_state_reason or phase

        return states

    def detect_state_changes(self, previous: dict, current: dict) -> list:
        """
        Compara dois snapshots e retorna apenas os pods que mudaram de estado.

        Detecta três tipos de mudança:
          - estado alterado: pod existia antes e agora, mas status diferente
          - pod novo:        pod não existia no snapshot anterior (previous_status=None)
          - pod removido:    pod desapareceu do snapshot atual (current_status=None)

        Args:
            previous: snapshot anterior {pod_name: parsed_status}
            current:  snapshot atual    {pod_name: parsed_status}

        Returns:
            lista de dicts com campos: pod_name, previous_status, current_status.
            Retorna [] se não houver mudanças.
        """
        changes = []
        for pod_name in sorted(set(previous) | set(current)):
            prev_status = previous.get(pod_name)
            curr_status = current.get(pod_name)
            if prev_status != curr_status:
                changes.append({
                    "pod_name": pod_name,
                    "previous_status": prev_status,
                    "current_status": curr_status,
                })
        return changes

    def run(self, callback: Callable[[dict], None]) -> None:
        """
        Loop de monitoramento contínuo.

        Na primeira iteração, estabelece o snapshot inicial sem disparar
        callbacks (baseline). A partir da segunda iteração, detecta mudanças
        e invoca callback(change) para cada mudança encontrada.

        O loop é interrompido por KeyboardInterrupt (Ctrl+C).
        Exceções no callback são capturadas e logadas — o loop continua.

        Args:
            callback: função chamada para cada mudança detectada.
                      Recebe dict {pod_name, previous_status, current_status}.
        """
        _log("INFO", f"iniciado — namespace: {self.namespace}, interval: {self.interval}s")

        previous = None

        while True:
            try:
                current = self.get_pod_states()

                if previous is None:
                    _log("INFO", f"baseline coletado — {len(current)} pod(s) em '{self.namespace}'")
                    previous = current
                else:
                    changes = self.detect_state_changes(previous, current)
                    if changes:
                        _log("INFO", f"{len(changes)} mudança(s) detectada(s) em '{self.namespace}'")
                        for change in changes:
                            try:
                                callback(change)
                            except Exception as exc:
                                _log("ERROR", f"erro no callback para {change['pod_name']}: {exc}")
                    previous = current

            except KeyboardInterrupt:
                _log("INFO", "encerrado pelo usuário.")
                break
            except Exception as exc:
                _log("ERROR", f"erro inesperado no loop: {exc}")

            time.sleep(self.interval)
