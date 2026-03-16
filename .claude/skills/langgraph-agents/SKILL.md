---
name: langgraph-agents
description: "Build stateful agent workflows with LangGraph. Graph-based orchestration, conditional routing, memory, human-in-the-loop."
---

# LangGraph Agent Workflows

## When to Use

- Agent needs **cycles/loops** (retry, self-correction, iterative refinement) -- simple chains can't loop back
- **Conditional routing** -- different paths based on LLM output or state
- **Persistent memory** across turns -- checkpointing conversation state
- **Human-in-the-loop** -- pause execution, get approval, resume
- **Multi-agent** orchestration -- supervisor delegates to specialist agents
- **Long-running workflows** -- durable execution that survives failures

If your task is a straight input->LLM->output pipe, use a simple chain. LangGraph adds value when the flow is non-linear.

## Prerequisites

```bash
# Core
pip install -U langgraph langchain-core

# Pick your LLM provider
pip install langchain-anthropic    # Claude
pip install langchain-openai       # OpenAI / GPT
pip install langchain-google-genai # Gemini

# Persistence (pick one)
pip install langgraph-checkpoint-sqlite    # local dev
pip install langgraph-checkpoint-postgres  # production

# Optional
pip install langsmith  # tracing/debugging
```

Versions as of March 2026: `langgraph>=0.3`, `langchain-core>=0.3`, Python 3.9+.

## Quick Start

Minimal graph: 2 nodes + conditional edge.

```python
from __future__ import annotations

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    query: str
    category: str
    response: str


def classify(state: State) -> dict:
    """Classify the query."""
    q = state["query"].lower()
    if "refund" in q or "return" in q:
        return {"category": "billing"}
    return {"category": "general"}


def handle_billing(state: State) -> dict:
    return {"response": f"Billing team will handle: {state['query']}"}


def handle_general(state: State) -> dict:
    return {"response": f"Here's help with: {state['query']}"}


def route(state: State) -> Literal["billing", "general"]:
    return state["category"]


# Build graph
graph = StateGraph(State)
graph.add_node("classify", classify)
graph.add_node("billing", handle_billing)
graph.add_node("general", handle_general)

graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", route)
graph.add_edge("billing", END)
graph.add_edge("general", END)

app = graph.compile()

# Run
result = app.invoke({"query": "I want a refund", "category": "", "response": ""})
print(result["response"])  # "Billing team will handle: I want a refund"
```

## Core Concepts

### StateGraph

Container for the entire workflow. Parameterized by a state schema (TypedDict or Pydantic BaseModel).

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # reducer: append
    step_count: int
    task_complete: bool


graph = StateGraph(AgentState)
```

Key: `Annotated[list, add_messages]` is a **reducer** -- incoming messages get appended, not replaced.

### Nodes

Plain Python functions. Receive current state, return a **partial** state update (dict with only the keys to change).

```python
from langchain_core.messages import AIMessage


def my_node(state: AgentState) -> dict:
    # Do work -- call LLM, invoke tool, validate, etc.
    return {
        "messages": [AIMessage(content="Done")],
        "step_count": state["step_count"] + 1,
    }


graph.add_node("worker", my_node)
```

### Edges

Unconditional (always go A -> B) or conditional (function decides next node).

```python
from langgraph.graph import START, END

# Unconditional
graph.add_edge(START, "classify")
graph.add_edge("process", END)

# Conditional
graph.add_conditional_edges(
    "agent",           # source node
    should_continue,   # routing function -> returns node name string
    {                  # mapping: return value -> target node
        "continue": "tool",
        "end": END,
    },
)
```

### Checkpointer (Persistence)

Saves state after every node execution. Enables resume, time-travel, multi-turn conversations.

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()  # in-memory, for dev/testing
app = graph.compile(checkpointer=memory)

# Each thread_id = separate conversation
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke({"messages": [("human", "Hello")]}, config)

# Continue same conversation
result = app.invoke({"messages": [("human", "Follow up")]}, config)
```

For production, use `SqliteSaver` or `PostgresSaver`:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("checkpoints.db") as memory:
    app = graph.compile(checkpointer=memory)
```

## Patterns

### 1. ReAct Agent (Tool-Calling Loop)

The most common pattern. LLM decides whether to call a tool or respond.

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver


@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))


tools = [search, calculator]
model = ChatAnthropic(model="claude-sonnet-4-20250514").bind_tools(tools)


def agent(state: MessagesState) -> dict:
    response = model.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: MessagesState) -> str:
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END


graph = StateGraph(MessagesState)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")  # loop back after tool execution

app = graph.compile(checkpointer=MemorySaver())

result = app.invoke(
    {"messages": [("human", "What is 25 * 17?")]},
    {"configurable": {"thread_id": "t1"}},
)
print(result["messages"][-1].content)
```

### 2. Prebuilt ReAct Agent (Shortcut)

For standard tool-calling agents, skip manual graph building:

```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_react_agent(
    model=ChatAnthropic(model="claude-sonnet-4-20250514"),
    tools=[search, calculator],
    checkpointer=MemorySaver(),
)

result = agent.invoke(
    {"messages": [("human", "Search for LangGraph docs")]},
    {"configurable": {"thread_id": "t1"}},
)
```

### 3. Human-in-the-Loop (Interrupt + Resume)

Pause the graph, wait for human approval, resume.

```python
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver


def draft_node(state: MessagesState) -> dict:
    draft = "Here is the proposed email: ..."
    # Pause execution, return value to caller
    decision = interrupt({"draft": draft, "prompt": "Approve or reject?"})
    if decision == "approve":
        return {"messages": [("ai", "Email sent!")]}
    return {"messages": [("ai", f"Revising based on: {decision}")]}


graph = StateGraph(MessagesState)
graph.add_node("draft", draft_node)
graph.add_edge(START, "draft")
graph.add_edge("draft", END)

app = graph.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "email-1"}}

# First invoke -- hits interrupt, returns to caller
result = app.invoke({"messages": [("human", "Write an email")]}, config)

# Resume with human decision
result = app.invoke(Command(resume="approve"), config)
```

### 4. Multi-Agent (Supervisor Pattern)

Supervisor classifies tasks and delegates to specialist agents.

```python
from typing import Literal
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import create_react_agent


def create_supervisor():
    researcher = create_react_agent(
        model=model,
        tools=[search],
        prompt="You are a research specialist.",
    )
    writer = create_react_agent(
        model=model,
        tools=[],
        prompt="You are a writing specialist.",
    )

    def supervisor(state: MessagesState) -> dict:
        # LLM decides which agent to use
        response = model.invoke(
            [("system", "Route to 'researcher' or 'writer'.")]
            + state["messages"]
        )
        return {"messages": [response]}

    def route_supervisor(state: MessagesState) -> Literal["researcher", "writer", "__end__"]:
        last = state["messages"][-1].content.lower()
        if "researcher" in last:
            return "researcher"
        if "writer" in last:
            return "writer"
        return "__end__"

    graph = StateGraph(MessagesState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_supervisor)
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("writer", "supervisor")

    return graph.compile()
```

### 5. Subgraphs (Nested Graphs)

Encapsulate complex logic as a compiled subgraph, use it as a node.

```python
# Define inner graph
inner = StateGraph(MessagesState)
inner.add_node("step_a", step_a_fn)
inner.add_node("step_b", step_b_fn)
inner.add_edge(START, "step_a")
inner.add_edge("step_a", "step_b")
inner.add_edge("step_b", END)
inner_compiled = inner.compile()

# Use as node in outer graph
outer = StateGraph(MessagesState)
outer.add_node("preprocess", preprocess_fn)
outer.add_node("inner_workflow", inner_compiled)  # compiled graph as node
outer.add_node("postprocess", postprocess_fn)

outer.add_edge(START, "preprocess")
outer.add_edge("preprocess", "inner_workflow")
outer.add_edge("inner_workflow", "postprocess")
outer.add_edge("postprocess", END)

app = outer.compile()
```

### 6. Self-Correcting Agent (Retry with Counter)

Bounded retry loop with error tracking.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class RetryState(TypedDict):
    query: str
    result: str | None
    error_count: int
    max_retries: int


def call_api(state: RetryState) -> dict:
    try:
        # Attempt the operation
        result = external_api_call(state["query"])
        return {"result": result}
    except Exception as e:
        return {"result": None, "error_count": state["error_count"] + 1}


def route_after_call(state: RetryState) -> str:
    if state["result"] is not None:
        return "success"
    if state["error_count"] >= state["max_retries"]:
        return "failure"
    return "retry"


graph = StateGraph(RetryState)
graph.add_node("call", call_api)
graph.add_node("success", lambda s: {"result": s["result"]})
graph.add_node("failure", lambda s: {"result": "Failed after retries"})

graph.add_edge(START, "call")
graph.add_conditional_edges("call", route_after_call, {
    "success": "success",
    "failure": "failure",
    "retry": "call",  # loop back
})
graph.add_edge("success", END)
graph.add_edge("failure", END)

app = graph.compile()
result = app.invoke({"query": "fetch data", "result": None, "error_count": 0, "max_retries": 3})
```

## State Management

### TypedDict State with Reducers

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
import operator


class AppState(TypedDict, total=False):
    # Reducer: new messages are APPENDED to existing list
    messages: Annotated[list, add_messages]

    # Reducer: operator.add concatenates lists
    tool_outputs: Annotated[list[str], operator.add]

    # No reducer: value is REPLACED on each update
    current_step: str
    error_count: int
```

### Rules

1. **Return partial updates** -- only keys you want to change. Don't return the full state.
2. **Reducers** (`add_messages`, `operator.add`) accumulate values. Without a reducer, the value is overwritten.
3. **Immutability mindset** -- treat nodes as pure functions. Don't mutate state in-place.
4. **Keep state minimal** -- don't store transient values. Pass those through function scope.

### Input/Output Schemas

Control what goes in and comes out of the graph:

```python
class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    response: str

class FullState(TypedDict):
    user_input: str
    response: str
    internal_data: dict  # not exposed to caller

graph = StateGraph(FullState, input=InputState, output=OutputState)
```

## Common Issues

### 1. Infinite Loop

**Problem**: Graph runs forever, never reaches END.
**Cause**: Conditional edge always returns the same node (e.g., tool loop where LLM always calls tools).
**Fix**: Add a step counter in state, check it in routing function. Or use `recursion_limit` at invoke time:
```python
result = app.invoke(input, config={"recursion_limit": 25})
```

### 2. State Not Updating

**Problem**: Node returns a value but state doesn't change.
**Cause**: Returning the wrong key name, or returning a full state instead of partial update.
**Fix**: Return a dict with only the keys to update. Key names must exactly match the state schema.
```python
# Wrong
def my_node(state):
    state["count"] += 1  # mutation, not tracked
    return state

# Right
def my_node(state):
    return {"count": state["count"] + 1}
```

### 3. Messages Overwritten Instead of Appended

**Problem**: Each node call replaces the message list instead of adding to it.
**Cause**: Missing `add_messages` reducer annotation.
**Fix**: Use `Annotated[list, add_messages]` for message fields:
```python
from langgraph.graph.message import add_messages
from typing import Annotated

class State(TypedDict):
    messages: Annotated[list, add_messages]  # appends
```

### 4. Checkpointer Not Persisting

**Problem**: Conversation resets every invoke, no memory across turns.
**Cause**: Missing `thread_id` in config, or forgot to pass checkpointer to `compile()`.
**Fix**: Always provide both:
```python
app = graph.compile(checkpointer=MemorySaver())
result = app.invoke(input, {"configurable": {"thread_id": "unique-id"}})
```

### 5. Conditional Edge Returns Invalid Node Name

**Problem**: `ValueError: Unknown target node` at runtime.
**Cause**: Routing function returns a string that doesn't match any node name or END.
**Fix**: Ensure routing function return values match the mapping dict exactly. Use `Literal` type hints:
```python
from typing import Literal

def router(state) -> Literal["node_a", "node_b", "__end__"]:
    ...
```
`"__end__"` is the string form of `END`.

### 6. Subgraph State Not Shared with Parent

**Problem**: Parent graph can't see state changes from subgraph.
**Cause**: Subgraph has its own state schema; only overlapping keys propagate.
**Fix**: Ensure parent and subgraph share the same key names for data that must flow between them. Or explicitly map state in a wrapper node.

### 7. Command(resume=...) Used Incorrectly with interrupt()

**Problem**: Human-in-the-loop resume doesn't work, state doesn't update.
**Cause**: Using `Command(update=...)` instead of `Command(resume=...)` after an `interrupt()`.
**Fix**: After `interrupt()`, always resume with:
```python
result = app.invoke(Command(resume="user_value"), config)
```
If you also need to update state, send the update as part of the resume value and handle it in the node.

### 8. Streaming Not Working

**Problem**: No intermediate outputs during execution.
**Cause**: Using `invoke()` instead of `stream()`.
**Fix**: Use `stream()` or `astream()` for real-time updates:
```python
for event in app.stream(input, config, stream_mode="updates"):
    print(event)

# stream_mode options: "values", "updates", "messages", "debug"
```

## Streaming Modes

| Mode | What You Get |
|------|-------------|
| `"values"` | Full state after each node |
| `"updates"` | Only the partial update from each node |
| `"messages"` | Token-by-token LLM output (for chat UIs) |
| `"debug"` | Everything (verbose) |

```python
# Token streaming for chat UI
async for event in app.astream(input, config, stream_mode="messages"):
    # event is (message_chunk, metadata)
    print(event[0].content, end="", flush=True)
```

## References

- [LangGraph GitHub](https://github.com/langchain-ai/langgraph) -- 27K stars, MIT license
- [Official Docs](https://docs.langchain.com/oss/python/langgraph/) -- API reference, how-to guides
- [LangGraph Quickstart](https://docs.langchain.com/oss/python/langgraph/tutorials/introduction/) -- first agent tutorial
- [How-to Guides](https://docs.langchain.com/oss/python/langgraph/how-tos/) -- streaming, persistence, subgraphs, etc.
- [LangChain Academy](https://academy.langchain.com/) -- free structured LangGraph course
- [Botmonster: Multi-Step Agents](https://botmonster.com/posts/building-multi-step-ai-agents-with-langgraph/) -- production patterns
- [TDS: Building Agent from Scratch](https://towardsdatascience.com/building-a-langgraph-agent-from-scratch/) -- Feb 2026
- [freeCodeCamp: Practical Guide](https://www.freecodecamp.org/news/how-to-develop-ai-agents-using-langgraph-a-practical-guide/) -- Feb 2026
- [Swarnendu De: Best Practices](https://www.swarnendu.de/blog/langgraph-best-practices/) -- production playbook
- [Sparkco: Error Handling](https://sparkco.ai/blog/advanced-error-handling-strategies-in-langgraph-applications/) -- multi-level error strategies
