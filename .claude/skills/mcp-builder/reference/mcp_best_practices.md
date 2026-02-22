# MCP Server Best Practices

## Quick Reference

### Server Naming
- **Python**: `{service}_mcp` (e.g., `slack_mcp`)
- **Node/TypeScript**: `{service}-mcp-server` (e.g., `slack-mcp-server`)

### Tool Naming
- Use snake_case with service prefix
- Format: `{service}_{action}_{resource}`
- Example: `slack_send_message`, `github_create_issue`

### Response Formats
- Support both JSON and Markdown formats
- JSON for programmatic processing
- Markdown for human readability

### Pagination
- Always respect `limit` parameter
- Return `has_more`, `next_offset`, `total_count`
- Default to 20-50 items

### Transport
- **Streamable HTTP**: For remote servers, multi-client scenarios
- **stdio**: For local integrations, command-line tools
- Avoid SSE (deprecated in favor of streamable HTTP)

## Tool Naming and Design

1. **Use snake_case**: `search_users`, `create_project`
2. **Include service prefix**: `slack_send_message` not `send_message`
3. **Be action-oriented**: Start with verbs (get, list, search, create)
4. **Be specific**: Avoid generic names

### Tool Design
- Descriptions must precisely match actual functionality
- Provide tool annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- Keep tool operations focused and atomic

## Pagination

```json
{
  "total": 150,
  "count": 20,
  "offset": 0,
  "items": [],
  "has_more": true,
  "next_offset": 20
}
```

## Transport Options

| Criterion | stdio | Streamable HTTP |
|-----------|-------|-----------------|
| Deployment | Local | Remote |
| Clients | Single | Multiple |
| Complexity | Low | Medium |
| Real-time | No | Yes |

## Security Best Practices

- Use OAuth 2.1 or API keys in environment variables
- Sanitize file paths, validate URLs
- Check parameter sizes and ranges
- Prevent command injection
- Use schema validation (Pydantic/Zod) for all inputs
- For local HTTP servers: enable DNS rebinding protection, bind to `127.0.0.1`

## Tool Annotations

| Annotation | Type | Default | Description |
|-----------|------|---------|-------------|
| `readOnlyHint` | boolean | false | Tool does not modify its environment |
| `destructiveHint` | boolean | true | Tool may perform destructive updates |
| `idempotentHint` | boolean | false | Repeated calls have no additional effect |
| `openWorldHint` | boolean | true | Tool interacts with external entities |

## Error Handling

- Use standard JSON-RPC error codes
- Report tool errors within result objects
- Provide helpful, specific error messages with suggested next steps
- Clean up resources properly on errors
