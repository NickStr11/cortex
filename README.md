# Cortex — AI Orchestration System

## What is Cortex?
Cortex is a personal AI corporation system that orchestrates AI agents (Jules, Codex, Claude) via GitHub Issues to complete development tasks. The human acts as CEO — setting goals, reviewing PRs, and merging, while agents perform the actual work.

## How it Works
Cortex follows a command-based orchestration flow to automate development:
1. **Plan**: `/council` generates tasks based on project roles (CPO, CTO, CMO, Growth).
2. **Assign**: `/dispatch` creates GitHub Issues from these tasks with appropriate agent labels.
3. **Queue**: GitHub Issues act as a task queue for the agents.
4. **Execute**: Agents like **Jules** and **Codex** pick up tasks, implement solutions, and submit Pull Requests.
5. **Review**: The human CEO reviews and merges the Pull Requests.

## Usage

### /council
The `/council` command generates a set of tasks based on the current project context and defined roles. It analyzes the project's goals and breaks them down into actionable items for the AI agents. It also supports a **Forge Port Sprint** mode to benchmark against claude-forge and produce 3-5 concrete feature-port tasks for Cortex.

### /dispatch
The `/dispatch` command takes the generated tasks and creates corresponding GitHub Issues. It automatically assigns the correct labels (e.g., `jules`) so the AI agents know which tasks to pick up and work on.
