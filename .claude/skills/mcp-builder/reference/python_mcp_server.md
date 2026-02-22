# Python MCP Server Implementation Guide

## Quick Reference

### Key Imports
```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum
import httpx
```

### Server Initialization
```python
mcp = FastMCP("service_mcp")
```

### Tool Registration Pattern
```python
@mcp.tool(name="tool_name", annotations={...})
async def tool_function(params: InputModel) -> str:
    pass
```

## Server Naming Convention

- **Format**: `{service}_mcp` (lowercase with underscores)
- **Examples**: `github_mcp`, `jira_mcp`, `stripe_mcp`

## Tool Implementation

```python
from pydantic import BaseModel, Field, ConfigDict

class ServiceToolInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    param1: str = Field(..., description="First parameter", min_length=1, max_length=100)
    param2: Optional[int] = Field(default=None, description="Optional integer", ge=0, le=1000)

@mcp.tool(
    name="service_tool_name",
    annotations={
        "title": "Human-Readable Tool Title",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def service_tool_name(params: ServiceToolInput) -> str:
    '''Tool description automatically becomes the description field.'''
    pass
```

## Error Handling

```python
def _handle_api_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404: return "Error: Resource not found."
        elif e.response.status_code == 403: return "Error: Permission denied."
        elif e.response.status_code == 429: return "Error: Rate limit exceeded."
        return f"Error: API request failed with status {e.response.status_code}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out."
    return f"Error: Unexpected error: {type(e).__name__}"
```

## Shared Utilities

```python
async def _make_api_request(endpoint: str, method: str = "GET", **kwargs) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method, f"{API_BASE_URL}/{endpoint}", timeout=30.0, **kwargs
        )
        response.raise_for_status()
        return response.json()
```

## Advanced FastMCP Features

### Context Parameter Injection
```python
from mcp.server.fastmcp import FastMCP, Context

@mcp.tool()
async def advanced_search(query: str, ctx: Context) -> str:
    await ctx.report_progress(0.25, "Starting search...")
    results = await search_api(query)
    return format_results(results)
```

### Resource Registration
```python
@mcp.resource("file://documents/{name}")
async def get_document(name: str) -> str:
    with open(f"./docs/{name}", "r") as f:
        return f.read()
```

### Lifespan Management
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def app_lifespan():
    db = await connect_to_database()
    yield {"db": db}
    await db.close()

mcp = FastMCP("example_mcp", lifespan=app_lifespan)
```

### Transport Options
```python
# stdio (default)
if __name__ == "__main__":
    mcp.run()

# Streamable HTTP
if __name__ == "__main__":
    mcp.run(transport="streamable_http", port=8000)
```

## Quality Checklist

- [ ] Server name follows `{service}_mcp` format
- [ ] All tools have `name` and `annotations` in decorator
- [ ] Pydantic BaseModel for all inputs with Field descriptions
- [ ] All network operations use async/await
- [ ] Common functionality extracted into reusable functions
- [ ] Server runs successfully
- [ ] Error scenarios handled gracefully
