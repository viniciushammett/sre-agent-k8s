import pytest
from unittest.mock import MagicMock
from analyzers.diagnosis_engine import DiagnosisEngine, DiagnosisReport


@pytest.fixture
def mock_remediator():
    r = MagicMock()
    r.get_pod_previous_logs.return_value = "Error: connection refused at startup"
    r.describe_pod.return_value = (
        "Name: demo-nginx\n"
        "Restart Count: 8\n"
        "Limits:\n  memory: 128Mi\n"
        "Liveness: http-get /health\n"
        "Warning  Unhealthy  Liveness probe failed\n"
        "Image: nginx:nonexistent-tag\n"
        "Failed to pull image\n"
        "SecretNotFound: my-secret\n"
        "Unschedulable: insufficient memory\n"
    )
    r.get_pod_logs.return_value = "INFO starting server\nERROR timeout connecting to db"
    return r


@pytest.fixture
def engine(mock_remediator):
    return DiagnosisEngine(mock_remediator)


class TestDiagnosisEngineBase:
    def test_unknown_state_returns_report(self, engine):
        report = engine.investigate("UnknownState", "pod-x", "ns-x")
        assert isinstance(report, DiagnosisReport)
        assert report.state == "UnknownState"

    def test_investigate_never_raises(self, engine):
        # mesmo com remediator quebrando, nunca deve lançar exceção
        engine.remediator.describe_pod.side_effect = Exception("kubectl timeout")
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert report is not None
        assert "erro" in report.hypothesis.lower()


class TestCrashLoopBackOff:
    def test_returns_correct_state(self, engine):
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert report.state == "CrashLoopBackOff"

    def test_cause_category(self, engine):
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert report.cause_category == "application_error"

    def test_evidence_collected(self, engine):
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert len(report.evidence) > 0

    def test_not_safe_to_automate(self, engine):
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert report.safe_to_automate is False

    def test_requires_human_review(self, engine):
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert report.requires_human_review is True

    def test_has_recommended_actions(self, engine):
        report = engine.investigate("CrashLoopBackOff", "pod-x", "ns-x")
        assert len(report.recommended_actions) > 0


class TestOOMKilled:
    def test_returns_correct_state(self, engine):
        report = engine.investigate("OOMKilled", "pod-x", "ns-x")
        assert report.state == "OOMKilled"

    def test_cause_category(self, engine):
        report = engine.investigate("OOMKilled", "pod-x", "ns-x")
        assert report.cause_category == "scheduling_resource_problem"

    def test_evidence_collected(self, engine):
        report = engine.investigate("OOMKilled", "pod-x", "ns-x")
        assert len(report.evidence) > 0

    def test_has_recommended_actions(self, engine):
        report = engine.investigate("OOMKilled", "pod-x", "ns-x")
        assert len(report.recommended_actions) > 0


class TestImagePullBackOff:
    def test_returns_correct_state(self, engine):
        report = engine.investigate("ImagePullBackOff", "pod-x", "ns-x")
        assert report.state == "ImagePullBackOff"

    def test_errimagepull_also_handled(self, engine):
        report = engine.investigate("ErrImagePull", "pod-x", "ns-x")
        assert report.state == "ErrImagePull"
        assert report.cause_category == "image_runtime_problem"

    def test_cause_category(self, engine):
        report = engine.investigate("ImagePullBackOff", "pod-x", "ns-x")
        assert report.cause_category == "image_runtime_problem"

    def test_evidence_collected(self, engine):
        report = engine.investigate("ImagePullBackOff", "pod-x", "ns-x")
        assert len(report.evidence) > 0


class TestPending:
    def test_returns_correct_state(self, engine):
        report = engine.investigate("Pending", "pod-x", "ns-x")
        assert report.state == "Pending"

    def test_detects_insufficient_resources(self, engine):
        report = engine.investigate("Pending", "pod-x", "ns-x")
        assert report.cause_category == "scheduling_resource_problem"

    def test_evidence_collected(self, engine):
        report = engine.investigate("Pending", "pod-x", "ns-x")
        assert len(report.evidence) > 0

    def test_has_hypothesis(self, engine):
        report = engine.investigate("Pending", "pod-x", "ns-x")
        assert report.hypothesis is not None


class TestCreateContainerConfigError:
    def test_returns_correct_state(self, engine):
        report = engine.investigate("CreateContainerConfigError", "pod-x", "ns-x")
        assert report.state == "CreateContainerConfigError"

    def test_detects_secret_issue(self, engine):
        report = engine.investigate("CreateContainerConfigError", "pod-x", "ns-x")
        assert report.cause_category == "configuration_error"
        assert "secret" in report.hypothesis.lower()

    def test_evidence_collected(self, engine):
        report = engine.investigate("CreateContainerConfigError", "pod-x", "ns-x")
        assert len(report.evidence) > 0

    def test_create_container_error_also_handled(self, engine):
        report = engine.investigate("CreateContainerError", "pod-x", "ns-x")
        assert report is not None


class TestRunningUnhealthy:
    def test_returns_correct_state(self, engine):
        report = engine.investigate("Running", "pod-x", "ns-x")
        assert report.state == "Running"

    def test_detects_liveness_probe(self, engine):
        report = engine.investigate("Running", "pod-x", "ns-x")
        assert "liveness" in report.hypothesis.lower()

    def test_evidence_collected(self, engine):
        report = engine.investigate("Running", "pod-x", "ns-x")
        assert len(report.evidence) > 0

    def test_not_safe_to_automate(self, engine):
        report = engine.investigate("Running", "pod-x", "ns-x")
        assert report.safe_to_automate is False
