import pytest
from unittest.mock import MagicMock
from remediators.dry_run_remediator import DryRunRemediator


@pytest.fixture
def real():
    r = MagicMock()
    r.get_pod_status.return_value = (True, '{"phase": "Running"}')
    r.list_pods.return_value = (True, "NAME  READY  STATUS")
    return r


@pytest.fixture
def dr(real):
    return DryRunRemediator(real)


class TestDryRunDestructive:
    def test_delete_pod_returns_dry_run_message(self, dr):
        ok, msg = dr.delete_pod("sre-demo", "nginx-123")
        assert ok is True
        assert "DRY-RUN" in msg
        assert "nginx-123" in msg
        assert "simulado" in msg

    def test_delete_pod_does_not_call_real(self, dr, real):
        dr.delete_pod("sre-demo", "nginx-123")
        real.delete_pod.assert_not_called()

    def test_rollout_restart_returns_dry_run_message(self, dr):
        ok, msg = dr.rollout_restart_deployment("sre-demo", "demo-nginx")
        assert ok is True
        assert "DRY-RUN" in msg
        assert "demo-nginx" in msg
        assert "simulado" in msg

    def test_rollout_restart_does_not_call_real(self, dr, real):
        dr.rollout_restart_deployment("sre-demo", "demo-nginx")
        real.rollout_restart_deployment.assert_not_called()


class TestDryRunReadOnly:
    def test_get_pod_status_delegates_to_real(self, dr, real):
        dr.get_pod_status("sre-demo", "nginx-123")
        real.get_pod_status.assert_called_once_with("sre-demo", "nginx-123")

    def test_list_pods_delegates_to_real(self, dr, real):
        dr.list_pods("sre-demo")
        real.list_pods.assert_called_once_with("sre-demo")

    def test_unknown_method_delegates_to_real(self, dr, real):
        real.some_future_method = MagicMock(return_value="ok")
        result = dr.some_future_method("arg1")
        real.some_future_method.assert_called_once_with("arg1")
