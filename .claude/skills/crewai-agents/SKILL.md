---
name: crewai-agents
description: "Build multi-agent teams with CrewAI. Quick setup, role-based agents, task delegation."
---

# CrewAI Multi-Agent Teams

## When to Use

- Need multiple specialized AI agents collaborating on a task
- Pipeline: research -> analysis -> writing (or any sequential chain)
- Hierarchical delegation: manager agent assigns sub-tasks to specialists
- Want role-based separation of concerns (each agent = one job)
- Prototyping multi-agent workflows faster than LangGraph/AutoGen

## Prerequisites

```bash
# Core framework (Python 3.10-3.13)
pip install crewai

# With built-in tools (search, scrape, file I/O, etc.)
pip install 'crewai[tools]'

# CLI for project scaffolding
uv tool install crewai
```

Environment variables (at minimum one LLM provider). Store in `.env`:
```bash
OPENAI_API_KEY=...
# or
GEMINI_API_KEY=...
# or use Ollama locally (no key needed)
```

## Quick Start

Minimal working example -- 2 agents, 2 tasks, sequential crew:

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="Senior Research Analyst",
    goal="Find accurate, up-to-date information about {topic}",
    backstory="10 years in tech industry analysis. Thorough and precise.",
    verbose=True,
)

writer = Agent(
    role="Content Writer",
    goal="Write a clear, engaging summary based on research findings",
    backstory="Technical writer who turns complex data into readable content.",
    verbose=True,
)

research_task = Task(
    description="Research the latest developments in {topic}. Find key trends and data.",
    expected_output="A list of 5 bullet points with the most relevant findings.",
    agent=researcher,
)

report_task = Task(
    description="Write a 3-paragraph summary based on the research findings.",
    expected_output="A well-structured summary in markdown format.",
    agent=writer,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, report_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff(inputs={"topic": "AI Agents in 2026"})
print(result)
```

## Core Concepts

### Agent

An LLM-powered unit with a role, goal, and optional tools.

```python
from crewai import Agent

agent = Agent(
    role="Senior Python Developer",        # Who the agent is
    goal="Write clean, tested Python code", # What it optimizes for
    backstory="Expert with 10 years of experience in backend systems.",
    llm="gpt-4o",                           # Default: OPENAI_MODEL_NAME or "gpt-4"
    tools=[],                               # List of tools the agent can use
    allow_delegation=False,                 # Can delegate to other agents
    max_iter=25,                            # Max reasoning iterations
    max_execution_time=300,                 # Timeout in seconds
    verbose=True,                           # Print agent's thought process
)
```

Key params:
- `llm` -- string like `"gpt-4o"`, `"gemini/gemini-2.0-flash"`, `"ollama/llama3.2"`
- `allow_delegation=True` -- agent can ask other crew members for help
- `allow_code_execution=True` -- agent can run Python code (uses Docker by default)

### Task

A unit of work assigned to an agent.

```python
from crewai import Task

task = Task(
    description="Analyze the dataset and identify top 3 trends.",
    expected_output="Bullet list of trends with supporting data.",
    agent=analyst_agent,
    tools=[data_tool],          # Task-specific tools (override agent tools)
    context=[previous_task],    # Output of these tasks fed as context
    output_file="report.md",   # Auto-save result to file
    async_execution=False,      # Set True for parallel execution
)
```

Key params:
- `context` -- list of Task objects whose output becomes input for this task
- `output_file` -- writes result to disk automatically
- `async_execution=True` -- runs in parallel with other async tasks
- `human_input=True` -- pauses for human review before finalizing

### Crew

The orchestrator that runs agents and tasks.

```python
from crewai import Crew, Process

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, report_task],
    process=Process.sequential,  # or Process.hierarchical
    verbose=True,
    memory=True,                 # Enable short/long-term memory
    max_rpm=10,                  # Rate limit API calls
)

result = crew.kickoff(inputs={"topic": "quantum computing"})
```

### Tool

A function an agent can call to interact with the world.

```python
from crewai.tools import tool

@tool("Search the web")
def search_tool(query: str) -> str:
    """Search the web for information. Use for finding current data."""
    # your implementation
    return search_api.search(query)
```

## Patterns

### Sequential (default)

Tasks run one after another. Output of task N becomes available to task N+1.

```python
crew = Crew(
    agents=[researcher, analyst, writer],
    tasks=[research_task, analysis_task, writing_task],
    process=Process.sequential,
)
```

### Hierarchical

A manager agent coordinates workers. It decides who does what.

```python
from crewai import Crew, Process

crew = Crew(
    agents=[data_analyst, report_writer, qa_reviewer],
    tasks=[complex_analysis_task],
    process=Process.hierarchical,
    manager_llm="gpt-4o",   # LLM for the auto-created manager
    verbose=True,
)
```

Or provide your own manager agent:

```python
manager = Agent(
    role="Project Manager",
    goal="Coordinate the team to deliver a complete analysis",
    backstory="Experienced PM who delegates effectively.",
    allow_delegation=True,
)

crew = Crew(
    agents=[data_analyst, report_writer],
    tasks=[complex_task],
    process=Process.hierarchical,
    manager_agent=manager,
)
```

### Task Context (chaining outputs)

Wire task outputs as inputs to downstream tasks:

```python
research = Task(
    description="Research {topic}",
    expected_output="Raw findings",
    agent=researcher,
)

analysis = Task(
    description="Analyze the research and find patterns",
    expected_output="Key insights",
    agent=analyst,
    context=[research],  # Gets research output automatically
)

report = Task(
    description="Write final report from the analysis",
    expected_output="Markdown report",
    agent=writer,
    context=[research, analysis],  # Gets both outputs
)
```

### Async Parallel Tasks

Run independent tasks simultaneously:

```python
task_a = Task(
    description="Research competitor A",
    expected_output="Competitor A analysis",
    agent=researcher,
    async_execution=True,
)

task_b = Task(
    description="Research competitor B",
    expected_output="Competitor B analysis",
    agent=researcher,
    async_execution=True,
)

# This task waits for both async tasks
summary = Task(
    description="Compare both competitors",
    expected_output="Comparison table",
    agent=analyst,
    context=[task_a, task_b],  # Waits for both to finish
)

crew = Crew(
    agents=[researcher, analyst],
    tasks=[task_a, task_b, summary],
    process=Process.sequential,  # Async tasks still run in parallel
)
```

## Adding Custom Tools

### @tool Decorator (simple, stateless)

```python
from crewai.tools import tool
import yfinance as yf

@tool("Get Stock Price")
def get_stock_price(ticker: str) -> str:
    """Get the current stock price and recent news for a ticker symbol."""
    stock = yf.Ticker(ticker)
    info = stock.info
    price = info.get("currentPrice", "N/A")
    name = info.get("shortName", ticker)
    return f"{name}: ${price}"
```

### BaseTool Class (complex, stateful, with input validation)

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class DBQueryInput(BaseModel):
    """Input schema for database query tool."""
    query: str = Field(..., description="SQL query to execute")
    limit: int = Field(default=10, description="Max rows to return")

class DatabaseQueryTool(BaseTool):
    name: str = "Query Database"
    description: str = "Execute a read-only SQL query against the analytics database."
    args_schema: type[BaseModel] = DBQueryInput

    def _run(self, query: str, limit: int = 10) -> str:
        import sqlite3
        conn = sqlite3.connect("analytics.db")
        cursor = conn.execute(f"{query} LIMIT {limit}")
        rows = cursor.fetchall()
        conn.close()
        return str(rows)
```

### Using Built-in Tools

```python
from crewai_tools import (
    SerperDevTool,       # Web search (needs SERPER_API_KEY env var)
    ScrapeWebsiteTool,   # Scrape any URL
    FileReadTool,        # Read files
    FileWriteTool,       # Write files
    DirectoryReadTool,   # List directory contents
)

agent = Agent(
    role="Researcher",
    goal="Find information online",
    tools=[SerperDevTool(), ScrapeWebsiteTool()],
)
```

### MCP Tools Integration

```python
from crewai_tools import MCPServerAdapter

# pip install 'crewai-tools[mcp]'
adapter = MCPServerAdapter(
    server_params={"command": "npx", "args": ["-y", "some-mcp-server"]},
)

agent = Agent(
    role="Analyst",
    goal="Analyze data",
    tools=adapter.tools,
)
```

## YAML Configuration (Recommended for Projects)

CrewAI CLI generates this structure:

```
my_project/
  src/my_project/
    config/
      agents.yaml
      tasks.yaml
    crew.py
    main.py
    tools/
      custom_tool.py
```

`agents.yaml`:
```yaml
researcher:
  role: "{topic} Senior Researcher"
  goal: "Find the most relevant information about {topic}"
  backstory: "Expert analyst with deep domain knowledge."

writer:
  role: "Technical Writer"
  goal: "Create clear, engaging content from research"
  backstory: "Skilled at turning complex findings into readable reports."
```

`tasks.yaml`:
```yaml
research_task:
  description: "Research {topic} thoroughly. Find trends, data, key players."
  expected_output: "5 bullet points of the most relevant findings."
  agent: researcher

report_task:
  description: "Write a summary report based on research findings."
  expected_output: "Markdown report, 3 paragraphs."
  agent: writer
```

`crew.py`:
```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

@CrewBase
class MyProjectCrew():
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            verbose=True,
        )

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def report_task(self) -> Task:
        return Task(config=self.tasks_config["report_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

`main.py`:
```python
from my_project.crew import MyProjectCrew

def run():
    inputs = {"topic": "AI Agents"}
    result = MyProjectCrew().crew().kickoff(inputs=inputs)
    print(result)

if __name__ == "__main__":
    run()
```

## Common Issues

### 1. Agent loops forever / hits max iterations

**Cause**: Vague `goal` or `description`. The LLM can't determine when it's done.

**Fix**: Make `expected_output` extremely specific. Add concrete criteria:
```python
# Bad
expected_output="A good analysis"

# Good
expected_output="A markdown table with 5 rows: Competitor, Market Share %, Key Product, Strengths, Weaknesses"
```

### 2. API key errors

**Cause**: Missing or incorrect env vars. CrewAI looks for `OPENAI_API_KEY` by default.

**Fix**: Set the right env var in `.env` for your provider. Or specify LLM directly:
```python
Agent(llm="ollama/llama3.2")  # No key needed
```

### 3. Hierarchical process acts like sequential

**Cause**: Known issue in some versions -- manager agent doesn't actually delegate. See crewAI#4783.

**Fix**: Use `manager_agent=` instead of `manager_llm=`. Give the manager a strong backstory about delegation:
```python
manager = Agent(
    role="Project Manager",
    goal="Delegate tasks to the right specialist. Never do the work yourself.",
    backstory="You are a pure coordinator. Your job is to assign tasks to team members "
              "and review their output. You NEVER do technical work directly.",
    allow_delegation=True,
)
```
If still broken, fall back to `Process.sequential` with explicit `context` wiring.

### 4. Timeout errors on long tasks

**Cause**: Default timeouts too low for complex LLM chains.

**Fix**: Increase agent and crew timeouts:
```python
agent = Agent(
    role="Analyst",
    goal="Deep analysis",
    max_execution_time=600,  # 10 minutes per agent
    max_iter=40,             # More reasoning steps
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    max_rpm=5,  # Lower rate limit to avoid 429s
)
```

### 5. Tool not being used by agent

**Cause**: Tool `description` / docstring doesn't clearly explain WHEN to use it. The LLM reads the description to decide.

**Fix**: Write tool descriptions as instructions, not labels:
```python
# Bad
@tool("search")
def search(q: str) -> str:
    """Search tool."""

# Good
@tool("Search the web")
def search(query: str) -> str:
    """Search the web for current information. Use this when you need
    up-to-date data, news, or facts that may not be in your training data."""
```

### 6. Output too verbose / unstructured

**Cause**: No output constraints in task definition.

**Fix**: Use `expected_output` and optionally `output_json` or `output_pydantic`:
```python
from pydantic import BaseModel

class AnalysisOutput(BaseModel):
    summary: str
    key_findings: list[str]
    confidence: float

task = Task(
    description="Analyze the market data",
    expected_output="Structured analysis with summary, findings, and confidence score",
    output_pydantic=AnalysisOutput,
    agent=analyst,
)
```

### 7. "Module not found" after install

**Cause**: Multiple Python envs, or `crewai-tools` not installed separately.

**Fix**:
```bash
# Make sure you're in the right env
which python
pip install 'crewai[tools]'

# For a CrewAI CLI project, use:
crewai install
# or
uv sync
```

### 8. Agents hallucinate URLs / fake data

**Cause**: No actual search/scrape tools attached. Agent "imagines" results.

**Fix**: Always attach real tools for data retrieval:
```python
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

researcher = Agent(
    role="Researcher",
    goal="Find real, verifiable information",
    tools=[SerperDevTool(), ScrapeWebsiteTool()],
    backstory="You ONLY use your tools. Never make up data or URLs.",
)
```

## Local LLMs (Ollama)

```python
from crewai import Agent

# No key needed -- just have Ollama running
agent = Agent(
    role="Local Analyst",
    goal="Analyze data privately",
    llm="ollama/llama3.2",       # or any Ollama model
)
```

Make sure Ollama is running: `ollama serve` and model is pulled: `ollama pull llama3.2`.

## References

- Official docs: https://docs.crewai.com
- GitHub (44K+ stars): https://github.com/crewAIInc/crewAI
- Examples repo: https://github.com/crewAIInc/crewAI-examples
- Built-in tools: https://docs.crewai.com/en/learn/create-custom-tools
- YAML config guide: https://docs.crewai.com/en/quickstart
- Firecrawl tutorial: https://www.firecrawl.dev/blog/crewai-multi-agent-systems-tutorial
- DigitalOcean guide: https://www.digitalocean.com/community/tutorials/crewai-crash-course-role-based-agent-orchestration
- Hierarchical delegation: https://activewizards.com/blog/hierarchical-ai-agents-a-guide-to-crewai-delegation
- Practical lessons learned: https://ondrej-popelka.medium.com/crewai-practical-lessons-learned-b696baa67242
