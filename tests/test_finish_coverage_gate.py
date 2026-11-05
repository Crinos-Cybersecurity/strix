"""finish_scan confronts the root agent with the coverage the runtime can see."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

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


def _finish() -> dict:
    return _do_finish(
        parent_id=None,
        executive_summary="summary",
        methodology="methodology",
        technical_analysis="analysis",
        recommendations="recommendations",
        agent_graph=_GRAPH,
    )


def test_finish_refuses_and_does_not_persist_when_a_class_is_unrecorded(monkeypatch) -> None:
    state = _FakeReportState()
    monkeypatch.setattr("strix.report.state.get_global_report_state", lambda: state)
    _record("sql_injection", "SQL injection")

    result = _finish()

    assert result["success"] is False
    assert result["scan_completed"] is False
    assert "Refusing to finish" in result["error"]
    assert "xss" in result["coverage_gaps"][0]["detail"]
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
