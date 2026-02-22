# MCP Server Evaluation Guide

## Overview

Create 10 evaluation questions to test whether LLMs can effectively use your MCP server.

## Requirements

- Questions must be READ-ONLY, INDEPENDENT, NON-DESTRUCTIVE
- Each question requires multiple tool calls (potentially dozens)
- Answers must be single, verifiable values
- Answers must be STABLE (won't change over time)

## Question Guidelines

1. Questions MUST be independent
2. Questions MUST require ONLY NON-DESTRUCTIVE operations
3. Questions must be REALISTIC, CLEAR, CONCISE, and COMPLEX
4. Questions must require deep exploration (multi-hop)
5. Questions must not be solvable with straightforward keyword search
6. Questions should stress-test tool return values
7. Include ambiguous questions (but with SINGLE VERIFIABLE ANSWER)

## Answer Guidelines

1. Answers must be VERIFIABLE via direct string comparison
2. Answers should prefer HUMAN-READABLE formats
3. Answers must be STABLE/STATIONARY
4. Answers must be DIVERSE (various modalities and formats)
5. Answers must NOT be complex structures

## Output Format

```xml
<evaluation>
  <qa_pair>
    <question>Find the project created in Q2 2024 with the highest number of completed tasks. What is the project name?</question>
    <answer>Website Redesign</answer>
  </qa_pair>
</evaluation>
```

## Evaluation Process

1. **Tool Inspection**: List available tools and understand capabilities
2. **Content Exploration**: Use READ-ONLY operations to explore data
3. **Question Generation**: Create 10 complex, realistic questions
4. **Answer Verification**: Solve each question yourself to verify

## Running Evaluations

```bash
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=your_api_key_here

# Local STDIO Server
python scripts/evaluation.py -t stdio -c python -a my_mcp_server.py evaluation.xml

# HTTP
python scripts/evaluation.py -t http -u https://example.com/mcp evaluation.xml
```
