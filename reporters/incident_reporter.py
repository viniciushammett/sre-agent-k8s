"""
IncidentReporter — serializa e persiste incident reports em JSONL.
Um registro por linha, append-only.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


DEFAULT_JSONL_PATH = "incident_history.jsonl"


@dataclass
class IncidentReport:
    """Estrutura completa de um incident report."""
    # Identificação
    timestamp: str = ""
    incident_id: str = ""
    session_id: str = ""

    # Input
    user_input: str = ""
    namespace: str = ""
    pod_name: str = ""

    # Classificação
    input_type: str = ""          # request | incident
    action: str = ""
    action_success: bool = False

    # Estado
    detected_state: Optional[str] = None
    health_status: Optional[str] = None
    container_name: Optional[str] = None
    restart_count: Optional[int] = None

    # Workload
    workload_type: Optional[str] = None
    workload_name: Optional[str] = None
    action_target: Optional[str] = None

    # Diagnosis
    cause_category: Optional[str] = None
    hypothesis: Optional[str] = None
    diagnosis_confidence: Optional[str] = None

    # Remediação
    follow_up_action: Optional[str] = None
    follow_up_executed: bool = False
    remediation_action: Optional[str] = None
    remediation_executed: bool = False
    remediation_success: Optional[bool] = None

    # Log analysis
    probable_cause: Optional[str] = None
    matched_pattern: Optional[str] = None
    confidence: Optional[str] = None

    # Outcome
    requires_human_review: Optional[bool] = None
    final_outcome: str = ""

    # Dry-run
    dry_run: bool = False


class IncidentReporter:
    """
    Persiste IncidentReport em arquivo JSONL.
    Append-only — nunca sobrescreve registros existentes.
    """

    def __init__(self, jsonl_path: str = DEFAULT_JSONL_PATH, session_id: str = ""):
        self.jsonl_path = jsonl_path
        self.session_id = session_id
        self._incident_count = 0

    def build(self, **kwargs) -> IncidentReport:
        """
        Constrói um IncidentReport com timestamp e IDs automáticos.
        Aceita qualquer campo do dataclass como keyword argument.
        """
        self._incident_count += 1
        now = datetime.now(timezone.utc)
        report = IncidentReport(
            timestamp=now.isoformat(),
            incident_id=f"{now.strftime('%Y%m%d%H%M%S')}-{self._incident_count:03d}",
            session_id=self.session_id,
            **{k: v for k, v in kwargs.items() if hasattr(IncidentReport, k)},
        )
        return report

    def save(self, report: IncidentReport) -> bool:
        """
        Persiste o report em JSONL. Retorna True se sucesso, False se erro.
        Nunca lança exceção.
        """
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(report), ensure_ascii=False) + "\n")
            return True
        except Exception:
            return False

    def load_all(self) -> list[IncidentReport]:
        """
        Carrega todos os reports do arquivo JSONL.
        Retorna lista vazia se arquivo não existe ou erro.
        """
        if not os.path.exists(self.jsonl_path):
            return []
        reports = []
        try:
            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        reports.append(IncidentReport(**data))
        except Exception:
            pass
        return reports

    def load_session(self, session_id: str = "") -> list[IncidentReport]:
        """
        Carrega apenas os reports da sessão atual.
        Se session_id vazio, usa self.session_id.
        """
        sid = session_id or self.session_id
        return [r for r in self.load_all() if r.session_id == sid]
