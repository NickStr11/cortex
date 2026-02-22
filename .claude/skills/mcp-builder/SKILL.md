---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
---

# MCP Server Development Guide

## Overview

Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. The quality of an MCP server is measured by how well it enables LLMs to accomplish real-world tasks.

---

# Process

## High-Level Workflow

Creating a high-quality MCP server involves four main phases:

### Phase 1: Deep Research and Planning

#### 1.1 Understand Modern MCP Design

**API Coverage vs. Workflow Tools:**
Balance comprehensive API endpoint coverage with specialized workflow tools. When uncertain, prioritize comprehensive API coverage.

**Tool Naming and Discoverability:**
Clear, descriptive tool names help agents find the right tools quickly. Use consistent prefixes (e.g., `github_create_issue`, `github_list_repos`).

**Context Management:**
Design tools that return focused, relevant data.

**Actionable Error Messages:**
Error messages should guide agents toward solutions with specific suggestions and next steps.

#### 1.2 Study MCP Protocol Documentation

Start with the sitemap: `https://modelcontextprotocol.io/sitemap.xml`
Then fetch specific pages with `.md` suffix.

#### 1.3 Study Framework Documentation

**Recommended stack:** TypeScript with Streamable HTTP for remote, stdio for local.

**Load framework documentation:**
- **MCP Best Practices**: [View Best Practices](./reference/mcp_best_practices.md)
- **TypeScript SDK**: Fetch `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- [TypeScript Guide](./reference/node_mcp_server.md)
- **Python SDK**: Fetch `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- [Python Guide](./reference/python_mcp_server.md)

#### 1.4 Plan Your Implementation

Review the service's API documentation. Prioritize comprehensive API coverage.

### Phase 2: Implementation

See language-specific guides for project setup:
- [TypeScript Guide](./reference/node_mcp_server.md)
- [Python Guide](./reference/python_mcp_server.md)

### Phase 3: Review and Test

- No duplicated code (DRY)
- Consistent error handling
- Full type coverage
- Clear tool descriptions
- `npm run build` or `python -m py_compile` to verify

### Phase 4: Create Evaluations

Load [Evaluation Guide](./reference/evaluation.md) for complete guidelines.

Create 10 evaluation questions that are independent, read-only, complex, realistic, verifiable, and stable.

Output format:
```xml
<evaluation>
  <qa_pair>
    <question>Your question here</question>
    <answer>Single verifiable answer</answer>
  </qa_pair>
</evaluation>
```

# Reference Files

- [MCP Best Practices](./reference/mcp_best_practices.md) — naming, pagination, transport, security
- [TypeScript Guide](./reference/node_mcp_server.md) — project structure, Zod, examples
- [Python Guide](./reference/python_mcp_server.md) — FastMCP, Pydantic, examples
- [Evaluation Guide](./reference/evaluation.md) — testing methodology
