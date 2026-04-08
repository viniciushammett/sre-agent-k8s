import pytest
from analyzers.incident_analyzer import suggest_remediation


class TestRolloutRestartNLP:
    def test_rollout_restart_with_namespace(self):
        result = suggest_remediation("rollout restart deployment demo-nginx in namespace sre-demo")
        assert result["action"] == "rollout_restart_deployment"
        assert result["params"]["deployment_name"] == "demo-nginx"
        assert result["params"]["namespace"] == "sre-demo"

    def test_rollout_restart_with_namespace_keyword(self):
        result = suggest_remediation("rollout restart deployment demo-nginx in sre-demo")
        assert result["action"] == "rollout_restart_deployment"
        assert result["params"]["deployment_name"] == "demo-nginx"

    def test_rollout_restart_without_namespace(self):
        result = suggest_remediation("rollout restart deployment demo-nginx")
        assert result["action"] == "rollout_restart_deployment"
        assert result["params"]["deployment_name"] == "demo-nginx"
        assert "namespace" not in result["params"]

    def test_rollout_restart_infers_from_context(self):
        # sem namespace no comando → params não contém namespace
        result = suggest_remediation("rollout restart deployment demo-nginx")
        assert result["params"].get("namespace") is None
