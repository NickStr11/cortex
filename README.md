# 🧠 Cortex

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: Open Source](https://img.shields.io/badge/License-Open%20Source-brightgreen.svg)](https://opensource.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Powered by Claude Code](https://img.shields.io/badge/powered%20by-Claude%20Code-6b4fbb.svg)](https://claude.ai/)

### Your Personal AI-Corporation
**Orchestrate a team of AI agents via GitHub Issues.**

Cortex turns your GitHub repository into a self-evolving AI corporation. You act as the CEO—setting goals and reviewing results—while a specialized team of AI agents handles the implementation, testing, and security.

---

## 🚀 Quick Start

Get your AI corporation up and running in less than 5 minutes:

1.  **Clone the brain**:
    ```bash
    git clone https://github.com/your-username/cortex.git
    cd cortex
    ```
2.  **Start the engine**:
    Launch [Claude Code](https://claude.ai/code) in the project root.
3.  **Run your first Council**:
    ```bash
    /council
    ```
    *The AI council (CPO, CTO, CMO) analyzes your project and suggests actionable tasks.*
4.  **Dispatch tasks**:
    ```bash
    /dispatch
    ```
    *Cortex creates GitHub Issues and assigns them to specialized agents like **Jules** or **Codex**.*
5.  **Review and Merge**:
    Watch as PRs arrive. Review the code, run `/verify`, and merge!

---

## 🛠 Features

### 💻 11 Specialized Commands
Power up your CLI with custom slash commands:
- `/council`: Strategic planning and task generation.
- `/dispatch`: Automatic issue creation and agent assignment.
- `/heartbeat`: Automated tech trend scanning (HN, GitHub, Reddit).
- `/status`: Real-time health check of your agent pipeline.
- `/verify`: Automated verification of task completion.
- *And more: /handoff, /new-project, /screenshot, /tdd, /build-fix, /learn.*

### 🤖 4 AI Agents
Your dedicated workforce, ready for any task:
- **Architect**: High-level system design and tech stack decisions.
- **Code Reviewer**: Automated PR analysis and quality enforcement.
- **Security Auditor**: Scanning for vulnerabilities and secret leaks.
- **Verify Agent**: Ensuring every task meets the Definition of Done.

### ⚓ 8 Hardened Git Hooks
Built-in safety and quality checks:
- `check-secrets`: Prevent accidental leaks of API keys.
- `protect-main`: Enforce branch protection and PR workflows.
- `mcp-usage-tracker`: Monitor and optimize MCP tool usage.
- *Plus: check-filesize, pre-commit-check, grab-screenshot, output-secret-filter, expensive-tool-warning.*

### 🔄 3 Automated Workflows
Set-and-forget automation via GitHub Actions:
- **Heartbeat Cron**: Keeps your project updated with the latest AI trends.
- **Auto-Review**: Instant feedback on every Pull Request.
- **Jules Trigger**: Seamless handoff from Issue to Implementation.

---

## 🏗 Architecture

```text
       [ YOU: CEO ]
            |
            | /council (Planning)
            v
     [ AI CONCILIUM ] <--- (CPO, CTO, CMO, Growth)
            |
            | /dispatch (Execution)
            v
     [ GITHUB ISSUES ] <--- (The Task Queue)
            |
     +------+------+
     |             |
 [ JULES ]     [ CODEX ] <--- (AI Workers)
     |             |
     +------+------+
            |
            v
     [ PULL REQUESTS ]
            |
            | (Human Review)
            v
      [ PRODUCTION ]
```

---

## ⚖️ Comparison

| Feature | Cortex | claude-forge | Aider / Cursor |
| :--- | :---: | :---: | :---: |
| **Orchestration** | Multi-agent via Issues | Single CLI | IDE-based |
| **Workflow** | CEO-centric (Reviewer) | Developer-centric | Developer-centric |
| **Automation** | Cron + Hooks + Actions | Hooks only | Manual |
| **Context** | Project-wide AI Roles | File-based | Session-based |

---

## 📝 License
This project is open-source. See individual file headers for specific licensing terms where applicable.
