"""finish_scan confronts the root agent with the coverage the runtime can see."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

import pytest
from agents.tool_context import ToolContext

from strix.core.agents import AgentCoordinator
from strix.tools.agents_graph.tools import agent_finish
from strix.tools.coverage.tools import _record_impl, hydrate_coverage_from_disk
from strix.tools.finish.tool import _coverage_summary, _do_finish


if TYPE_CHECKING:
    from pathlib import Path


_GRAPH = {
    "statuses": {"agent-1": "completed"},
    "names": {"agent-1": "injection-tester"},
    "metadata": {"agent-1": {"skills": ["sql_injection", "xss"]}},
}


@pytest.fixture(autouse=True)
def _empty_ledger(tmp_path: Path) -> None:
    hydrate_coverage_from_disk(tmp_path)


def _record(risk_class: str, risk_area: str) -> None:
    _record_impl(
        surface="POST /api/orders/{id}",
        risk_area=risk_area,
        risk_class=risk_class,
        outcome="no_issue_found",
        evidence="Parameters fuzzed; no anomalies.",
        agent_id="agent-1",
        agent_name="injection-tester",
    )


def _record_for(
    *,
    agent_id: str,
    agent_name: str,
    outcome: str = "no_issue_found",
    evidence: str = "Parameters fuzzed; no anomalies.",
) -> None:
    _record_impl(
        surface="GET /api/orders",
        risk_area="object-level authorization",
        outcome=outcome,
        evidence=evidence,
        agent_id=agent_id,
        agent_name=agent_name,
    )


_TWO_AGENT_GRAPH = {
    "statuses": {"agent-1": "completed", "agent-2": "completed"},
    "names": {"agent-1": "injection-tester", "agent-2": "recon"},
    "metadata": {
        "agent-1": {"skills": ["sql_injection", "xss"]},
        "agent-2": {"skills": []},
    },
}


def test_unrecorded_risk_class_is_reported_back_to_the_root_agent() -> None:
    _record("sql_injection", "SQL injection")

    summary = _coverage_summary(_GRAPH)

    assert summary["coverage_recorded"] == 1
    assert len(summary["coverage_gaps"]) == 1
    assert "xss" in summary["coverage_gaps"][0]
    assert "unexamined" in summary["coverage_gap_warning"]


def test_fully_accounted_coverage_raises_no_gap_warning() -> None:
    _record("sql_injection", "SQL injection")
    _record("xss", "cross-site scripting")

    summary = _coverage_summary(_GRAPH)

    assert "coverage_gaps" not in summary
    assert "coverage_gap_warning" not in summary


def test_an_empty_ledger_still_warns_first() -> None:
    summary = _coverage_summary(_GRAPH)

    assert summary["coverage_recorded"] == 0
    assert "No coverage was recorded" in summary["coverage_warning"]


class _FakeReportState:
    def __init__(self) -> None:
        self.vulnerability_reports: list[object] = []
        self.final: dict[str, str] | None = None

    def update_scan_final_fields(self, **kwargs: str) -> None:
        self.final = kwargs


def _finish(agent_graph: dict = _GRAPH) -> dict:
    return _do_finish(
        parent_id=None,
        executive_summary="summary",
        methodology="methodology",
        technical_analysis="analysis",
        recommendations="recommendations",
        agent_graph=agent_graph,
    )


def test_finish_refuses_and_does_not_persist_when_a_class_is_unrecorded(monkeypatch) -> None:
    state = _FakeReportState()
    monkeypatch.setattr("strix.report.state.get_global_report_state", lambda: state)
    _record("sql_injection", "SQL injection")

    result = _finish()

    assert result["success"] is False
    assert result["scan_completed"] is False
    assert "Refusing to finish" in result["error"]
    assert any("xss" in gap for gap in result["coverage_gaps"])
    assert state.final is None


def test_finish_persists_when_all_assigned_classes_are_recorded(monkeypatch) -> None:
    state = _FakeReportState()
    monkeypatch.setattr("strix.report.state.get_global_report_state", lambda: state)
    _record("sql_injection", "SQL injection")
    _record("xss", "cross-site scripting")

    result = _finish()

    assert result["success"] is True
    assert result["scan_completed"] is True
    assert "coverage_gaps" not in result
    assert state.final is not None


def test_finish_accepts_needs_follow_up_as_attestation(monkeypatch) -> None:
    state = _FakeReportState()
    monkeypatch.setattr("strix.report.state.get_global_report_state", lambda: state)
    _record("sql_injection", "SQL injection")
    _record_impl(
        surface="GET /api/orders",
        risk_area="cross-site scripting",
        risk_class="xss",
        outcome="needs_follow_up",
        evidence="Reflected parameter found but output encoding not confirmed.",
        agent_id="agent-1",
        agent_name="injection-tester",
    )

    result = _finish()

    assert result["success"] is True
    assert result["scan_completed"] is True
    assert state.final is not None


def test_silent_agent_is_reported_back_to_the_root_agent() -> None:
    _record("sql_injection", "SQL injection")
    _record("xss", "cross-site scripting")

    summary = _coverage_summary(_TWO_AGENT_GRAPH)

    assert len(summary["coverage_gaps"]) == 1
    assert "recon" in summary["coverage_gaps"][0]
    assert "without recording any coverage" in summary["coverage_gaps"][0]
    assert "agents that recorded nothing" in summary["coverage_gap_warning"]


def test_finish_refuses_when_an_agent_recorded_nothing(monkeypatch) -> None:
    state = _FakeReportState()
    monkeypatch.setattr("strix.report.state.get_global_report_state", lambda: state)
    _record("sql_injection", "SQL injection")
    _record("xss", "cross-site scripting")

    result = _finish(_TWO_AGENT_GRAPH)

    assert result["success"] is False
    assert result["scan_completed"] is False
    assert "Refusing to finish" in result["error"]
    assert any("recon" in gap for gap in result["coverage_gaps"])
    assert state.final is None


def test_finish_persists_when_every_agent_recorded_something(monkeypatch) -> None:
    state = _FakeReportState()
    monkeypatch.setattr("strix.report.state.get_global_report_state", lambda: state)
    _record("sql_injection", "SQL injection")
    _record("xss", "cross-site scripting")
    _record_for(agent_id="agent-2", agent_name="recon")

    result = _finish(_TWO_AGENT_GRAPH)

    assert result["success"] is True
    assert result["scan_completed"] is True
    assert "coverage_gaps" not in result
    assert state.final is not None


# --- agent_finish gate -----------------------------------------------------------


async def _agent_graph() -> AgentCoordinator:
    coordinator = AgentCoordinator()
    await coordinator.register("root", "strix", parent_id=None)
    await coordinator.register("child", "Validator", parent_id="root")
    await coordinator.attach_runtime("root", resumable=False)
    await coordinator.attach_runtime("child", resumable=False)
    return coordinator


async def _call_agent_finish(
    coordinator: AgentCoordinator, agent_id: str = "child", parent_id: str = "root"
) -> dict[str, Any]:
    ctx = ToolContext(
        context={"coordinator": coordinator, "agent_id": agent_id, "parent_id": parent_id},
        tool_name=agent_finish.name,
        tool_call_id="call-1",
        tool_arguments="{}",
    )
    raw: str = await agent_finish.on_invoke_tool(ctx, json.dumps({"result_summary": "done"}))
    return cast("dict[str, Any]", json.loads(raw))


@pytest.mark.asyncio
async def test_agent_finish_refuses_an_agent_with_no_coverage() -> None:
    coordinator = await _agent_graph()

    result = await _call_agent_finish(coordinator)

    assert result["success"] is False
    assert result["agent_completed"] is False
    assert "record_coverage" in result["error"]
    assert coordinator.statuses["child"] != "completed"
    assert coordinator.runtimes["root"].mailbox == []


@pytest.mark.asyncio
async def test_agent_finish_accepts_after_coverage_is_recorded() -> None:
    coordinator = await _agent_graph()
    _record_for(agent_id="child", agent_name="Validator")

    result = await _call_agent_finish(coordinator)

    assert result["success"] is True
    assert result["agent_completed"] is True
    assert coordinator.statuses["child"] == "completed"
    assert len(coordinator.runtimes["root"].mailbox) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("outcome", "evidence"),
    [
        ("not_applicable", "No file-upload surface exists on this target."),
        ("needs_follow_up", "Auth wall blocked testing before token entropy could be assessed."),
    ],
)
async def test_agent_finish_accepts_an_honest_unresolved_row(
    outcome: str, evidence: str
) -> None:
    coordinator = await _agent_graph()
    _record_for(agent_id="child", agent_name="Validator", outcome=outcome, evidence=evidence)

    result = await _call_agent_finish(coordinator)

    assert result["success"] is True
    assert result["agent_completed"] is True
    assert coordinator.statuses["child"] == "completed"
