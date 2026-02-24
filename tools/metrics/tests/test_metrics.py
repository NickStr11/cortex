from __future__ import annotations

from datetime import datetime, timezone
from main import calculate_metrics, AgentMetrics

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
