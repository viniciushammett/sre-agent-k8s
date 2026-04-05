import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import SessionContext


# ---------------------------------------------------------------------------
# 1. update()
# ---------------------------------------------------------------------------

def test_update_namespace():
    ctx = SessionContext()
    ctx.update({"namespace": "sre-demo"})
    assert ctx.active_namespace == "sre-demo"


def test_update_pod():
    ctx = SessionContext()
    ctx.update({"pod_name": "nginx-abc"})
    assert ctx.active_pod == "nginx-abc"


def test_update_partial_no_pod_key():
    ctx = SessionContext()
    ctx.update({"namespace": "sre-demo"})
    assert ctx.active_pod is None


def test_update_partial_no_namespace_key():
    ctx = SessionContext()
    ctx.update({"pod_name": "nginx-abc"})
    assert ctx.active_namespace is None


# ---------------------------------------------------------------------------
# 2. fill()
# ---------------------------------------------------------------------------

def test_fill_namespace_when_missing():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    result = ctx.fill({})
    assert result["namespace"] == "sre-demo"


def test_fill_pod_when_missing():
    ctx = SessionContext()
    ctx.active_pod = "nginx-abc"
    result = ctx.fill({})
    assert result["pod_name"] == "nginx-abc"


def test_fill_does_not_overwrite_explicit_namespace():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    result = ctx.fill({"namespace": "other-ns"})
    assert result["namespace"] == "other-ns"


def test_fill_does_not_overwrite_explicit_pod():
    ctx = SessionContext()
    ctx.active_pod = "nginx-abc"
    result = ctx.fill({"pod_name": "explicit-pod"})
    assert result["pod_name"] == "explicit-pod"


def test_fill_returns_new_dict():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    original = {"pod_name": "nginx-abc"}
    result = ctx.fill(original)
    assert result is not original
    assert "namespace" not in original


# ---------------------------------------------------------------------------
# 3. prompt()
# ---------------------------------------------------------------------------

def test_prompt_without_context():
    ctx = SessionContext()
    assert ctx.prompt() == "sre-agent> "


def test_prompt_with_namespace():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    assert ctx.prompt() == "sre-agent [sre-demo]> "


def test_prompt_with_namespace_and_pod():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    ctx.active_pod = "nginx-abc"
    assert ctx.prompt() == "sre-agent [sre-demo]> "


# ---------------------------------------------------------------------------
# 4. Comportamento parcial (fill com contexto parcial)
# ---------------------------------------------------------------------------

def test_fill_only_namespace_set():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    result = ctx.fill({})
    assert result.get("namespace") == "sre-demo"
    assert result.get("pod_name") is None


def test_fill_namespace_and_pod_set():
    ctx = SessionContext()
    ctx.active_namespace = "sre-demo"
    ctx.active_pod = "nginx-abc"
    result = ctx.fill({})
    assert result["namespace"] == "sre-demo"
    assert result["pod_name"] == "nginx-abc"
