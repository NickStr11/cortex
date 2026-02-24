#!/usr/bin/env python3
"""Cortex Metrics — AI Agent performance tracking.

Usage:
    uv run python main.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from beartype import beartype


@dataclass
class AgentMetrics:
    agent_name: str
    total_prs: int = 0
    merged_prs: int = 0
    closed_prs: int = 0
    open_prs: int = 0
    total_loc: int = 0
    merge_times_seconds: list[float] = field(default_factory=list)

    @property
    @beartype
    def success_rate(self) -> float:
        total_finished = self.merged_prs + self.closed_prs
        if total_finished == 0:
            return 0.0
        return (self.merged_prs / total_finished) * 100

    @property
    @beartype
    def avg_merge_time_hours(self) -> float:
        if not self.merge_times_seconds:
            return 0.0
        return sum(self.merge_times_seconds) / len(self.merge_times_seconds) / 3600

    @property
    @beartype
    def avg_loc(self) -> float:
        if self.total_prs == 0:
            return 0.0
        return self.total_loc / self.total_prs


@beartype
def parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    # GitHub returns ISO 8601 strings like "2024-02-24T12:00:00Z"
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


@beartype
def get_repo_info() -> tuple[str, str]:
    """Get owner and name of the current repository."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwnership"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        owner, name = data["nameWithOwnership"].split("/")
        return owner, name
    except Exception:
        # Fallback for local testing or if gh fails
        return "NickStr11", "cortex"


@beartype
def fetch_pr_data(owner: str, name: str) -> list[dict[str, Any]]:
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        pullRequests(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            number
            state
            createdAt
            mergedAt
            additions
            deletions
            labels(first: 10) {
              nodes { name }
            }
            closingIssuesReferences(first: 10) {
              nodes {
                number
                createdAt
                labels(first: 10) {
                  nodes { name }
                }
              }
            }
          }
        }
      }
    }
    """
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}", "-F", f"owner={owner}", "-F", f"name={name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return data["data"]["repository"]["pullRequests"]["nodes"]  # type: ignore
    except Exception as e:
        print(f"Error fetching data from GitHub: {e}", file=sys.stderr)
        return []


@beartype
def determine_agent(pr: dict[str, Any]) -> str | None:
    # Check labels on PR
    pr_labels = [l["name"].lower() for l in pr["labels"]["nodes"]]
    if "jules" in pr_labels:
        return "jules"
    if "codex" in pr_labels:
        return "codex"

    # Check labels on linked issues
    for issue in pr["closingIssuesReferences"]["nodes"]:
        issue_labels = [l["name"].lower() for l in issue["labels"]["nodes"]]
        if "jules" in issue_labels:
            return "jules"
        if "codex" in issue_labels:
            return "codex"

    return None


@beartype
def calculate_metrics(prs: list[dict[str, Any]]) -> dict[str, AgentMetrics]:
    metrics: dict[str, AgentMetrics] = {
        "jules": AgentMetrics("jules"),
        "codex": AgentMetrics("codex"),
    }

    for pr in prs:
        agent = determine_agent(pr)
        if not agent:
            continue

        m = metrics[agent]
        m.total_prs += 1
        m.total_loc += pr["additions"] + pr["deletions"]

        if pr["state"] == "MERGED":
            m.merged_prs += 1
            merged_at = parse_date(pr["mergedAt"])
            if merged_at:
                # Find the earliest linked issue creation time
                issue_times = [
                    parse_date(issue["createdAt"])
                    for issue in pr["closingIssuesReferences"]["nodes"]
                ]
                valid_issue_times = [t for t in issue_times if t]
                if valid_issue_times:
                    earliest_issue = min(valid_issue_times)
                    duration = (merged_at - earliest_issue).total_seconds()
                    if duration > 0:
                        m.merge_times_seconds.append(duration)
        elif pr["state"] == "CLOSED":
            m.closed_prs += 1
        elif pr["state"] == "OPEN":
            m.open_prs += 1

    return metrics


@beartype
def format_report(metrics: dict[str, AgentMetrics]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = [f"## Agent Performance Metrics ({now})\n"]

    for agent in ["jules", "codex"]:
        m = metrics[agent]
        if m.total_prs == 0:
            report.append(f"### {agent.capitalize()}\n- No data available.\n")
            continue

        report.append(f"### {agent.capitalize()}")
        report.append(f"- **Success Rate**: {m.success_rate:.1f}% ({m.merged_prs}/{m.merged_prs + m.closed_prs})")
        report.append(f"- **Avg Time to Merge**: {m.avg_merge_time_hours:.1f} hours")
        report.append(f"- **Avg LOC per Task**: {int(m.avg_loc)}")
        report.append(f"- **Total PRs**: {m.total_prs} ({m.open_prs} open, {m.merged_prs} merged, {m.closed_prs} closed)")
        report.append("")

    return "\n".join(report)


@beartype
def main() -> None:
    owner, name = get_repo_info()
    print(f"Fetching metrics for {owner}/{name}...", file=sys.stderr)
    prs = fetch_pr_data(owner, name)
    if not prs:
        print("No PR data found.")
        return

    metrics = calculate_metrics(prs)
    report = format_report(metrics)
    print(report)


if __name__ == "__main__":
    main()
