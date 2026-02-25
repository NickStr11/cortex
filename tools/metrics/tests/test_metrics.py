from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from main import (
    calculate_metrics,
    AgentMetrics,
    parse_date,
    get_repo_info,
    fetch_pr_data,
    determine_agent,
    format_report,
    main
)

def test_parse_date():
    assert parse_date(None) is None
    assert parse_date("2024-02-24T12:00:00Z") == datetime(2024, 2, 24, 12, 0, 0, tzinfo=timezone.utc)
    assert parse_date("2024-02-24T12:00:00+00:00") == datetime(2024, 2, 24, 12, 0, 0, tzinfo=timezone.utc)

def test_agent_metrics_properties():
    m = AgentMetrics("test")
    assert m.success_rate == 0.0
    assert m.avg_merge_time_hours == 0.0
    assert m.avg_loc == 0.0

    m.merged_prs = 1
    m.closed_prs = 1
    assert m.success_rate == 50.0

    m.merge_times_seconds = [3600.0, 7200.0]
    assert m.avg_merge_time_hours == 1.5

    m.total_prs = 2
    m.total_loc = 100
    assert m.avg_loc == 50.0

@patch("subprocess.run")
def test_get_repo_info_success(mock_run: MagicMock):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({"nameWithOwnership": "owner/repo"}),
        check_returncode=lambda: None
    )
    owner, name = get_repo_info()
    assert owner == "owner"
    assert name == "repo"

@patch("subprocess.run")
def test_get_repo_info_fallback(mock_run: MagicMock):
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
    owner, name = get_repo_info()
    assert owner == "NickStr11"
    assert name == "cortex"

@patch("subprocess.run")
def test_fetch_pr_data_success(mock_run: MagicMock):
    mock_data = {"data": {"repository": {"pullRequests": {"nodes": [{"number": 1}]}}}}
    mock_run.return_value = MagicMock(
        stdout=json.dumps(mock_data),
        check_returncode=lambda: None
    )
    prs = fetch_pr_data("owner", "repo")
    assert len(prs) == 1
    assert prs[0]["number"] == 1

@patch("subprocess.run")
def test_fetch_pr_data_error(mock_run: MagicMock):
    mock_run.side_effect = Exception("gh failed")
    prs = fetch_pr_data("owner", "repo")
    assert prs == []

def test_determine_agent():
    # Label on PR
    pr = {
        "labels": {"nodes": [{"name": "jules"}]},
        "closingIssuesReferences": {"nodes": []}
    }
    assert determine_agent(pr) == "jules"

    # Label on PR (codex)
    pr = {
        "labels": {"nodes": [{"name": "codex"}]},
        "closingIssuesReferences": {"nodes": []}
    }
    assert determine_agent(pr) == "codex"

    # Label on Issue (jules)
    pr = {
        "labels": {"nodes": []},
        "closingIssuesReferences": {
            "nodes": [{"labels": {"nodes": [{"name": "jules"}]}}]
        }
    }
    assert determine_agent(pr) == "jules"

    # Label on Issue (codex)
    pr = {
        "labels": {"nodes": []},
        "closingIssuesReferences": {
            "nodes": [{"labels": {"nodes": [{"name": "codex"}]}}]
        }
    }
    assert determine_agent(pr) == "codex"

    # No label
    pr = {
        "labels": {"nodes": []},
        "closingIssuesReferences": {"nodes": []}
    }
    assert determine_agent(pr) is None

def test_format_report():
    metrics = {
        "jules": AgentMetrics("jules"),
        "codex": AgentMetrics("codex")
    }
    # No data
    report = format_report(metrics)
    assert "### Jules\n- No data available." in report
    assert "### Codex\n- No data available." in report

    # With data
    metrics["jules"].total_prs = 1
    metrics["jules"].merged_prs = 1
    metrics["jules"].total_loc = 100
    metrics["jules"].merge_times_seconds = [3600.0]
    report = format_report(metrics)
    assert "### Jules" in report
    assert "**Success Rate**: 100.0%" in report
    assert "**Avg Time to Merge**: 1.0 hours" in report
    assert "**Avg LOC per Task**: 100" in report

def test_calculate_metrics_edge_cases():
    # Empty PRs
    assert calculate_metrics([]) == {"jules": AgentMetrics("jules"), "codex": AgentMetrics("codex")}

    # PR without agent
    prs = [{
        "number": 1,
        "state": "OPEN",
        "additions": 1,
        "deletions": 1,
        "labels": {"nodes": []},
        "closingIssuesReferences": {"nodes": []}
    }]
    metrics = calculate_metrics(prs)
    assert metrics["jules"].total_prs == 0
    assert metrics["codex"].total_prs == 0

    # PR with missing mergedAt (should not happen for MERGED but good to test)
    prs = [{
        "number": 1,
        "state": "MERGED",
        "mergedAt": None,
        "additions": 1,
        "deletions": 1,
        "labels": {"nodes": [{"name": "jules"}]},
        "closingIssuesReferences": {"nodes": []}
    }]
    metrics = calculate_metrics(prs)
    assert metrics["jules"].merged_prs == 1
    assert metrics["jules"].merge_times_seconds == []

@patch("main.get_repo_info")
@patch("main.fetch_pr_data")
@patch("main.calculate_metrics")
@patch("main.format_report")
def test_main_success(mock_format, mock_calc, mock_fetch, mock_repo):
    mock_repo.return_value = ("owner", "repo")
    mock_fetch.return_value = [{"number": 1}]
    mock_calc.return_value = {"jules": AgentMetrics("jules"), "codex": AgentMetrics("codex")}
    mock_format.return_value = "Report Content"

    with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
        main()
        mock_stdout.write.assert_any_call("Report Content")

@patch("main.get_repo_info")
@patch("main.fetch_pr_data")
def test_main_no_data(mock_fetch, mock_repo):
    mock_repo.return_value = ("owner", "repo")
    mock_fetch.return_value = []

    with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
        main()
        # "No PR data found." is printed via print() which might call sys.stdout.write multiple times
        # depending on Python version and environment.
        calls = [call.args[0] for call in mock_stdout.write.call_args_list]
        assert any("No PR data found." in str(c) for c in calls)

def test_calculate_metrics():
    # Mock data
    prs = [
        {
            "number": 1,
            "state": "MERGED",
            "createdAt": "2024-02-24T10:00:00Z",
            "mergedAt": "2024-02-24T12:00:00Z",
            "additions": 100,
            "deletions": 50,
            "labels": {"nodes": [{"name": "jules"}]},
            "closingIssuesReferences": {
                "nodes": [
                    {"number": 101, "createdAt": "2024-02-24T08:00:00Z", "labels": {"nodes": []}}
                ]
            }
        },
        {
            "number": 2,
            "state": "CLOSED",
            "createdAt": "2024-02-24T11:00:00Z",
            "mergedAt": None,
            "additions": 10,
            "deletions": 10,
            "labels": {"nodes": []},
            "closingIssuesReferences": {
                "nodes": [
                    {"number": 102, "createdAt": "2024-02-24T10:00:00Z", "labels": {"nodes": [{"name": "codex"}]}}
                ]
            }
        },
        {
            "number": 3,
            "state": "OPEN",
            "createdAt": "2024-02-24T13:00:00Z",
            "mergedAt": None,
            "additions": 20,
            "deletions": 5,
            "labels": {"nodes": [{"name": "jules"}]},
            "closingIssuesReferences": {"nodes": []}
        }
    ]

    metrics = calculate_metrics(prs)

    # Jules metrics
    jules = metrics["jules"]
    assert jules.total_prs == 2
    assert jules.merged_prs == 1
    assert jules.open_prs == 1
    assert jules.closed_prs == 0
    assert jules.total_loc == 175  # (100+50) + (20+5)
    # Time to merge: 12:00 - 08:00 = 4 hours = 14400 seconds
    assert jules.merge_times_seconds == [14400.0]
    assert jules.avg_merge_time_hours == 4.0
    assert jules.success_rate == 100.0  # 1 merged / (1 merged + 0 closed)

    # Codex metrics
    codex = metrics["codex"]
    assert codex.total_prs == 1
    assert codex.merged_prs == 0
    assert codex.closed_prs == 1
    assert codex.success_rate == 0.0
    assert codex.total_loc == 20
