"""
Event Watcher — monitoramento orientado a eventos via kubectl get events --watch.

Implementa stream contínuo de eventos Kubernetes com filtragem por tipo relevante,
retry automático e callback por evento detectado. Executa em thread daemon.

Uso:
    from monitoring.event_watcher import EventWatcher

    def on_event(event_type: str, pod_name: str, message: str, namespace: str):
        print(event_type, pod_name, message)

    watcher = EventWatcher(namespace="sre-demo")
    watcher.start(on_event)
    # ... later ...
    watcher.stop()
"""
import re
import subprocess
import threading
import time
from typing import Callable, Optional

from utils.logger import log as _logger

RETRY_MAX = 3       # número de retries após a primeira tentativa
RETRY_DELAY = 5     # segundos entre tentativas

# Tipos de evento relevantes para diagnóstico — determinístico, sem heurística
WATCHED_REASONS = frozenset({
    "BackOff",
    "OOMKilling",
    "Failed",
    "FailedScheduling",
    "Unhealthy",
    "FailedMount",
    "ErrImagePull",
    "ImagePullBackOff",
})

# Extrai pod_name de OBJECT no formato pod/<name> ou Pod/<name>
_RE_POD_OBJECT = re.compile(r"^[Pp]od/(.+)$")


def _log(level: str, message: str) -> None:
    _logger(level, f"[EventWatcher] {message}")


class EventWatcher:
    """
    Monitora eventos Kubernetes via kubectl get events --watch.

    Filtra eventos por tipo relevante e invoca um callback para cada evento
    detectado referente a um pod. Executa em thread daemon sem bloquear o
    chamador.
    """

    def __init__(self, namespace: str):
        """
        Args:
            namespace: namespace Kubernetes a monitorar.
        """
        self.namespace = namespace
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None

    def _parse_line(self, line: str) -> Optional[dict]:
        """
        Parseia uma linha de saída do kubectl get events --watch.

        Formato esperado (colunas separadas por whitespace):
            LAST SEEN   TYPE   REASON   OBJECT   MESSAGE...

        Retorna None para o header, linhas curtas, reasons fora do conjunto
        filtrado ou objetos que não sejam pods.

        Args:
            line: linha de texto da saída do kubectl.

        Returns:
            dict com event_type, pod_name, message — ou None se irrelevante.
        """
        line = line.rstrip()
        if not line:
            return None

        # split em no máximo 5 partes: last_seen, type_, reason, object_, message
        parts = line.split(None, 4)
        if len(parts) < 4:
            return None

        reason = parts[2]
        object_ = parts[3]
        message = parts[4].strip() if len(parts) == 5 else ""

        # Ignorar linha de header
        if reason == "REASON":
            return None

        # Filtrar apenas reasons relevantes ao diagnóstico
        if reason not in WATCHED_REASONS:
            return None

        # Extrair pod_name — ignorar eventos de outros tipos de objeto
        match = _RE_POD_OBJECT.match(object_)
        if not match:
            return None

        pod_name = match.group(1)
        return {"event_type": reason, "pod_name": pod_name, "message": message}

    def _stream_events(self, callback: Callable) -> None:
        """
        Executa kubectl get events --watch e processa linhas em stream.

        Faz até RETRY_MAX retries em caso de falha do subprocess, aguardando
        RETRY_DELAY segundos entre tentativas. Usa stop_event.wait() no lugar
        de time.sleep() para que stop() possa interromper a espera imediatamente.

        Args:
            callback: função chamada para cada evento relevante.
        """
        retries = 0

        while not self._stop_event.is_set() and retries <= RETRY_MAX:
            try:
                _log("INFO", f"iniciando stream — namespace: {self.namespace} "
                     f"(tentativa {retries + 1}/{RETRY_MAX + 1})")

                self._process = subprocess.Popen(
                    ["kubectl", "get", "events", "--watch", "-n", self.namespace],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Leitura linha a linha — bloqueia até nova linha ou EOF
                for line in self._process.stdout:
                    if self._stop_event.is_set():
                        break

                    parsed = self._parse_line(line)
                    if parsed is None:
                        continue

                    try:
                        callback(
                            event_type=parsed["event_type"],
                            pod_name=parsed["pod_name"],
                            message=parsed["message"],
                            namespace=self.namespace,
                        )
                    except Exception as exc:
                        _log("ERROR", f"erro no callback para {parsed['pod_name']}: {exc}")

                self._process.wait()

                if self._stop_event.is_set():
                    break

                returncode = self._process.returncode
                stderr_output = self._process.stderr.read().strip()
                _log("WARNING", f"kubectl encerrou inesperadamente (código {returncode})"
                     + (f": {stderr_output}" if stderr_output else ""))

                retries += 1
                if retries <= RETRY_MAX:
                    _log("INFO", f"aguardando {RETRY_DELAY}s antes do retry {retries}/{RETRY_MAX}")
                    self._stop_event.wait(timeout=RETRY_DELAY)

            except FileNotFoundError:
                _log("ERROR", "kubectl não encontrado no PATH — abortando")
                break
            except Exception as exc:
                _log("ERROR", f"erro inesperado no stream: {exc}")
                retries += 1
                if retries <= RETRY_MAX:
                    _log("INFO", f"aguardando {RETRY_DELAY}s antes do retry {retries}/{RETRY_MAX}")
                    self._stop_event.wait(timeout=RETRY_DELAY)

        if retries > RETRY_MAX:
            _log("ERROR", f"número máximo de retries ({RETRY_MAX}) atingido — monitoramento encerrado")

        _log("INFO", "stream encerrado")

    def start(self, callback: Callable[..., None]) -> None:
        """
        Inicia o monitoramento de eventos em thread daemon.

        Não bloqueia o chamador. Thread marcada como daemon encerra
        automaticamente junto com o processo principal.

        Args:
            callback: função chamada para cada evento relevante.
                      Assinatura: on_event(event_type, pod_name, message, namespace).
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._stream_events,
            args=(callback,),
            daemon=True,
            name=f"EventWatcher-{self.namespace}",
        )
        self._thread.start()
        _log("INFO", f"thread iniciada — namespace: {self.namespace}")

    def stop(self) -> None:
        """
        Encerra o stream de eventos e a thread de forma limpa.

        Sinaliza o stop_event (interrompe loop e sleeps), termina o subprocess
        se ainda estiver ativo e aguarda a thread encerrar (timeout: 10s).
        """
        _log("INFO", "encerrando...")
        self._stop_event.set()

        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception as exc:
                _log("WARNING", f"erro ao terminar subprocess: {exc}")

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                _log("WARNING", "thread não encerrou dentro do timeout de 10s")

        _log("INFO", "encerrado")
